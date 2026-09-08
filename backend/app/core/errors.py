"""Structured error responses for HTTP endpoints."""

from typing import Any

from fastapi import HTTPException


def http_error(status_code: int, err: Any) -> HTTPException:
    """Build an HTTPException with structured code if available on the exception."""
    code = getattr(err, "code", None)
    message = str(err)
    if code is not None:
        return HTTPException(
            status_code=status_code,
            detail={"code": code, "message": message},
        )
    return HTTPException(status_code=status_code, detail=message)
