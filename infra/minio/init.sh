#!/bin/sh
# Creates the private document bucket and one least-privilege account per service. Idempotent:
# re-running updates the secrets and policies. The root account is used only here.
set -eu

: "${MINIO_ROOT_USER:?}" "${MINIO_ROOT_PASSWORD:?}" "${S3_BUCKET:?}"
: "${S3_WEB_ACCESS_KEY:?}" "${S3_WEB_SECRET_KEY:?}" "${S3_EXTRACT_ACCESS_KEY:?}" "${S3_EXTRACT_SECRET_KEY:?}"

policies=$(mktemp -d)
trap 'rm -rf "$policies"' EXIT

mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null
mc mb --ignore-existing "local/$S3_BUCKET"
mc anonymous set none "local/$S3_BUCKET"

# Web application: stores originals, signs browser and extraction URLs, removes its own uploads.
cat >"$policies/web.json" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
     "Resource": ["arn:aws:s3:::$S3_BUCKET/org/*"]},
    {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": ["arn:aws:s3:::$S3_BUCKET"],
     "Condition": {"StringLike": {"s3:prefix": ["org/*"]}}}
  ]
}
JSON

# Extraction service: reads originals only through URLs signed by the web app; writes page images.
cat >"$policies/extract.json" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["s3:PutObject"],
     "Resource": ["arn:aws:s3:::$S3_BUCKET/org/*/cases/*/documents/*/pages/*"]}
  ]
}
JSON

ensure_account() { # name access_key secret_key
  mc admin policy create local "renova-$1" "$policies/$1.json" >/dev/null
  mc admin user add local "$2" "$3" >/dev/null
  # The mc image has no grep; attaching an already attached policy is an error.
  case "$(mc admin user info local "$2")" in
    *"renova-$1"*) ;;
    *) mc admin policy attach local "renova-$1" --user "$2" >/dev/null ;;
  esac
  echo "account $2: policy renova-$1"
}

ensure_account web "$S3_WEB_ACCESS_KEY" "$S3_WEB_SECRET_KEY"
ensure_account extract "$S3_EXTRACT_ACCESS_KEY" "$S3_EXTRACT_SECRET_KEY"
