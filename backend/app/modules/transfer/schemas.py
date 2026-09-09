from pydantic import BaseModel


class Manifest(BaseModel):
    version: str
    alembic_revision: str
    exported_at: str
    table_counts: dict[str, int]
