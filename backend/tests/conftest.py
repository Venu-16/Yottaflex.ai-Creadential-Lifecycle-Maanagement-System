import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://unused:unused@localhost/unused")
os.environ.setdefault("SECRET_KEY", "test-only-placeholder-secret")
