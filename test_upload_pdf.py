#!/usr/bin/env python3
"""Tests for upload_pdf.py.

Runs without a real network connection or API key by stubbing the
``anthropic`` package (if it is not installed) and monkey-patching
``anthropic.Anthropic`` on a per-test basis.

Run with:
    python3 -m unittest test_upload_pdf.py -v
or:
    python3 test_upload_pdf.py
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from unittest import mock


# ---------------------------------------------------------------------------
# Make sure there is *some* ``anthropic`` module available so that importing
# ``upload_pdf`` succeeds even in environments where the real SDK is missing.
# ---------------------------------------------------------------------------
if "anthropic" not in sys.modules:
    stub = types.ModuleType("anthropic")

    class _StubError(Exception):
        def __init__(self, message: str = "", *, status_code: int = 0) -> None:
            super().__init__(message)
            self.status_code = status_code

    # Mirror the public error classes imported by upload_pdf.
    for name in (
        "APIConnectionError",
        "APIStatusError",
        "APITimeoutError",
        "AuthenticationError",
        "BadRequestError",
        "InternalServerError",
        "NotFoundError",
        "PermissionDeniedError",
        "RateLimitError",
    ):
        setattr(stub, name, type(name, (_StubError,), {}))

    class _StubAnthropic:
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "Stub Anthropic client should be replaced via mock.patch in tests."
            )

    stub.Anthropic = _StubAnthropic
    sys.modules["anthropic"] = stub


# Import after the stub is in place.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import upload_pdf  # noqa: E402


PDF_MAGIC = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def _write_pdf(path: str, content: bytes = PDF_MAGIC) -> None:
    with open(path, "wb") as f:
        f.write(content)


class FakeFileObject:
    def __init__(self) -> None:
        self.id = "file_abc123"
        self.filename = "document.pdf"
        self.size_bytes = len(PDF_MAGIC)
        self.mime_type = "application/pdf"
        self.created_at = "2026-04-23T00:00:00Z"


class FakeFilesNamespace:
    def __init__(self, exc: Exception | None = None) -> None:
        self._exc = exc
        self.calls: list[dict] = []

    def upload(self, *, file):  # noqa: A002
        self.calls.append({"file": file})
        if self._exc is not None:
            raise self._exc
        return FakeFileObject()


class FakeBetaNamespace:
    def __init__(self, exc: Exception | None = None) -> None:
        self.files = FakeFilesNamespace(exc)


class FakeAnthropicClient:
    last_instance: "FakeAnthropicClient | None" = None

    def __init__(self, *args, **kwargs) -> None:
        self.init_args = args
        self.init_kwargs = kwargs
        self.beta = FakeBetaNamespace(kwargs.pop("_raise", None))
        FakeAnthropicClient.last_instance = self


def _client_factory(raise_exc: Exception | None = None):
    def factory(*args, **kwargs):
        client = FakeAnthropicClient(*args, **kwargs)
        client.beta = FakeBetaNamespace(raise_exc)
        FakeAnthropicClient.last_instance = client
        return client

    return factory


class ValidatePdfTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_valid_pdf_passes(self) -> None:
        path = os.path.join(self.tmp.name, "ok.pdf")
        _write_pdf(path)
        upload_pdf.validate_pdf(path)  # should not raise

    def test_missing_file(self) -> None:
        with self.assertRaises(FileNotFoundError):
            upload_pdf.validate_pdf(os.path.join(self.tmp.name, "nope.pdf"))

    def test_directory_path(self) -> None:
        with self.assertRaises(IsADirectoryError):
            upload_pdf.validate_pdf(self.tmp.name)

    def test_empty_file(self) -> None:
        path = os.path.join(self.tmp.name, "empty.pdf")
        open(path, "wb").close()
        with self.assertRaises(ValueError):
            upload_pdf.validate_pdf(path)

    def test_non_pdf_header(self) -> None:
        path = os.path.join(self.tmp.name, "fake.pdf")
        with open(path, "wb") as f:
            f.write(b"not a pdf at all")
        with self.assertRaises(ValueError):
            upload_pdf.validate_pdf(path)

    def test_unreadable_file(self) -> None:
        path = os.path.join(self.tmp.name, "locked.pdf")
        _write_pdf(path)
        os.chmod(path, 0)
        self.addCleanup(os.chmod, path, 0o644)
        # root can read anything, so skip in that case.
        if os.geteuid() == 0:
            self.skipTest("Running as root, chmod 000 does not block reads.")
        with self.assertRaises(PermissionError):
            upload_pdf.validate_pdf(path)

    def test_oversized_file(self) -> None:
        path = os.path.join(self.tmp.name, "big.pdf")
        with mock.patch.object(upload_pdf, "MAX_PDF_BYTES", 10):
            _write_pdf(path, PDF_MAGIC)  # > 10 bytes
            with self.assertRaises(ValueError):
                upload_pdf.validate_pdf(path)


class UploadPdfTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "document.pdf")
        _write_pdf(self.path)

    def test_upload_success_returns_file_object(self) -> None:
        with mock.patch.object(upload_pdf.anthropic, "Anthropic", _client_factory()):
            result = upload_pdf.upload_pdf(self.path, api_key="sk-test")
        self.assertEqual(result.id, "file_abc123")
        self.assertEqual(result.mime_type, "application/pdf")
        # Verify the SDK was called with a (filename, fileobj, mimetype) tuple.
        call = FakeAnthropicClient.last_instance.beta.files.calls[0]
        filename, fileobj, mimetype = call["file"]
        self.assertEqual(filename, "document.pdf")
        self.assertEqual(mimetype, "application/pdf")
        self.assertTrue(hasattr(fileobj, "read"))

    def test_upload_propagates_sdk_error(self) -> None:
        exc = upload_pdf.RateLimitError("slow down")
        with mock.patch.object(
            upload_pdf.anthropic, "Anthropic", _client_factory(raise_exc=exc)
        ):
            with self.assertRaises(upload_pdf.RateLimitError):
                upload_pdf.upload_pdf(self.path, api_key="sk-test")


class MainCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "document.pdf")
        _write_pdf(self.path)

    def _run_main(self, argv: list[str], *, raise_exc: Exception | None = None) -> tuple[int, str]:
        buf = io.StringIO()
        with mock.patch.object(
            upload_pdf.anthropic, "Anthropic", _client_factory(raise_exc=raise_exc)
        ):
            with redirect_stdout(buf):
                code = upload_pdf.main(argv)
        return code, buf.getvalue()

    def test_missing_api_key_returns_auth_error(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            code, _ = self._run_main([self.path])
        self.assertEqual(code, upload_pdf.EXIT_AUTH_ERROR)

    def test_successful_upload_returns_ok(self) -> None:
        code, stdout = self._run_main([self.path, "--api-key", "sk-test"])
        self.assertEqual(code, upload_pdf.EXIT_OK)
        self.assertIn("file_abc123", stdout)

    def test_nonexistent_file_returns_file_error(self) -> None:
        missing = os.path.join(self.tmp.name, "missing.pdf")
        code, _ = self._run_main([missing, "--api-key", "sk-test"])
        self.assertEqual(code, upload_pdf.EXIT_FILE_ERROR)

    def test_non_pdf_returns_bad_request(self) -> None:
        bad = os.path.join(self.tmp.name, "bad.pdf")
        with open(bad, "wb") as f:
            f.write(b"not a pdf")
        code, _ = self._run_main([bad, "--api-key", "sk-test"])
        self.assertEqual(code, upload_pdf.EXIT_BAD_REQUEST)

    def test_authentication_error_mapped(self) -> None:
        code, _ = self._run_main(
            [self.path, "--api-key", "sk-test"],
            raise_exc=upload_pdf.AuthenticationError("bad key"),
        )
        self.assertEqual(code, upload_pdf.EXIT_AUTH_ERROR)

    def test_rate_limit_mapped(self) -> None:
        code, _ = self._run_main(
            [self.path, "--api-key", "sk-test"],
            raise_exc=upload_pdf.RateLimitError("slow down"),
        )
        self.assertEqual(code, upload_pdf.EXIT_RATE_LIMIT)

    def test_connection_error_mapped(self) -> None:
        code, _ = self._run_main(
            [self.path, "--api-key", "sk-test"],
            raise_exc=upload_pdf.APIConnectionError("no net"),
        )
        self.assertEqual(code, upload_pdf.EXIT_NETWORK_ERROR)

    def test_unexpected_error_mapped(self) -> None:
        code, _ = self._run_main(
            [self.path, "--api-key", "sk-test"],
            raise_exc=RuntimeError("boom"),
        )
        self.assertEqual(code, upload_pdf.EXIT_UNKNOWN)


if __name__ == "__main__":
    unittest.main(verbosity=2)
