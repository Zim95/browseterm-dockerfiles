"""Pytest configuration and fixtures for integration tests."""
import os
from browseterm_db.common.config import DBConfig


# Test Database configuration
# Uses production database config but with test database name
TEST_DB_CONFIG: DBConfig = DBConfig(
    host=os.getenv('DB_HOST', 'localhost'),
    port=int(os.getenv('DB_PORT', '5432')),
    username=os.getenv('DB_USERNAME', 'postgres'),
    password=os.getenv('DB_PASSWORD', 'postgres'),
    database=os.getenv('TEST_DB_DATABASE', 'browseterm_test')  # Only database is different
)

# Test Docker registry configuration (can be overridden via environment)
TEST_REPO_NAME: str = os.getenv('REPO_NAME', '')
TEST_REPO_PASSWORD: str = os.getenv('REPO_PASSWORD', '')
