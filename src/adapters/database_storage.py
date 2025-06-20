"""
SQLAlchemy-based database storage adapter.

This adapter uses SQLAlchemy to interact with a relational database (e.g., SQLite, PostgreSQL).
It defines an `ItemDB` model that maps to an "items" table in the database.
Data persistence is managed by the underlying database system.
"""
import uuid
from typing import List, Optional, Dict, Any
import os

from sqlalchemy import create_engine, Column, String, JSON
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError

from src.core.storage_interface import StorageInterface, PaginatedDbResponse

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
    Implements StorageInterface using SQLAlchemy for database interaction (typically SQLite).

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
        if "sqlite:///" in db_url:
            path_part = db_url.split("sqlite:///", 1)[1]
            if path_part.startswith("./"):
                path_part = path_part[2:]
            db_dir = os.path.dirname(path_part)

        if db_dir and not os.path.exists(db_dir):
             os.makedirs(db_dir, exist_ok=True)

        self.engine = create_engine(db_url)
        Base.metadata.create_all(bind=self.engine)
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
        item_id = item_data.get('id', uuid.uuid4().hex)

        db_item = ItemDB(
            id=item_id,
            name=item_data.get('name'),
            description=item_data.get('description'),
            data=item_data.get('data', {})
        )
        session: Session = self.SessionLocal()
        try:
            session.add(db_item)
            session.commit()
            session.refresh(db_item)
            return self._item_to_dict(db_item)
        except SQLAlchemyError as e:
            session.rollback()
            raise RuntimeError(f"Error creating item in SQLite database: {e}")
        finally:
            session.close()

    async def read_all(self, offset: int = 0, limit: int = 100) -> PaginatedDbResponse:
        """
        Retrieves items from the SQLite database with pagination using SQLAlchemy.

        Args:
            offset: The number of items to skip (SQL OFFSET).
            limit: The maximum number of items to return (SQL LIMIT).

        Returns:
            A dictionary conforming to PaginatedDbResponse, containing the
            paginated list of items, total count of all items in the table,
            the offset used, and the limit used.

        Raises:
            RuntimeError: If a database error occurs during the read operation.
        """
        session: Session = self.SessionLocal()
        try:
            total_count = session.query(ItemDB).count()

            items_db = session.query(ItemDB).offset(offset).limit(limit).all()

            items_dict = [item.to_dict() for item in items_db]

            return {
                "items": items_dict,
                "total_count": total_count,
                "offset": offset,
                "limit": limit,
            }
        except SQLAlchemyError as e:
            print(f"Error reading items from SQLite database: {e}")
            raise RuntimeError(f"Error reading items from SQLite database: {e}")
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
        except SQLAlchemyError as e:
            session.rollback()
            raise RuntimeError(f"Error reading item {item_id} from SQLite database: {e}")
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
                for key, value in item_data.items():
                    if key != 'id' and hasattr(db_item, key):
                        setattr(db_item, key, value)

                session.commit()
                session.refresh(db_item)
                return self._item_to_dict(db_item)
            return None
        except SQLAlchemyError as e:
            session.rollback()
            raise RuntimeError(f"Error updating item {item_id} in SQLite database: {e}")
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
        except SQLAlchemyError as e:
            session.rollback()
            raise RuntimeError(f"Error deleting item {item_id} from SQLite database: {e}")
        finally:
            session.close()
