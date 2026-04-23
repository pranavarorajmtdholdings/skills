#!/usr/bin/env python3
"""Upload a PDF file to the Anthropic Files API with robust error handling and logging."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Optional

try:
    import anthropic
    from anthropic import (
        APIConnectionError,
        APIStatusError,
        APITimeoutError,
        AuthenticationError,
        BadRequestError,
        InternalServerError,
        NotFoundError,
        PermissionDeniedError,
        RateLimitError,
    )
except ImportError as exc:  # pragma: no cover
    sys.stderr.write(
        "Error: the 'anthropic' package is not installed. "
        "Install it with `pip install anthropic`.\n"
    )
    raise SystemExit(1) from exc


logger = logging.getLogger("upload_pdf")


# Exit codes
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_FILE_ERROR = 3
EXIT_AUTH_ERROR = 4
EXIT_BAD_REQUEST = 5
EXIT_NOT_FOUND = 6
EXIT_RATE_LIMIT = 7
EXIT_SERVER_ERROR = 8
EXIT_NETWORK_ERROR = 9
EXIT_UNKNOWN = 1

# PDF upload size limit for Anthropic's Files API is 32 MB at the time of writing.
MAX_PDF_BYTES = 32 * 1024 * 1024


def configure_logging(verbosity: int, log_file: Optional[str]) -> None:
    """Configure root logging based on verbosity count and optional log file."""
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_file:
        try:
            handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
        except OSError as exc:
            sys.stderr.write(f"Warning: could not open log file {log_file!r}: {exc}\n")

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        handlers=handlers,
        force=True,
    )


def validate_pdf(file_path: str) -> None:
    """Validate that the given path points at a readable, non-empty PDF within size limits."""
    logger.debug("Validating file: %s", file_path)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if not os.path.isfile(file_path):
        raise IsADirectoryError(f"Not a regular file: {file_path}")

    if not os.access(file_path, os.R_OK):
        raise PermissionError(f"File is not readable: {file_path}")

    size = os.path.getsize(file_path)
    if size == 0:
        raise ValueError(f"File is empty: {file_path}")
    if size > MAX_PDF_BYTES:
        raise ValueError(
            f"File {file_path!r} is {size} bytes, exceeding the "
            f"{MAX_PDF_BYTES}-byte limit for PDF uploads."
        )

    # Sniff the magic bytes to confirm this is a PDF.
    with open(file_path, "rb") as f:
        header = f.read(5)
    if not header.startswith(b"%PDF-"):
        raise ValueError(
            f"File {file_path!r} does not appear to be a PDF "
            f"(missing %PDF- header, got {header!r})."
        )

    logger.info("File %s validated (%d bytes).", file_path, size)


def upload_pdf(file_path: str, api_key: Optional[str] = None) -> object:
    """Upload a PDF to the Anthropic Files API and return the file object."""
    validate_pdf(file_path)

    logger.debug("Instantiating Anthropic client.")
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    filename = os.path.basename(file_path)
    logger.info("Uploading %s to Anthropic Files API...", filename)

    with open(file_path, "rb") as f:
        file_obj = client.beta.files.upload(
            file=(filename, f, "application/pdf"),
        )

    logger.info("Upload succeeded. File ID: %s", getattr(file_obj, "id", "<unknown>"))
    return file_obj


def _print_result(file_obj: object) -> None:
    print(f"Uploaded file ID: {getattr(file_obj, 'id', '')}")
    print(f"Filename:         {getattr(file_obj, 'filename', '')}")
    print(f"Size (bytes):     {getattr(file_obj, 'size_bytes', '')}")
    print(f"MIME type:        {getattr(file_obj, 'mime_type', '')}")
    print(f"Created at:       {getattr(file_obj, 'created_at', '')}")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload a PDF to the Anthropic Files API with logging and error handling.",
    )
    parser.add_argument("path", help="Path to the PDF file to upload.")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v for INFO, -vv for DEBUG).",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Optional path to also write logs to a file.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Override the ANTHROPIC_API_KEY environment variable.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose, args.log_file)

    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error(
            "ANTHROPIC_API_KEY is not set. Export it or pass --api-key."
        )
        return EXIT_AUTH_ERROR

    try:
        file_obj = upload_pdf(args.path, api_key=api_key)
    except (FileNotFoundError, IsADirectoryError, PermissionError) as exc:
        logger.error("File error: %s", exc)
        return EXIT_FILE_ERROR
    except ValueError as exc:
        logger.error("Invalid input: %s", exc)
        return EXIT_BAD_REQUEST
    except AuthenticationError as exc:
        logger.error("Authentication failed: %s", exc)
        return EXIT_AUTH_ERROR
    except PermissionDeniedError as exc:
        logger.error("Permission denied by API: %s", exc)
        return EXIT_AUTH_ERROR
    except NotFoundError as exc:
        logger.error("Resource not found: %s", exc)
        return EXIT_NOT_FOUND
    except BadRequestError as exc:
        logger.error("Bad request rejected by API: %s", exc)
        return EXIT_BAD_REQUEST
    except RateLimitError as exc:
        logger.error("Rate limit exceeded: %s", exc)
        return EXIT_RATE_LIMIT
    except InternalServerError as exc:
        logger.error("Anthropic server error: %s", exc)
        return EXIT_SERVER_ERROR
    except APITimeoutError as exc:
        logger.error("Request timed out: %s", exc)
        return EXIT_NETWORK_ERROR
    except APIConnectionError as exc:
        logger.error("Network/connection error: %s", exc)
        return EXIT_NETWORK_ERROR
    except APIStatusError as exc:
        logger.error(
            "Unexpected API status %s: %s",
            getattr(exc, "status_code", "?"),
            exc,
        )
        return EXIT_SERVER_ERROR
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        return EXIT_UNKNOWN
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error during upload.")
        return EXIT_UNKNOWN

    _print_result(file_obj)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
