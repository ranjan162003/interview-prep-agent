"""Domain errors raised by the service layer.

Routes never build HTTP errors by hand — `register_exception_handlers` maps
each of these to a status code and a consistent `{"detail": ...}` body.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class InterviewPrepError(Exception):
    """Base class for every expected, user-explainable failure."""

    status_code = 500

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidRequestError(InterviewPrepError):
    status_code = 400


class ResourceNotFoundError(InterviewPrepError):
    status_code = 404


class ProviderNotConnectedError(InterviewPrepError):
    """The chosen LLM provider has no usable login, API key, or local server."""

    status_code = 409


class ProviderCallError(InterviewPrepError):
    """The LLM provider was reachable but the call itself failed."""

    status_code = 502


class AgentResponseParseError(InterviewPrepError):
    """The LLM's reply couldn't be turned into the structure the agent expected."""

    status_code = 502


class ApiKeyStorageError(InterviewPrepError):
    status_code = 500


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InterviewPrepError)
    async def handle_interview_prep_error(_: Request, exc: InterviewPrepError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
