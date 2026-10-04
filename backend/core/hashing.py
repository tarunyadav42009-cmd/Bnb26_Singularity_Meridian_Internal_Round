import hashlib
from pathlib import Path


def sha256_file(file_path: str) -> str:
    """
    Calculate SHA-256 hash of a file.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    sha256 = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """
    Calculate SHA-256 hash of raw bytes.
    """

    return hashlib.sha256(data).hexdigest()