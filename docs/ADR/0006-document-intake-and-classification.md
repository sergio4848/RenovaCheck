# ADR-0006: Document intake, storage and type classification

* Status: Accepted · 2026-10-13

## Context

Users upload the documents of a case (PDF scans and generated PDFs, sometimes photos). The
type of each document decides which fields and rules apply later. Uploads are untrusted input.

## Decision

* **Intake (web):** at most 20 files × 20 MB per request; the validator checks the content type
  with finfo, and `FileSniffer` checks magic bytes again (PDF, PNG, JPEG only). The stored
  extension comes from the content, never from the client's file name. SHA-256 per case
  de-duplicates (unique index `(case_file_id, sha256)`). Optional ClamAV (`--profile av`,
  `CLAMAV_ENABLED=true`) fails closed when enabled; when off the document is marked `skipped`.
* **Storage:** private bucket, key `org/<org>/cases/<case>/documents/<doc>/original.<ext>`;
  derived page images under `…/pages/NNN.png`. Browsers only get 5-minute presigned URLs (signed
  for the public MinIO host); the extraction service gets a 10-minute URL for the original.
* **Analysis (extract):** `POST /v1/documents/analyze` with a bearer token compared in constant
  time. The service only downloads from the object-store host (no redirects, size cap), renders
  pages at 150 dpi with pdfium, reads the PDF text layer and falls back to OCR for pages without
  one (`RENOVA_OCR_PROVIDER=tesseract` in compose; cloud adapters in phase 4). Page count is
  capped (50) and image decoding refuses decompression bombs.
* **Classification:** keyword rules in `packages/rules/doc_types.yaml` on folded text (lower case,
  no diacritics). A type wins only above a minimum score and margin; otherwise the document stays
  "unrecognised" until a person sets the type. A manual type (`doc_type_source = user`) is never
  overwritten by reprocessing; every change is an audit event. A learned model was not needed for
  the synthetic set (100% accuracy) and is deferred.
* **Job:** `ProcessDocument` runs inside `TenantContext::runForOrganization()` (cleared before and
  after), validates the whole response (`AnalysisResult`) before storing anything, retries 5xx and
  connection errors, and marks 4xx as failed with an error code. Its timeout (240 s) sits between
  the HTTP timeout to the extraction service (180 s) and the queue's `retry_after` (300 s), and a
  per-document lock (`WithoutOverlapping`) drops duplicate deliveries while one is running.
* **Limits and credentials:** the extraction service caps rendered page pixels, decoded image
  pixels, characters per page and OCR time per document, and analyses at most two documents at
  a time (503 when busy); its container has memory and CPU limits. Each service has its own
  object-store account: the web app may read, write and delete under `org/*`; the extraction
  service may only write page images (`org/*/cases/*/documents/*/pages/*`). Downloads use a name
  rebuilt from an ASCII stem and the sniffed extension, never the raw client name.

## Consequences

* The web app stays the only database writer; the extraction service writes only page images
  under a prefix the web app chose and that must contain the document id.
* Classification quality depends on the text: scans need OCR; with `text_layer` only, scans stay
  unrecognised rather than mis-typed.
