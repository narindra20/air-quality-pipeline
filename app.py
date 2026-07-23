import os
from sqlalchemy import create_engine

engine = create_engine(
    f"postgresql+psycopg2://{os.getenv('DB_USER1')}:"
    f"{os.getenv('DB_PASSWORD1')}@"
    f"{os.getenv('DB_HOST1')}:"
    f"{os.getenv('DB_PORT1')}/"
    f"{os.getenv('DB_NAME1')}?sslmode=require"
)