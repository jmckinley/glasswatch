"""
SQLAlchemy declarative base class for all models.

Provides common functionality and standard table naming.
"""
from sqlalchemy.ext.declarative import declarative_base, declared_attr


class CustomBase:
    """
    Custom base class for SQLAlchemy models.
    
    Provides:
    - Automatic table naming from class name
    - Common functionality for all models
    """
    
    @declared_attr
    def __tablename__(cls):
        """
        Generate table name from class name.
        
        CamelCase -> snake_case
        e.g., AssetVulnerability -> asset_vulnerability
        """
        name = cls.__name__
        # Handle simple cases
        table_name = ""
        for i, char in enumerate(name):
            if i > 0 and char.isupper() and name[i-1].islower():
                table_name += "_"
            table_name += char.lower()
        return table_name


# Create the declarative base
Base = declarative_base(cls=CustomBase)