# ADR-0004: Object storage image after MinIO stopped publishing images

* Status: Accepted · 2026-10-13

## Context

The plan fixes MinIO as the local S3-compatible store. The upstream `minio/minio` and
`minio/mc` repositories are no longer available on Docker Hub (pulls fail with
"repository does not exist").

## Decision

Use the community build `pgsty/minio` (a maintained fork that builds unmodified MinIO from
source) pinned to `RELEASE.2026-08-04T00-00-00Z`, and `pgsty/mc:RELEASE.2026-09-16T00-00-00Z`
for bucket creation. MinIO (AGPL-3.0) runs as a separate, unmodified service and is reached only
over the S3 API; no MinIO code is linked into RenovaCheck.

## Consequences

* The application only depends on the S3 API, so swapping to another S3-compatible store
  (or a managed bucket in production) is a configuration change.
* Image provenance is a fork: pin tags, and re-evaluate before any production use.
