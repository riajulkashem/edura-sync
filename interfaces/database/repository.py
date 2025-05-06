from datetime import datetime, date

from peewee import DoesNotExist
from interfaces.database.models import db, Device, User, Attendance, Settings


class Repository:
    """
    Generic repository for basic CRUD operations using Peewee.
    Returns lists of model instances for `get_all` and `filter`.
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
                raise ValueError(
                    f"Field '{field}' does not exist on model {self.model.__name__}"
                )
            query = query.where(getattr(self.model, field) == value)
        return query.exists()

    def get_all(self):
        """Return a list of all records."""
        return list(self.model.select())

    def filter(self, **filters):
        """Return a list of records filtered by the given field=value pairs."""
        query = self.model.select()
        for field, value in filters.items():
            if not hasattr(self.model, field):
                raise ValueError(
                    f"Field '{field}' does not exist on model {self.model.__name__}"
                )
            query = query.where(getattr(self.model, field) == value)
        return list(query)

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

    def update_bulk(self, data, ids=None, filters=None, **filters_kwargs):
        """
        Update multiple records matching either a list of IDs, a filters dict, or keyword filters.
        Args:
            data: dict of field-value pairs to update.
            ids: optional list of primary-key values.
            filters: optional dict of field-value pairs for filtering.
            **filters_kwargs: additional field-value filters.
        Returns:
            Number of rows updated.
        """
        # Combine filters from dict and kwargs
        combined = {}
        if filters:
            combined.update(filters)
        combined.update(filters_kwargs)

        if not ids and not combined:
            raise ValueError(
                "Either 'ids', 'filters', or filter kwargs must be provided for bulk update"
            )

        query = self.model.update(**data)
        if ids:
            query = query.where(self.model._meta.primary_key.in_(ids))
        else:
            for field, value in combined.items():
                if not hasattr(self.model, field):
                    raise ValueError(
                        f"Field '{field}' does not exist on model {self.model.__name__}"
                    )
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
                raise ValueError(
                    f"Field '{field}' does not exist on model {self.model.__name__}"
                )
            query = query.where(getattr(self.model, field) == value)
        with db.atomic():
            return query.execute()

    def count(self, **filters) -> int:
        """Count all or filtered records."""
        if filters:
            return len(self.filter(**filters))
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
