# interfaces/database/base_repository.py
"""
Enhanced base repository with common patterns and error handling.
Provides a foundation for all repository classes.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from peewee import DoesNotExist, IntegrityError

from interfaces.database.models import db
from core.exceptions import DatabaseError


class BaseRepository:
    """
    Enhanced base repository for common CRUD operations with error handling.
    Provides a foundation for all repository classes.
    """

    def __init__(self, model):
        """Initialize repository with a Peewee model."""
        self.model = model
        self.logger = logging.getLogger(f"{__name__}.{model.__name__}")

    def get(self, **filters) -> Optional[Any]:
        """
        Get a single record by filters.
        
        Args:
            **filters: Field-value pairs to filter by
            
        Returns:
            Model instance or None if not found
        """
        try:
            return self.model.get(**filters)
        except DoesNotExist:
            return None
        except Exception as e:
            self.logger.error(f"Error getting record with filters {filters}: {e}")
            raise DatabaseError(f"Failed to get record: {str(e)}")

    def get_all(self) -> List[Any]:
        """
        Get all records.
        
        Returns:
            List of model instances
        """
        try:
            return list(self.model.select())
        except Exception as e:
            self.logger.error(f"Error getting all records: {e}")
            raise DatabaseError(f"Failed to get all records: {str(e)}")

    def filter(self, **filters) -> List[Any]:
        """
        Filter records by field-value pairs.
        
        Args:
            **filters: Field-value pairs to filter by
            
        Returns:
            List of matching model instances
        """
        try:
            query = self.model.select()
            for field, value in filters.items():
                if not hasattr(self.model, field):
                    raise ValueError(f"Field '{field}' does not exist on model {self.model.__name__}")
                query = query.where(getattr(self.model, field) == value)
            return list(query)
        except Exception as e:
            self.logger.error(f"Error filtering records with {filters}: {e}")
            raise DatabaseError(f"Failed to filter records: {str(e)}")

    def create(self, **data) -> Any:
        """
        Create a new record.
        
        Args:
            **data: Field-value pairs for the new record
            
        Returns:
            Created model instance
        """
        try:
            # Add timestamps if they exist in the model
            if hasattr(self.model, 'created_at') and 'created_at' not in data:
                data['created_at'] = datetime.now()
            if hasattr(self.model, 'updated_at') and 'updated_at' not in data:
                data['updated_at'] = datetime.now()
                
            with db.atomic():
                return self.model.create(**data)
        except IntegrityError as e:
            self.logger.error(f"Integrity error creating record: {e}")
            raise DatabaseError(f"Data integrity error: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error creating record: {e}")
            raise DatabaseError(f"Failed to create record: {str(e)}")

    def create_bulk(self, data_list: List[Dict]) -> int:
        """
        Create multiple records in bulk.
        
        Args:
            data_list: List of dictionaries containing field-value pairs
            
        Returns:
            Number of records created
        """
        try:
            # Add timestamps to all records
            for data in data_list:
                if hasattr(self.model, 'created_at') and 'created_at' not in data:
                    data['created_at'] = datetime.now()
                if hasattr(self.model, 'updated_at') and 'updated_at' not in data:
                    data['updated_at'] = datetime.now()
                    
            with db.atomic():
                return self.model.insert_many(data_list).execute()
        except Exception as e:
            self.logger.error(f"Error creating bulk records: {e}")
            raise DatabaseError(f"Failed to create bulk records: {str(e)}")

    def update(self, obj: Any, **data) -> Any:
        """
        Update an existing record.
        
        Args:
            obj: Model instance to update
            **data: Field-value pairs to update
            
        Returns:
            Updated model instance
        """
        try:
            # Add updated_at timestamp if it exists in the model
            if hasattr(self.model, 'updated_at') and 'updated_at' not in data:
                data['updated_at'] = datetime.now()
                
            for field, value in data.items():
                setattr(obj, field, value)
            with db.atomic():
                obj.save()
            return obj
        except IntegrityError as e:
            self.logger.error(f"Integrity error updating record: {e}")
            raise DatabaseError(f"Data integrity error: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error updating record: {e}")
            raise DatabaseError(f"Failed to update record: {str(e)}")

    def update_bulk(self, data: Dict, ids: Optional[List[int]] = None, **filters) -> int:
        """
        Update multiple records.
        
        Args:
            data: Dictionary of field-value pairs to update
            ids: Optional list of record IDs to update
            **filters: Optional field-value pairs to filter records
            
        Returns:
            Number of records updated
        """
        try:
            if not ids and not filters:
                raise ValueError("Either 'ids' or 'filters' must be provided for bulk update")

            # Add updated_at timestamp if it exists in the model
            if hasattr(self.model, 'updated_at') and 'updated_at' not in data:
                data['updated_at'] = datetime.now()

            query = self.model.update(**data)
            if ids:
                query = query.where(self.model.id.in_(ids))
            elif filters:
                for field, value in filters.items():
                    if not hasattr(self.model, field):
                        raise ValueError(f"Field '{field}' does not exist on model {self.model.__name__}")
                    query = query.where(getattr(self.model, field) == value)

            with db.atomic():
                return query.execute()
        except Exception as e:
            self.logger.error(f"Error updating bulk records: {e}")
            raise DatabaseError(f"Failed to update bulk records: {str(e)}")

    def delete(self, obj: Any) -> bool:
        """
        Delete a record.
        
        Args:
            obj: Model instance to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            with db.atomic():
                return obj.delete_instance()
        except Exception as e:
            self.logger.error(f"Error deleting record: {e}")
            raise DatabaseError(f"Failed to delete record: {str(e)}")

    def delete_bulk(self, **filters) -> int:
        """
        Delete multiple records.
        
        Args:
            **filters: Field-value pairs to filter records for deletion
            
        Returns:
            Number of records deleted
        """
        try:
            if not filters:
                raise ValueError("Filters must be provided for bulk delete")

            query = self.model.delete()
            for field, value in filters.items():
                if not hasattr(self.model, field):
                    raise ValueError(f"Field '{field}' does not exist on model {self.model.__name__}")
                query = query.where(getattr(self.model, field) == value)

            with db.atomic():
                return query.execute()
        except Exception as e:
            self.logger.error(f"Error deleting bulk records: {e}")
            raise DatabaseError(f"Failed to delete bulk records: {str(e)}")

    def count(self) -> int:
        """
        Count total records.
        
        Returns:
            Number of records
        """
        try:
            return self.model.select().count()
        except Exception as e:
            self.logger.error(f"Error counting records: {e}")
            raise DatabaseError(f"Failed to count records: {str(e)}")

    def exists(self, **filters) -> bool:
        """
        Check if any record exists with given filters.
        
        Args:
            **filters: Field-value pairs to filter by
            
        Returns:
            True if record exists, False otherwise
        """
        try:
            return self.model.select().where(**filters).exists()
        except Exception as e:
            self.logger.error(f"Error checking existence with filters {filters}: {e}")
            raise DatabaseError(f"Failed to check existence: {str(e)}")

    def to_dict(self, instance: Any) -> Dict:
        """
        Convert a model instance to a dictionary.
        
        Args:
            instance: Model instance
            
        Returns:
            Dictionary representation of the instance
        """
        try:
            return {
                field.name: getattr(instance, field.name) 
                for field in instance._meta.fields
            }
        except Exception as e:
            self.logger.error(f"Error converting instance to dict: {e}")
            raise DatabaseError(f"Failed to convert to dictionary: {str(e)}")

    def get_as_dict(self, **filters) -> Optional[Dict]:
        """
        Get a single record as a dictionary.
        
        Args:
            **filters: Field-value pairs to filter by
            
        Returns:
            Dictionary representation or None if not found
        """
        try:
            instance = self.get(**filters)
            return self.to_dict(instance) if instance else None
        except Exception as e:
            self.logger.error(f"Error getting record as dict with filters {filters}: {e}")
            raise DatabaseError(f"Failed to get record as dictionary: {str(e)}")

    def get_or_create(self, defaults: Optional[Dict] = None, **filters) -> tuple:
        """
        Get an existing record or create a new one.
        
        Args:
            defaults: Default values for new record creation
            **filters: Field-value pairs to filter by
            
        Returns:
            Tuple of (instance, created) where created is a boolean
        """
        try:
            defaults = defaults or {}
            instance = self.get(**filters)
            if instance:
                return instance, False
            else:
                # Merge filters with defaults
                data = {**filters, **defaults}
                return self.create(**data), True
        except Exception as e:
            self.logger.error(f"Error in get_or_create with filters {filters}: {e}")
            raise DatabaseError(f"Failed to get or create record: {str(e)}")

    def update_or_create(self, defaults: Optional[Dict] = None, **filters) -> tuple:
        """
        Update an existing record or create a new one.
        
        Args:
            defaults: Default values for new record creation
            **filters: Field-value pairs to filter by
            
        Returns:
            Tuple of (instance, created) where created is a boolean
        """
        try:
            defaults = defaults or {}
            instance = self.get(**filters)
            if instance:
                return self.update(instance, **defaults), False
            else:
                # Merge filters with defaults
                data = {**filters, **defaults}
                return self.create(**data), True
        except Exception as e:
            self.logger.error(f"Error in update_or_create with filters {filters}: {e}")
            raise DatabaseError(f"Failed to update or create record: {str(e)}")