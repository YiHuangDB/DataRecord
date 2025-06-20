import unittest
import os
import sys

# Add src to Python path to allow direct imports of modules like src.adapters.memory_storage
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

if __name__ == "__main__":
    # Discover tests in the 'tests' directory from the root directory
    # Assumes run_tests.py is in the root directory of the project.
    loader = unittest.TestLoader()

    # If you want to run all tests from the 'tests' directory and its subdirectories:
    suite = loader.discover(start_dir='tests', pattern='test_*.py', top_level_dir='.')

    # Example: To run tests only for a specific module or sub-directory
    # suite = loader.discover(start_dir='tests/adapters', pattern='test_memory_storage.py', top_level_dir='.')
    # suite = loader.discover(start_dir='tests/adapters', pattern='test_*.py', top_level_dir='.')


    runner = unittest.TextTestRunner(verbosity=2) # Increased verbosity
    result = runner.run(suite)

    # Exit with a non-zero status if tests failed
    if not result.wasSuccessful():
        exit(1)
