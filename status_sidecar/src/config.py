from browseterm_db.common.config import DBConfig
import os


DB_CONFIG: DBConfig = DBConfig(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    username=os.getenv("DB_USERNAME"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_DATABASE")
)

CONTAINER_ID: str = os.getenv("CONTAINER_ID")
