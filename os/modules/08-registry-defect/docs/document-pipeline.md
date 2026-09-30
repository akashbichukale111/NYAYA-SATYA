# Document Pipeline

Code: `backend/app/services/parsing.py`,
`backend/app/routers/documents.py`.

## Upload flow

1. Client sends `multipart/form-data` to
   `POST /api/filing-packages/{id}/documents`.
2. Filename extension is checked against `DANGEROUS_EXTENSIONS`
   (`.exe`, `.sh`, `.js`, ...) and rejected outright regardless of
   declared content type.
3. `parsing.parse_file()` runs format detection (extension **and**
   content-signature, e.g. `%PDF` / `PK`), size-limit enforcement
   (25 MB), and format-specific extraction.
4. A `DocumentVersion` row is written with `extraction_status` (`OK` /
   `FAILED`), `extraction_error` (a specific code, e.g.
   `EMPTY_DOCUMENT`, `CORRUPTED_DOCUMENT: ...`, `UNREADABLE_DOCUMENT`),
   `sha256`, and `source_location_known`.
5. The file is written to disk at a path built entirely from generated
   ids (`STORAGE_ROOT/case_id/package_id/<version_id>.<ext>`) — the
   client-supplied filename is never used for the actual path, which is
   the path-traversal defense (verified: the constructed path is checked
   with `os.path.abspath(...).startswith(...)` before writing).
6. If extraction succeeded, `attachment_engine.detect_and_store_references`
   runs immediately so references are available before the next precheck.

## Parser failures are data

Every parser (`_parse_pdf`, `_parse_docx`, `_parse_txt`, `_parse_json`,
`_parse_csv`) is wrapped so that a corrupt/unreadable file produces a
`ParseResult` with `extraction_status=FAILED` and a specific error, never
an unhandled exception. `parse_file()` additionally wraps the whole
dispatch in a `try/except` as a last-resort safety net.

## Never fabricating a location

- PDF: `location_known=True` for every page (PyPDF2 gives a real page
  index).
- DOCX: `page_count=None` always — there is no reliable page concept
  without a rendering engine, so the field is left `None` rather than
  guessed.
- TXT/CSV: sections are per-line/per-row, `location_known=True`.
- JSON: no natural sub-document location; `source_location_known=False`.

## Security scanning

Extracted text is scanned for prompt-injection-style phrasing
(`services/security_scan.py`) during precheck. A hit produces a
`PROMPT_INJECTION_CONTENT` defect; it never changes any other part of the
system's behavior — see the "Prompt-injection defense" section of the
top-level README.
