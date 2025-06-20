"""
SQLAlchemy-based database storage adapter.

This adapter uses SQLAlchemy to interact with a relational database (e.g., SQLite, PostgreSQL).
It defines an `ItemDB` model that maps to an "items" table in the database.
Data persistence is managed by the underlying database system.
"""
import uuid
from typing import List, Optional, Dict, Any
import os

from sqlalchemy import create_engine, Column, String, JSON # Text was imported but not used.
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

from src.core.storage_interface import StorageInterface

Base = declarative_base()

class ItemDB(Base):
    """SQLAlchemy model representing an item in the 'items' table."""
    __tablename__ = "items"

    id = Column(String, primary_key=True, index=True, doc="Unique identifier for the item (UUID string)")
    name = Column(String, nullable=False, doc="Name of the item")
    description = Column(String, nullable=True, doc="Optional description of the item")
    data = Column(JSON, doc="Flexible JSON field for arbitrary data associated with the item")

    def to_dict(self) -> Dict[str, Any]:
        """Converts the ORM object to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "data": self.data,
        }

class DatabaseStorage(StorageInterface):
    """
    Implements StorageInterface using SQLAlchemy for database interaction.

    Attributes:
        engine: The SQLAlchemy engine instance.
        SessionLocal: A factory for creating database sessions.
    """
    def __init__(self, db_url: str):
        """
        Initializes the DatabaseStorage adapter.

        Args:
            db_url: The database connection URL (e.g., "sqlite:///./data/items.db").
        """
        db_dir = None
        if "sqlite:///" in db_url: # Check if it's a file-based SQLite DB
            # Extract directory path from db_url like "sqlite:///./data/items.db" or "sqlite:///data/items.db"
            path_part = db_url.split("sqlite:///", 1)[1]
            if path_part.startswith("./"):
                path_part = path_part[2:]
            db_dir = os.path.dirname(path_part)

        if db_dir and not os.path.exists(db_dir): # Ensure directory exists if it's part of the path
             os.makedirs(db_dir, exist_ok=True)

        self.engine = create_engine(db_url)
        Base.metadata.create_all(bind=self.engine) # Create tables if they don't exist
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        print(f"DatabaseStorage initialized. DB URL: {db_url}")


    def _item_to_dict(self, item_db: ItemDB) -> Dict[str, Any]:
        """Converts an ItemDB ORM object to a dictionary. (Helper, same as ItemDB.to_dict)"""
        return item_db.to_dict()

    async def create(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a new item in the database.
        Generates a UUID for 'id' if not provided.
        """
        # Ensure 'id' is present, or generate one.
        item_id = item_data.get('id', uuid.uuid4().hex)

        db_item = ItemDB(
            id=item_id, # Use the determined item_id
            name=item_data.get('name'), # Let model handle nullable for description/data
            description=item_data.get('description'),
            data=item_data.get('data', {}) # Default to empty dict for JSON field
        )
        session: Session = self.SessionLocal()
        try:
            session.add(db_item)
            session.commit()
            session.refresh(db_item)
            return self._item_to_dict(db_item)
        finally:
            session.close()

    async def read_all(self) -> List[Dict[str, Any]]:
        """Retrieves all items from the database."""
        session: Session = self.SessionLocal()
        try:
            items_db = session.query(ItemDB).all()
            return [self._item_to_dict(item) for item in items_db]
        finally:
            session.close()

    async def read_one(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single item by ID from the database."""
        session: Session = self.SessionLocal()
        try:
            item_db = session.query(ItemDB).filter(ItemDB.id == item_id).first()
            if item_db:
                return self._item_to_dict(item_db)
            return None
        finally:
            session.close()

    async def update(self, item_id: str, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Updates an existing item in the database.
        Fields in item_data are applied to the found item. 'id' in item_data is ignored.
        """
        session: Session = self.SessionLocal()
        try:
            db_item = session.query(ItemDB).filter(ItemDB.id == item_id).first()
            if db_item:
                # Update fields from item_data, excluding 'id' as it's fixed by item_id
                for key, value in item_data.items():
                    if key != 'id' and hasattr(db_item, key):
                        setattr(db_item, key, value)

                session.commit()
                session.refresh(db_item)
                return self._item_to_dict(db_item)
            return None
        finally:
            session.close()

    async def delete(self, item_id: str) -> bool:
        """Deletes an item by ID from the database."""
        session: Session = self.SessionLocal()
        try:
            db_item = session.query(ItemDB).filter(ItemDB.id == item_id).first()
            if db_item:
                session.delete(db_item)
                session.commit()
                return True
            return False
        finally:
            session.close()
