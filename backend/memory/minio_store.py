# AI Memory OS - MinIO File Storage
from __future__ import annotations
from minio import Minio
from minio.error import S3Error

from backend.services.config import settings

BUCKET = "memory-files"

class MinIOStore:
    def __init__(self, endpoint=None, access_key=None, secret_key=None):
        endpoint = endpoint or settings.minio_endpoint
        access_key = access_key or settings.minio_access_key
        secret_key = secret_key or settings.minio_secret_key
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(BUCKET):
                self.client.make_bucket(BUCKET)
        except S3Error: pass

    def upload(self, object_name: str, data: bytes, content_type: str = "application/octet-stream"):
        import io
        self.client.put_object(BUCKET, object_name, io.BytesIO(data), len(data), content_type=content_type)
        return object_name

    def get_url(self, object_name: str) -> str:
        return self.client.presigned_get_object(BUCKET, object_name)
