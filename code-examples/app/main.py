import json
import logging
import os
import time
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send


logger = logging.getLogger("cynbit_reference")
DEFAULT_MAX_INQUIRY_BODY_BYTES = 16 * 1024


class _RequestBodyTooLarge(Exception):
    pass


class RequestBodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if (
            scope["type"] != "http"
            or scope["path"] != "/inquiries"
            or scope["method"] != "POST"
        ):
            await self.app(scope, receive, send)
            return

        request_id = str(uuid4())
        content_length = next(
            (
                value
                for name, value in scope["headers"]
                if name.lower() == b"content-length"
            ),
            None,
        )
        if content_length is not None and int(content_length) > self.max_bytes:
            await self._send_too_large(send, request_id)
            return

        total_bytes = 0
        exceeded_limit = False
        messages: list[Message] = []

        async def receive_limited() -> Message:
            nonlocal total_bytes, exceeded_limit
            message = await receive()
            if message["type"] == "http.request":
                total_bytes += len(message.get("body", b""))
                if total_bytes > self.max_bytes:
                    exceeded_limit = True
                    raise _RequestBodyTooLarge
            return message

        async def buffer_send(message: Message) -> None:
            messages.append(message)

        try:
            await self.app(scope, receive_limited, buffer_send)
        except _RequestBodyTooLarge:
            pass

        if exceeded_limit:
            await self._send_too_large(send, request_id)
            return

        for message in messages:
            await send(message)

    async def _send_too_large(self, send: Send, request_id: str) -> None:
        logger.warning(
            "request_rejected request_id=%s reason=body_too_large",
            request_id,
        )
        body = json.dumps(
            {
                "error": {
                    "code": "request_too_large",
                    "message": "The request body exceeds the allowed size.",
                },
                "request_id": request_id,
            }
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"x-request-id", request_id.encode()),
                    (
                        b"content-security-policy",
                        b"default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
                    ),
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"no-referrer"),
                    (
                        b"permissions-policy",
                        b"camera=(), microphone=(), geolocation=()",
                    ),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
                "more_body": False,
            }
        )


def _configured_request_body_limit() -> int:
    configured_value = os.environ.get(
        "CYNBIT_REFERENCE_MAX_BODY_BYTES",
        str(DEFAULT_MAX_INQUIRY_BODY_BYTES),
    )
    try:
        max_bytes = int(configured_value)
    except ValueError as error:
        raise RuntimeError(
            "CYNBIT_REFERENCE_MAX_BODY_BYTES must be a positive integer."
        ) from error
    if max_bytes <= 0:
        raise RuntimeError(
            "CYNBIT_REFERENCE_MAX_BODY_BYTES must be a positive integer."
        )
    return max_bytes


class InquiryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    organization: str | None = Field(default=None, max_length=150)
    industry: str | None = Field(default=None, max_length=100)
    message: str = Field(min_length=10, max_length=2000)

    @field_validator("name", "organization", "industry", "message", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class InquiryValidationResult(BaseModel):
    status: Literal["validated"] = "validated"
    request_id: str


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
) -> JSONResponse:
    error: dict[str, object] = {"code": code, "message": message}
    if details:
        error["details"] = details
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "request_id": getattr(request.state, "request_id", "unavailable"),
        },
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="Cynbit Assessment Reference API",
        description=(
            "A local validation-only example. It does not store or forward inquiries."
        ),
        version="1.0.0",
    )

    @app.middleware("http")
    async def add_request_context(request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_complete request_id=%s method=%s status=%s duration_ms=%.2f",
            request_id,
            request.method,
            response.status_code,
            (time.perf_counter() - started) * 1000,
        )
        return response

    @app.middleware("http")
    async def add_api_security_headers(request: Request, call_next):
        response = await call_next(request)
        if request.url.path in {"/health", "/inquiries"}:
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
            )
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Permissions-Policy"] = (
                "camera=(), microphone=(), geolocation=()"
            )
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = []
        for error in exc.errors():
            field = next(
                (str(part) for part in reversed(error["loc"]) if part != "body"),
                "request",
            )
            details.append({"field": field, "message": "invalid_value"})
        return _error_response(
            request,
            status_code=422,
            code="validation_error",
            message="The request did not pass validation.",
            details=details,
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        code, message = {
            404: ("not_found", "The requested resource was not found."),
            405: ("method_not_allowed", "The HTTP method is not allowed."),
        }.get(exc.status_code, ("request_rejected", "The request could not be completed."))
        return _error_response(
            request,
            status_code=exc.status_code,
            code=code,
            message=message,
        )

    @app.exception_handler(Exception)
    async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "request_failed request_id=%s error_type=%s",
            getattr(request.state, "request_id", "unavailable"),
            type(exc).__name__,
        )
        return _error_response(
            request,
            status_code=500,
            code="internal_error",
            message="An unexpected error occurred.",
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/inquiries", response_model=InquiryValidationResult)
    async def validate_inquiry(
        _inquiry: InquiryRequest, request: Request
    ) -> InquiryValidationResult:
        return InquiryValidationResult(request_id=request.state.request_id)

    app.add_middleware(
        RequestBodySizeLimitMiddleware,
        max_bytes=_configured_request_body_limit(),
    )
    return app


app = create_app()
