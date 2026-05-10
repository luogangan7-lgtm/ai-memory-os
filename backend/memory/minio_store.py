# AI Memory OS - MinIO File Storage
from __future__ import annotations
from minio import Minio
from minio.error import S3Error

BUCKET = "memory-files"

class MinIOStore:
    def __init__(self, endpoint="localhost:9000", access_key="admin", secret_key="password"):
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
