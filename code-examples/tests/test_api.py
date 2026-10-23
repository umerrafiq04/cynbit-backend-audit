import asyncio
import logging

from fastapi.testclient import TestClient
from pytest import LogCaptureFixture, MonkeyPatch, mark, raises

from main import DEFAULT_MAX_INQUIRY_BODY_BYTES, create_app


def test_valid_inquiry_is_validated_and_not_echoed() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/inquiries",
        json={
            "name": "  Alex Rivera  ",
            "email": "  alex@example.com ",
            "organization": " Example Org ",
            "industry": " Software ",
            "message": "  Please contact me about a project.  ",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "validated"
    assert response.headers["x-request-id"] == response.json()["request_id"]
    assert "alex@example.com" not in response.text


def test_missing_required_field_has_consistent_validation_error() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/inquiries",
        json={"name": "Alex Rivera", "email": "alex@example.com"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["message"] == (
        "The request did not pass validation."
    )
    assert any(
        detail["field"] == "message"
        for detail in response.json()["error"]["details"]
    )


def test_invalid_email_and_oversized_message_are_rejected() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/inquiries",
        json={
            "name": "Alex Rivera",
            "email": "not-an-email",
            "message": "x" * 2001,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert {item["field"] for item in response.json()["error"]["details"]} >= {
        "email",
        "message",
    }
    assert "not-an-email" not in response.text
    assert "x" * 100 not in response.text


def test_blank_name_after_trimming_is_rejected() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/inquiries",
        json={
            "name": "   ",
            "email": "alex@example.com",
            "message": "Please contact me about a project.",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@mark.parametrize(
    ("field", "value"),
    [
        ("name", ""),
        ("name", " \t "),
        ("message", ""),
        ("message", " \t "),
    ],
)
def test_empty_and_whitespace_required_text_fields_are_rejected(
    field: str, value: str
) -> None:
    payload = {
        "name": "Alex Rivera",
        "email": "alex@example.com",
        "message": "Please contact me about a project.",
    }
    payload[field] = value

    response = TestClient(create_app()).post("/inquiries", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert any(item["field"] == field for item in response.json()["error"]["details"])


def test_unexpected_error_returns_generic_json_without_exception_detail(
    caplog: LogCaptureFixture,
) -> None:
    app = create_app()

    @app.get("/test-only/internal-error")
    async def fail_for_test() -> None:
        raise RuntimeError("sensitive internal detail")

    client = TestClient(app, raise_server_exceptions=False)
    with caplog.at_level(logging.ERROR, logger="cynbit_reference"):
        response = client.get("/test-only/internal-error")

    assert response.status_code == 500
    assert response.json()["error"] == {
        "code": "internal_error",
        "message": "An unexpected error occurred.",
    }
    assert "sensitive internal detail" not in response.text
    assert "sensitive internal detail" not in caplog.text


def test_unknown_route_uses_standard_error_envelope() -> None:
    client = TestClient(create_app())

    response = client.get("/not-a-route")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_method_not_allowed_uses_standard_error_envelope() -> None:
    client = TestClient(create_app())

    response = client.get("/inquiries")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


def test_oversized_request_body_returns_413_with_request_id() -> None:
    response = TestClient(create_app()).post(
        "/inquiries",
        content=b"x" * (16 * 1024 + 1),
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert "x" * 100 not in response.text
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_streamed_oversized_body_is_rejected_without_content_length() -> None:
    app = create_app()
    messages = [
        {
            "type": "http.request",
            "body": b"x" * (16 * 1024 + 1),
            "more_body": False,
        }
    ]
    sent = []

    async def receive():
        return messages.pop(0)

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/inquiries",
        "raw_path": b"/inquiries",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "client": ("testclient", 1234),
        "server": ("testserver", 80),
    }

    asyncio.run(app(scope, receive, send))

    response_start = next(
        message for message in sent if message["type"] == "http.response.start"
    )
    response_body = next(
        message["body"]
        for message in sent
        if message["type"] == "http.response.body"
    )
    assert response_start["status"] == 413
    assert b"request_too_large" in response_body


def test_api_responses_include_security_headers_but_docs_remain_usable() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    docs_response = client.get("/docs")

    assert response.status_code == 200
    assert response.headers["content-security-policy"] == (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    )
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == (
        "camera=(), microphone=(), geolocation=()"
    )
    assert docs_response.status_code == 200
    assert "content-security-policy" not in docs_response.headers


@mark.parametrize("configured_value", ["0", "-10", "not-a-number"])
def test_invalid_body_limit_configuration_fails_at_startup(
    monkeypatch: MonkeyPatch, configured_value: str
) -> None:
    monkeypatch.setenv("CYNBIT_REFERENCE_MAX_BODY_BYTES", configured_value)

    with raises(RuntimeError, match="must be a positive integer"):
        create_app()


def test_default_body_limit_is_explicitly_bounded() -> None:
    assert DEFAULT_MAX_INQUIRY_BODY_BYTES == 16 * 1024


def test_environment_body_limit_is_applied(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CYNBIT_REFERENCE_MAX_BODY_BYTES", "128")

    response = TestClient(create_app()).post(
        "/inquiries",
        content=b"x" * 129,
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"


def test_malformed_json_uses_validation_error_envelope() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/inquiries",
        content='{"name":',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert "name" not in response.text


def test_non_object_json_is_rejected_without_reflecting_input() -> None:
    client = TestClient(create_app())

    response = client.post("/inquiries", json=["private-input"])

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "private-input" not in response.text


def test_wrong_field_types_and_extra_fields_are_rejected() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/inquiries",
        json={
            "name": ["Alex Rivera"],
            "email": "alex@example.com",
            "message": 123,
            "internal_note": "private-input",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert {item["field"] for item in response.json()["error"]["details"]} >= {
        "name",
        "message",
        "internal_note",
    }
    assert "private-input" not in response.text


def test_request_logs_do_not_include_submitted_personal_data(
    caplog: LogCaptureFixture,
) -> None:
    client = TestClient(create_app())
    name = "Private Person"
    email = "private.person@example.com"
    organization = "Confidential Example Org"
    message = "Please contact me about a confidential project."

    with caplog.at_level(logging.INFO, logger="cynbit_reference"):
        response = client.post(
            "/inquiries",
            json={
                "name": name,
                "email": email,
                "organization": organization,
                "message": message,
            },
        )

    assert response.status_code == 200
    assert name not in caplog.text
    assert email not in caplog.text
    assert organization not in caplog.text
    assert message not in caplog.text
