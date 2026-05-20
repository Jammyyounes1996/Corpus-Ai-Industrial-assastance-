from __future__ import annotations


def format_size(size_bytes: int | float) -> str:
    """Format bytes to human-readable size string."""
    size_bytes = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


FILE_TYPE_ICONS: dict[str, str] = {
    "pdf": "📄",
    "audio": "🎵",
    "image": "🖼️",
    "unknown": "📁",
}

FILE_TYPE_EXTENSIONS: dict[str, set[str]] = {
    "pdf": {".pdf"},
    "audio": {".mp3", ".wav", ".m4a", ".ogg"},
    "image": {".jpg", ".jpeg", ".png", ".webp"},
}


def get_type_icon(file_type: str) -> str:
    """Return emoji icon for a file type."""
    return FILE_TYPE_ICONS.get(file_type, FILE_TYPE_ICONS["unknown"])


def get_file_type(filename: str) -> str:
    """Infer file type from filename extension."""
    name = filename.lower()
    for ftype, exts in FILE_TYPE_EXTENSIONS.items():
        if any(name.endswith(ext) for ext in exts):
            return ftype
    return "unknown"
