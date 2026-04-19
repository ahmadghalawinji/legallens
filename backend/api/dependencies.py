from fastapi import HTTPException, UploadFile

from backend.config import settings


async def validate_upload(file: UploadFile) -> UploadFile:
    """Validate uploaded file size and extension.

    Args:
        file: The uploaded file.

    Returns:
        The validated file.

    Raises:
        HTTPException: If file type or size is invalid.
    """
    suffix = "." + file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if suffix not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {settings.allowed_extensions}",
        )
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.max_file_size_mb}MB",
        )
    await file.seek(0)
    return file
