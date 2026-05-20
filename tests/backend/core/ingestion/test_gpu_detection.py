import pytest
from unittest.mock import patch

from backend.core.ingestion.audio_ingestor import AudioIngestor


def test_gpu_detection_cuda():
    ingestor = AudioIngestor()
    with patch.dict("sys.modules", {"torch": None}):
        pass

    with patch("backend.core.ingestion.audio_ingestor.AudioIngestor._get_device", return_value="cuda"):
        assert ingestor._get_device() == "cuda"


def test_gpu_detection_cpu():
    ingestor = AudioIngestor()
    with patch("backend.core.ingestion.audio_ingestor.AudioIngestor._get_device", return_value="cpu"):
        assert ingestor._get_device() == "cpu"


def test_compute_type_cuda():
    ingestor = AudioIngestor()
    assert ingestor._get_compute_type("cuda") == "float16"


def test_compute_type_cpu():
    ingestor = AudioIngestor()
    assert ingestor._get_compute_type("cpu") == "int8"
