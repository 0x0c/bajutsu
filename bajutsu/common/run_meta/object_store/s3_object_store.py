"""The store over one S3-compatible bucket, via an injected boto3 client."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ._functions import _is_not_found
from ._shared import _PRESIGN_TTL, _PUT_TTL


class S3ObjectStore:
    """`ObjectStore` over one S3-compatible bucket (AWS / R2 / MinIO) via an injected boto3 client."""

    def __init__(self, client: Any, bucket: str, *, presign_ttl: int = _PRESIGN_TTL) -> None:
        self._client = client
        self._bucket = bucket
        self._ttl = presign_ttl

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as e:
            if _is_not_found(e):
                return False
            raise  # a real error (auth, throttling, …) — don't mask it as "absent"
        return True

    def get_bytes(self, key: str) -> bytes | None:
        from botocore.exceptions import ClientError

        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as e:
            if _is_not_found(e):
                return None
            raise
        stream = resp["Body"]
        try:
            body: bytes = stream.read()
        finally:
            stream.close()  # release the HTTP connection/fd rather than leaking it under load
        return body

    def put_bytes(self, key: str, data: bytes, *, content_type: str = "") -> None:
        extra = {"ContentType": content_type} if content_type else {}
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, **extra)

    def put_file(self, key: str, path: Path, *, content_type: str = "") -> None:
        # upload_file streams from disk (multipart for large files) — no full read into memory.
        extra = {"ExtraArgs": {"ContentType": content_type}} if content_type else {}
        self._client.upload_file(str(path), self._bucket, key, **extra)

    def presigned_url(self, key: str) -> str:
        url: str = self._client.generate_presigned_url(
            "get_object", Params={"Bucket": self._bucket, "Key": key}, ExpiresIn=self._ttl
        )
        return url

    def presigned_put_url(self, key: str, *, content_type: str = "", ttl: int = _PUT_TTL) -> str:
        params: dict[str, str] = {"Bucket": self._bucket, "Key": key}
        if content_type:
            params["ContentType"] = content_type
        url: str = self._client.generate_presigned_url("put_object", Params=params, ExpiresIn=ttl)
        return url

    def list_keys(self, prefix: str) -> list[str]:
        keys: list[str] = []
        token: str | None = None
        while True:
            kw: dict[str, Any] = {"Bucket": self._bucket, "Prefix": prefix}
            if token:
                kw["ContinuationToken"] = token
            resp = self._client.list_objects_v2(**kw)
            keys.extend(str(o["Key"]) for o in resp.get("Contents", []))
            if not resp.get("IsTruncated"):
                return keys
            token = resp.get("NextContinuationToken")

    def delete_key(self, key: str) -> None:
        # S3 delete_object is idempotent — deleting an absent key returns success, so no existence
        # probe is needed to satisfy the seam's "no-op if absent" contract.
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def delete_keys(self, keys: Iterable[str]) -> None:
        # One batch delete per 1000 keys (the S3 DeleteObjects limit); an empty batch is skipped so a
        # run with no keys makes no call. Each key is idempotent, like `delete_key`.
        batch: list[dict[str, str]] = []
        for key in keys:
            batch.append({"Key": key})
            if len(batch) == 1000:
                self._client.delete_objects(Bucket=self._bucket, Delete={"Objects": batch})
                batch = []
        if batch:
            self._client.delete_objects(Bucket=self._bucket, Delete={"Objects": batch})
