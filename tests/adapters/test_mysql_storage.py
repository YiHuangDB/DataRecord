import unittest
import os
import asyncio
from sqlalchemy import create_engine #, text # Not using text directly here
from sqlalchemy.orm import sessionmaker
from src.adapters.mysql_storage import MySQLStorage, Base as MySQLBase
from sqlalchemy.exc import OperationalError, SQLAlchemyError # For catching specific errors

class TestMySQLStorage(unittest.IsolatedAsyncioTestCase):
    db_url = os.getenv("TEST_MYSQL_URL")
    storage: MySQLStorage
    engine = None # Class level engine for setup/teardown

    @classmethod
    def setUpClass(cls):
        if not cls.db_url:
            raise unittest.SkipTest("TEST_MYSQL_URL environment variable not set. Skipping MySQL tests.")

        print(f"MySQL Test URL: {cls.db_url}")
        try:
            cls.engine = create_engine(cls.db_url)
            with cls.engine.connect() as connection: # Test basic connectivity
                pass
            # Create all tables defined in MySQLBase (i.e., items_mysql)
            MySQLBase.metadata.create_all(bind=cls.engine)
            print(f"MySQL tables created using engine: {cls.engine}")
        except OperationalError as e:
            # OperationalError is common for connection issues (host, credentials, db not found)
            raise unittest.SkipTest(f"Cannot connect to MySQL database at {cls.db_url}. Skipping tests. Error: {e}")
        except SQLAlchemyError as e: # Catch other SQLAlchemy errors during setup
            raise unittest.SkipTest(f"SQLAlchemy error during MySQL setup at {cls.db_url}. Skipping tests. Error: {e}")


    @classmethod
    def tearDownClass(cls):
        if cls.engine:
            try:
                # Drop all tables defined in MySQLBase
                MySQLBase.metadata.drop_all(bind=cls.engine)
                print(f"MySQL tables dropped using engine: {cls.engine}")
            except Exception as e:
                print(f"Error tearing down MySQL test tables: {e}")
            finally:
                cls.engine.dispose() # Close all connections associated with the engine


    async def setUp(self):
        if not self.db_url: # Should be caught by setUpClass but as a safeguard
            self.skipTest("TEST_MYSQL_URL not set (skipped in setUp).")

        # Each test method will get a new storage instance,
        # ensuring they use the class-level engine for table structure but manage sessions independently.
        self.storage = MySQLStorage(db_url=self.db_url)

        # Clean all data from tables before each test method
        # This is crucial for test isolation.
        async_session = self.storage.SessionLocal()
        try:
            for table in reversed(MySQLBase.metadata.sorted_tables):
                await asyncio.get_event_loop().run_in_executor(None, lambda: async_session.execute(table.delete()))
            await asyncio.get_event_loop().run_in_executor(None, async_session.commit)
        except SQLAlchemyError as e:
            await asyncio.get_event_loop().run_in_executor(None, async_session.rollback)
            print(f"Warning: Could not clear MySQL tables before test: {e}")
            # Depending on the error, might want to fail or skip the test
            self.skipTest(f"Failed to clear MySQL tables before test: {e}")
        finally:
            await asyncio.get_event_loop().run_in_executor(None, async_session.close)


    async def test_create_item(self):
        item_data = {"name": "MySQL Test Item", "description": "A test item for MySQL", "data": {"key": "value"}}
        created_item = await self.storage.create(item_data)
        self.assertIsNotNone(created_item.get("id"))
        self.assertEqual(created_item["name"], item_data["name"])
        self.assertEqual(created_item["description"], item_data["description"])
        self.assertEqual(created_item["data"], item_data["data"])

        # Verify by reading
        retrieved_item = await self.storage.read_one(created_item["id"])
        self.assertEqual(retrieved_item, created_item)


    async def test_read_all_items_empty(self):
        items = await self.storage.read_all()
        self.assertEqual(len(items), 0)

    async def test_read_all_items_multiple(self):
        item1 = await self.storage.create({"name": "MySQL Item 1", "data": {"val":1}})
        item2 = await self.storage.create({"name": "MySQL Item 2", "data": {"val":2}})
        items = await self.storage.read_all()
        self.assertEqual(len(items), 2)
        # Check if created items are present (order might not be guaranteed)
        retrieved_ids = {item["id"] for item in items}
        self.assertIn(item1["id"], retrieved_ids)
        self.assertIn(item2["id"], retrieved_ids)


    async def test_read_one_item(self):
        created = await self.storage.create({"name": "Specific MySQL Item", "description": "Details", "data": {"s_key": "s_val"}})
        item_id = created["id"]
        read_item = await self.storage.read_one(item_id)
        self.assertIsNotNone(read_item)
        self.assertEqual(read_item["name"], "Specific MySQL Item")
        self.assertEqual(read_item["description"], "Details")
        self.assertEqual(read_item["data"], {"s_key": "s_val"})


    async def test_read_nonexistent_item(self):
        read_item = await self.storage.read_one("nonexistent-mysql-id")
        self.assertIsNone(read_item)

    async def test_update_item(self):
        created = await self.storage.create({"name": "Original MySQL Name", "description": "Original Desc", "data": {"k_orig": "v_orig"}})
        item_id = created["id"]

        updated_data = {"name": "Updated MySQL Name", "description": "Updated Desc", "data": {"k_new": "v_new"}}
        updated_item = await self.storage.update(item_id, updated_data)

        self.assertIsNotNone(updated_item)
        self.assertEqual(updated_item["id"], item_id) # ID should remain the same
        self.assertEqual(updated_item["name"], "Updated MySQL Name")
        self.assertEqual(updated_item["description"], "Updated Desc")
        self.assertEqual(updated_item["data"], {"k_new": "v_new"})

        # Verify by reading again
        retrieved_item = await self.storage.read_one(item_id)
        self.assertEqual(retrieved_item["name"], "Updated MySQL Name")
        self.assertEqual(retrieved_item["description"], "Updated Desc")


    async def test_update_nonexistent_item(self):
        updated_item = await self.storage.update("nonexistent-mysql-id", {"name": "New Name"})
        self.assertIsNone(updated_item)

    async def test_delete_item(self):
        created = await self.storage.create({"name": "To Be Deleted MySQL", "data": {}})
        item_id = created["id"]

        # Ensure it exists before delete
        self.assertIsNotNone(await self.storage.read_one(item_id))

        deleted = await self.storage.delete(item_id)
        self.assertTrue(deleted)

        # Ensure it's gone
        read_item = await self.storage.read_one(item_id)
        self.assertIsNone(read_item)


    async def test_delete_nonexistent_item(self):
        deleted = await self.storage.delete("nonexistent-mysql-id")
        self.assertFalse(deleted)

# This allows running the test file directly, though 'python run_tests.py' is preferred.
if __name__ == '__main__':
    unittest.main()
