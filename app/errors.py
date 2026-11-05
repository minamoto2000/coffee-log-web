from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Business-rule error raised by the service layer.

    Services do not depend on HTTP; the mapping to status codes lives here.
    """

    status_code = 500

    def __init__(self, detail):
        super().__init__(detail)
        self.detail = detail


class NotFoundError(AppError):
    status_code = 404


class EmptyUpdateError(AppError):
    status_code = 400


class ConflictError(AppError):
    """The request is valid but the current state forbids it (e.g. the plan
    already has trials)."""

    status_code = 409


class InvalidResourceError(AppError):
    """The resource would be invalid after the change (PATCH merge validation)."""

    status_code = 422


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
