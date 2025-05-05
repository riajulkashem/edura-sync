from datetime import datetime, date

from peewee import DoesNotExist
from interfaces.database.models import (
    db, Device, User, Attendance, Settings
)


class Repository:
    """
    Generic repository for basic CRUD operations.
    Subclass with `model` set to a Peewee Model class.
    """

    def __init__(self, model):
        self.model = model

    def get(self, **filters):
        try:
            return self.model.get(**filters)
        except DoesNotExist:
            return None
        except Exception as e:
            print(e)
            return None

    def get_all(self):
        return list(self.model.select())

    def filter(self, **filters):
        query = self.model.select()
        for field, value in filters.items():
            if not hasattr(self.model, field):
                raise ValueError(f"Field '{field}' does not exist on model {self.model.__name__}")
            query = query.where(getattr(self.model, field) == value)
        return list(query)

    def create(self, **data):
        with db.atomic():
            return self.model.create(**data)

    def create_bulk(self, data_list):
        """
        Create multiple records in bulk using insert_many for optimization.
        Args:
            data_list: List of dictionaries containing field-value pairs for each record.
        Returns:
            Number of rows inserted.
        """
        with db.atomic():
            return self.model.insert_many(data_list).execute()

    def update(self, obj, **data):
        for field, value in data.items():
            setattr(obj, field, value)
        with db.atomic():
            obj.save()
        return obj

    def delete(self, obj):
        with db.atomic():
            return obj.delete_instance()

    def count(self):
        return self.model.select().count()

    def to_dict(self, instance):
        """
        Convert a model instance to a dictionary suitable for JSON serialization.
        """
        data = {k: v for k, v in instance._data.items()}
        for key, value in data.items():
            if isinstance(value, (datetime, date)):
                data[key] = value.isoformat()
        return data

    def get_as_dict(self, **filters):
        """
        Retrieve a single record as a dictionary based on filters.
        """
        instance = self.get(**filters)
        if instance:
            return self.to_dict(instance)
        return None

    def get_all_as_dict(self):
        """
        Retrieve all records as a list of dictionaries.
        """
        return [self.to_dict(instance) for instance in self.get_all()]


class DeviceRepository(Repository):
    def __init__(self):
        super().__init__(Device)


class UserRepository(Repository):
    def __init__(self):
        super().__init__(User)


class AttendanceRepository(Repository):
    def __init__(self):
        super().__init__(Attendance)

    def cloud_format(self):
        """
        Return attendance records in a cloud-friendly dict format.
        """
        records = []
        for att in self.model.select().where(self.model.posted == False):
            if att.user and att.user.user_cloud_id:
                records.append({
                    'user_cloud_id': att.user.user_cloud_id,
                    'user_cloud_device_id': att.user.device_cloud_id,
                    'timestamp': att.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'punch': att.punch,
                    'status': att.status
                })
        return records


class SettingsRepository(Repository):
    def __init__(self):
        super().__init__(Settings)

    def get_settings(self):
        return self.get()

    def save_settings(self, **data):
        settings = self.get_settings()
        if settings:
            return self.update(settings, **data)
        return self.create(**data)
