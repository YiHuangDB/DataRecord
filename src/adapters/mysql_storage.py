"""
SQLAlchemy-based MySQL storage adapter.

This adapter uses SQLAlchemy to interact with a MySQL database.
It defines an `ItemDB` model that maps to an "items_mysql" table.
Requires PyMySQL driver and a running MySQL server.
"""
from sqlalchemy import create_engine, Column, String, Text, JSON
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
import uuid

from src.core.storage_interface import StorageInterface, PaginatedDbResponse
from typing import List, Optional, Dict, Any

Base = declarative_base()

class ItemDB(Base):
    """SQLAlchemy model for items in MySQL, stored in 'items_mysql' table."""
    __tablename__ = "items_mysql"
    id = Column(String(36), primary_key=True, index=True, doc="Item unique identifier (UUID string)")
    name = Column(String(255), nullable=False, doc="Name of the item")
    description = Column(Text, nullable=True, doc="Optional textual description of the item")
    data = Column(JSON, doc="Flexible JSON field for arbitrary item data")

    def to_dict(self) -> Dict[str, Any]:
        """Converts the ORM object to a dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class MySQLStorage(StorageInterface):
    """
    Implements StorageInterface using SQLAlchemy for MySQL database interaction.
    """
    def __init__(self, db_url: str):
        """
        Initializes the MySQLStorage adapter.

        Args:
            db_url: The MySQL connection URL (e.g., "mysql+pymysql://user:pass@host:port/dbname").

        Raises:
            ConnectionError: If connection to MySQL fails or table creation fails.
        """
        try:
            self.engine = create_engine(db_url)
            Base.metadata.create_all(bind=self.engine)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            with self.engine.connect() as connection:
                pass

            print(f"MySQLStorage initialized with DB URL: {db_url} and table '{ItemDB.__tablename__}'")
        except SQLAlchemyError as e:
            print(f"Error initializing MySQLStorage: {e}")
            raise ConnectionError(f"Failed to connect or initialize MySQL database at {db_url}: {e}")


    async def create(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new item in the MySQL database."""
        session: Session = self.SessionLocal()
        try:
            item_id = item_data.get('id', uuid.uuid4().hex)
            # Filter item_data for valid ItemDB columns
            valid_data = {k: v for k, v in item_data.items() if hasattr(ItemDB, k) and k != 'id'}
            db_item = ItemDB(id=item_id, **valid_data)

            session.add(db_item)
            session.commit()
            session.refresh(db_item)
            return db_item.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise RuntimeError(f"Error creating item in MySQL: {e}")
        finally:
            session.close()

    async def read_all(self, offset: int = 0, limit: int = 100) -> PaginatedDbResponse:
        """
        Retrieves items from the MySQL database with pagination using SQLAlchemy.

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
            print(f"Error reading items from MySQL database: {e}")
            raise RuntimeError(f"Error reading items from MySQL database: {e}")
        finally:
            session.close()

    async def read_one(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single item by its ID from the MySQL database."""
        session: Session = self.SessionLocal()
        try:
            item = session.query(ItemDB).filter(ItemDB.id == item_id).first()
            return item.to_dict() if item else None
        except SQLAlchemyError as e:
            # session.rollback() # Not strictly necessary for read
            raise RuntimeError(f"Error reading item '{item_id}' from MySQL: {e}")
        finally:
            session.close()

    async def update(self, item_id: str, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates an existing item in the MySQL database."""
        session: Session = self.SessionLocal()
        try:
            db_item = session.query(ItemDB).filter(ItemDB.id == item_id).first()
            if db_item:
                for key, value in item_data.items():
                    if key != 'id' and hasattr(db_item, key):
                        setattr(db_item, key, value)
                session.commit()
                session.refresh(db_item)
                return db_item.to_dict()
            return None
        except SQLAlchemyError as e:
            session.rollback()
            raise RuntimeError(f"Error updating item '{item_id}' in MySQL: {e}")
        finally:
            session.close()

    async def delete(self, item_id: str) -> bool:
        """Deletes an item by its ID from the MySQL database."""
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
            raise RuntimeError(f"Error deleting item '{item_id}' from MySQL: {e}")
        finally:
            session.close()

    async def create_many(self, items_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Creates multiple items in batch in the MySQL database."""
        session: Session = self.SessionLocal()
        created_items_with_ids = []
        mappings_to_insert = []

        for item_data_single in items_data:
            item_id = item_data_single.get('id', uuid.uuid4().hex)

            # Prepare a dictionary that only includes keys corresponding to ItemDB columns
            valid_data_for_model = {k: v for k, v in item_data_single.items() if hasattr(ItemDB, k) and k != 'id'}
            mapping = {'id': item_id, **valid_data_for_model}

            mappings_to_insert.append(mapping)

            # Store a representation for return.
            return_item_data = item_data_single.copy()
            return_item_data['id'] = item_id
            created_items_with_ids.append(return_item_data)

        if not mappings_to_insert:
            return []

        try:
            # Use bulk_insert_mappings for potentially better performance with dicts.
            # ItemDB instances could also be created and session.add_all used.
            session.bulk_insert_mappings(ItemDB, mappings_to_insert)
            session.commit()
            return created_items_with_ids
        except SQLAlchemyError as e:
            session.rollback()
            raise RuntimeError(f"Error bulk creating items in MySQL: {e}")
        finally:
            session.close()

    async def export_all(self) -> List[Dict[str, Any]]:
        """Exports all items from the MySQL database."""
        session: Session = self.SessionLocal()
        try:
            all_db_items = session.query(ItemDB).all()
            return [item.to_dict() for item in all_db_items]
        except SQLAlchemyError as e:
            raise RuntimeError(f"Error exporting all items from MySQL: {e}")
        finally:
            session.close()
