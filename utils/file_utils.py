import hashlib
import re
from pathlib import Path


def sha256_file(file_path: str | Path) -> str:
    """Compute a file's SHA-256 hash by streaming it in chunks."""
    hasher = hashlib.sha256()
    with Path(file_path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def sanitize_filename(name: str) -> str:
    """Replace characters that are invalid in Windows filenames."""
    return re.sub(r'[<>:"/\\|?*]', "_", name)
