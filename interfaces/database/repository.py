from datetime import datetime, date

from peewee import DoesNotExist
from interfaces.database.models import db, Device, User, Attendance, Settings


class Repository:
    """
    Generic repository for basic CRUD operations using Peewee.
    Returns Query objects for chaining, not plain lists.
    """
    def __init__(self, model):
        self.model = model

    def get(self, **filters):
        """Fetch a single instance matching filters or return None."""
        try:
            return self.model.get(**filters)
        except DoesNotExist:
            return None

    def exists(self, **filters) -> bool:
        """Check if any record exists matching the filters."""
        query = self.model.select()
        for field, value in filters.items():
            if not hasattr(self.model, field):
                raise ValueError(f"Field '{field}' does not exist on model {self.model.__name__}")
            query = query.where(getattr(self.model, field) == value)
        return query.exists()

    def get_all(self):
        """Return a Peewee Query for all records (use .list() if you need a list)."""
        return self.model.select()

    def filter(self, **filters):
        """Return a Query filtered by the given field=value pairs."""
        query = self.model.select()
        for field, value in filters.items():
            if not hasattr(self.model, field):
                raise ValueError(f"Field '{field}' does not exist on model {self.model.__name__}")
            query = query.where(getattr(self.model, field) == value)
        return query

    def create(self, **data):
        """Insert a new record and return the created instance."""
        with db.atomic():
            return self.model.create(**data)

    def create_bulk(self, data_list):
        """Bulk-insert multiple dicts, returns number of rows inserted."""
        if not data_list:
            return 0
        with db.atomic():
            return self.model.insert_many(data_list).execute()

    def update(self, instance, **data):
        """Update fields on an instance and save."""
        for field, value in data.items():
            setattr(instance, field, value)
        with db.atomic():
            instance.save()
        return instance

    def update_bulk(self, data, ids=None, **filters):
        """
        Update multiple records matching either a list of IDs or filters.
        Returns number of rows updated.
        """
        if not ids and not filters:
            raise ValueError("Either 'ids' or 'filters' must be provided for bulk update")
        query = self.model.update(**data)
        if ids:
            # handles primary-key fields automatically
            query = query.where(self.model._meta.primary_key.in_(ids))
        else:
            for field, value in filters.items():
                if not hasattr(self.model, field):
                    raise ValueError(f"Field '{field}' does not exist on model {self.model.__name__}")
                query = query.where(getattr(self.model, field) == value)
        with db.atomic():
            return query.execute()

    def delete(self, instance):
        """Delete a single instance."""
        with db.atomic():
            return instance.delete_instance()

    def delete_bulk(self, **filters):
        """Delete records matching filters, returns number of rows deleted."""
        if not filters:
            raise ValueError("Filters must be provided for bulk delete")
        query = self.model.delete()
        for field, value in filters.items():
            if not hasattr(self.model, field):
                raise ValueError(f"Field '{field}' does not exist on model {self.model.__name__}")
            query = query.where(getattr(self.model, field) == value)
        with db.atomic():
            return query.execute()

    def count(self, **filters) -> int:
        """Count all or filtered records."""
        if filters:
            return self.filter(**filters).count()
        return self.model.select().count()

    def to_dict(self, instance):
        """Convert a model instance to a JSON-serializable dict."""
        data = {k: v for k, v in instance._data.items()}
        for key, value in data.items():
            if isinstance(value, (datetime, date)):
                data[key] = value.isoformat()
        return data

    def get_as_dict(self, **filters):
        """Retrieve a single record as a dict, or None if not found."""
        inst = self.get(**filters)
        return self.to_dict(inst) if inst else None


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
        """Return attendance records in a cloud-friendly format."""
        records = []
        for att in self.filter(posted=False):
            if att.user and att.user.user_cloud_id:
                records.append({
                    "device_id": att.device_id,
                    "timestamp": att.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "punch": att.punch,
                    "status": att.status,
                    "user_id": att.user_id,
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
