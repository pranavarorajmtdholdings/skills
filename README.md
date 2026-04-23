# Skills
Skills in this repository are backed up from https://clawdhub.com - check them out there for an easier experience (or have your clawdbot do it!)
## upload_pdf
A small command-line utility that uploads a PDF to the [Anthropic Files API](https://docs.anthropic.com/) using the official `anthropic` Python SDK. It includes pre-flight validation, structured logging, granular error handling, and an offline unit-test suite.
### Project layout
- `upload_pdf.py` — the CLI entry point.
- `test_upload_pdf.py` — `unittest`-based tests that stub the SDK and run without network access.
### Requirements
- Python 3.9+ (tested on macOS).
- The `anthropic` Python SDK.
- An `ANTHROPIC_API_KEY` for real uploads (tests do **not** need one).
### Setup
Create and activate a virtual environment, then install the SDK:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install anthropic
```
Export your API key for the session (or pass `--api-key` on each invocation):
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```
### Usage
Upload a PDF:
```bash
python upload_pdf.py /path/to/document.pdf
```
Available flags:
- `-v`, `--verbose` — increase verbosity (`-v` for INFO, `-vv` for DEBUG).
- `--log-file PATH` — additionally write logs to the given file.
- `--api-key KEY` — override `ANTHROPIC_API_KEY`.
Example with verbose logging written to disk:
```bash
python upload_pdf.py ./document.pdf -vv --log-file upload.log
```
On success the script prints the returned file ID and metadata:
```
Uploaded file ID: file_abc123
Filename:         document.pdf
Size (bytes):     12345
MIME type:        application/pdf
Created at:       2026-04-23T00:00:00Z
```
### Validation rules
Before contacting the API, `upload_pdf.py` verifies that the target path:
1. Exists and is a regular file.
2. Is readable by the current user.
3. Is non-empty and no larger than 32 MB (Anthropic's PDF limit; configurable via `MAX_PDF_BYTES`).
4. Starts with the `%PDF-` magic header.
### Exit codes
The CLI maps failure modes to distinct exit codes so calling scripts can react programmatically:
- `0` — success
- `1` — unknown / unexpected error
- `3` — local file error (missing, not a file, not readable)
- `4` — authentication or permission problem (missing key, `AuthenticationError`, `PermissionDeniedError`)
- `5` — bad input or API `BadRequestError` (including invalid PDF)
- `6` — API `NotFoundError`
- `7` — API `RateLimitError`
- `8` — API server error (`InternalServerError`, other `APIStatusError`)
- `9` — network issue (`APIConnectionError`, `APITimeoutError`)
### Testing
The tests run fully offline — they stub the `anthropic` module when it isn't installed and monkey-patch `anthropic.Anthropic` during each test. No real API key is required.
Run the full suite:
```bash
python3 -m unittest test_upload_pdf.py -v
```
Or directly:
```bash
python3 test_upload_pdf.py
```
Expected output ends with `OK` and `Ran 17 tests`. Covered scenarios include:
- `validate_pdf`: valid PDF, missing file, directory path, empty file, bad magic bytes, unreadable file, oversized file.
- `upload_pdf`: successful upload returns the expected object and calls the SDK with `(filename, fileobj, "application/pdf")`; SDK exceptions propagate unchanged.
- `main` CLI: missing API key, successful upload, non-existent file, non-PDF file, and mapping of `AuthenticationError`, `RateLimitError`, `APIConnectionError`, and unexpected errors to their respective exit codes.
### Troubleshooting
- **`externally-managed-environment`** on `pip install` — you are using the system/Homebrew Python. Activate the `.venv` first, or use `pipx`.
- **`zsh: command not found: python`** — Homebrew Python only ships `python3`. Either activate the venv (which provides `python`) or invoke `python3` explicitly.
- **`ANTHROPIC_API_KEY is not set`** — export the key or pass `--api-key`.
