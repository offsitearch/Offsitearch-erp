"""File upload validation utilities."""

from pathlib import Path

from fastapi import HTTPException, UploadFile, status

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".txt",
    ".csv",
    ".rtf",
    ".odt",
    ".ods",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".svg",
    ".dwg",
    ".dxf",
    ".skp",  # CAD / SketchUp
}

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".heic",
    ".heif",
}

ALLOWED_RECEIPT_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
}


def _ext(filename: str | None) -> str:
    return Path(filename or "").suffix.lower()


def validate_upload(
    file: UploadFile,
    content: bytes,
    *,
    allowed: set[str],
    label: str = "file",
) -> str:
    """Validate upload size and extension. Returns the validated extension."""
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"{label} exceeds maximum size of {MAX_UPLOAD_SIZE // (1024 * 1024)} MB",
        )
    ext = _ext(file.filename)
    if ext not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File type '{ext or '(none)'}' not allowed for {label}. Accepted: {allowed_str}",
        )
    return ext
