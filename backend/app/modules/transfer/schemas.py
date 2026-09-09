from pydantic import BaseModel


class Manifest(BaseModel):
    version: str
    alembic_revision: str
    exported_at: str
    table_counts: dict[str, int]


class ImportResponse(BaseModel):
    restart_required: bool = True
    backup_file: str
    message: str
