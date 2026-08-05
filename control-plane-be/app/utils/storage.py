"""S3-compatible file storage via boto3 (MinIO in dev, S3 in prod)."""
import uuid
from io import BytesIO
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

from app.config import settings

_s3 = boto3.client(
    "s3",
    endpoint_url=settings.AWS_ENDPOINT_URL,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION,
)


def _ensure_bucket() -> None:
    try:
        _s3.head_bucket(Bucket=settings.AWS_BUCKET_NAME)
    except ClientError:
        _s3.create_bucket(Bucket=settings.AWS_BUCKET_NAME)


async def upload_file(data: bytes, filename: str, content_type: str) -> tuple[str, int]:
    """Upload bytes to object storage. Returns (file_url, size_bytes)."""
    key = f"control-plans/{uuid.uuid4()}/{filename}"
    _ensure_bucket()
    _s3.put_object(
        Bucket=settings.AWS_BUCKET_NAME,
        Key=key,
        Body=BytesIO(data),
        ContentType=content_type,
    )
    file_url = f"{settings.AWS_ENDPOINT_URL}/{settings.AWS_BUCKET_NAME}/{key}"
    return file_url, len(data)


async def download_file(file_url: str) -> bytes:
    """Download a file from object storage by its URL. Returns raw bytes."""
    # URL format: {endpoint}/{bucket}/{key}
    prefix = f"{settings.AWS_ENDPOINT_URL}/{settings.AWS_BUCKET_NAME}/"
    if file_url.startswith(prefix):
        key = file_url[len(prefix):]
    else:
        parsed = urlparse(file_url)
        path = parsed.path.lstrip("/")
        bucket_prefix = f"{settings.AWS_BUCKET_NAME}/"
        key = path[len(bucket_prefix):] if path.startswith(bucket_prefix) else path

    buf = BytesIO()
    _s3.download_fileobj(settings.AWS_BUCKET_NAME, key, buf)
    return buf.getvalue()


def _url_to_key(file_url: str) -> str:
    """Extract the S3 object key from a stored file URL."""
    prefix = f"{settings.AWS_ENDPOINT_URL}/{settings.AWS_BUCKET_NAME}/"
    if file_url.startswith(prefix):
        return file_url[len(prefix):]
    parsed = urlparse(file_url)
    path = parsed.path.lstrip("/")
    bucket_prefix = f"{settings.AWS_BUCKET_NAME}/"
    return path[len(bucket_prefix):] if path.startswith(bucket_prefix) else path


def _rewrite_public(url: str) -> str:
    """
    Replace the internal MinIO endpoint with the public-facing URL so browsers
    can resolve it.  e.g. http://minio:9000/… → http://localhost:9000/…

    Only applied when AWS_PUBLIC_ENDPOINT_URL is set and differs from
    AWS_ENDPOINT_URL.
    """
    public = settings.AWS_PUBLIC_ENDPOINT_URL.rstrip("/")
    internal = settings.AWS_ENDPOINT_URL.rstrip("/")
    if public and public != internal and url.startswith(internal):
        return public + url[len(internal):]
    return url


def generate_presigned_url(key: str, expiry: int = 3600) -> str:
    url = _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_BUCKET_NAME, "Key": key},
        ExpiresIn=expiry,
    )
    return _rewrite_public(url)


def get_presigned_download_url(file_url: str, expiry: int = 3600) -> str:
    """Generate a presigned download URL from a stored file URL."""
    return generate_presigned_url(_url_to_key(file_url), expiry)
