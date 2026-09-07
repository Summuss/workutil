"""Evidence — one round of verification, delivered as one xlsx. See CONTEXT.md."""

from app.modules.evidence import models as models  # noqa: F401  — registers ORM tables
from app.modules.evidence.router import router as evidence_router

__all__ = ["evidence_router"]
