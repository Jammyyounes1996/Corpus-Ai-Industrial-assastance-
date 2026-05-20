from frontend.utils.file_helpers import format_size, get_type_icon, get_file_type


def test_format_size_bytes():
    assert format_size(500) == "500.0 B"


def test_format_size_kb():
    assert format_size(1024) == "1.0 KB"


def test_format_size_mb():
    assert format_size(1024 * 1024) == "1.0 MB"


def test_format_size_gb():
    assert format_size(1024 * 1024 * 1024) == "1.0 GB"


def test_get_type_icon():
    assert get_type_icon("pdf") == "📄"
    assert get_type_icon("audio") == "🎵"
    assert get_type_icon("image") == "🖼️"
    assert get_type_icon("unknown") == "📁"
    assert get_type_icon("other") == "📁"


def test_get_file_type():
    assert get_file_type("report.pdf") == "pdf"
    assert get_file_type("song.mp3") == "audio"
    assert get_file_type("recording.wav") == "audio"
    assert get_file_type("photo.jpg") == "image"
    assert get_file_type("photo.jpeg") == "image"
    assert get_file_type("photo.png") == "image"
    assert get_file_type("unknown.xyz") == "unknown"
