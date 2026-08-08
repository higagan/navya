from pathlib import Path

import pytest

import config
from ocr_engines import EngineUnavailableError, OllamaVisionEngine, ParinamikaEngine


def test_parinamika_unavailable_when_unconfigured(monkeypatch):
    monkeypatch.setattr(config, "PARINAMIKA_MODE", None)
    engine = ParinamikaEngine()

    with pytest.raises(EngineUnavailableError):
        engine.recognize(Path("does-not-matter.png"), page_num=1)


def test_parinamika_cli_mode_requires_command(monkeypatch):
    monkeypatch.setattr(config, "PARINAMIKA_MODE", "cli")
    monkeypatch.setattr(config, "PARINAMIKA_CLI_CMD", None)
    engine = ParinamikaEngine()

    with pytest.raises(EngineUnavailableError):
        engine.recognize(Path("does-not-matter.png"), page_num=1)


def test_parinamika_http_mode_requires_url(monkeypatch):
    monkeypatch.setattr(config, "PARINAMIKA_MODE", "http")
    monkeypatch.setattr(config, "PARINAMIKA_HTTP_URL", None)
    engine = ParinamikaEngine()

    with pytest.raises(EngineUnavailableError):
        engine.recognize(Path("does-not-matter.png"), page_num=1)


def test_parinamika_file_mode_requires_input_dir(monkeypatch):
    monkeypatch.setattr(config, "PARINAMIKA_MODE", "file")
    monkeypatch.setattr(config, "PARINAMIKA_INPUT_DIR", None)
    engine = ParinamikaEngine()

    with pytest.raises(EngineUnavailableError):
        engine.recognize(Path("does-not-matter.png"), page_num=1)


def test_parinamika_file_mode_falls_back_when_export_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "PARINAMIKA_MODE", "file")
    monkeypatch.setattr(config, "PARINAMIKA_INPUT_DIR", str(tmp_path))
    engine = ParinamikaEngine()

    with pytest.raises(EngineUnavailableError):
        engine.recognize(Path("does-not-matter.png"), page_num=1)


def test_parinamika_file_mode_reads_txt_export(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "PARINAMIKA_MODE", "file")
    monkeypatch.setattr(config, "PARINAMIKA_INPUT_DIR", str(tmp_path))
    (tmp_path / "page-017.txt").write_text("देवदत्तो गच्छति", encoding="utf-8")
    engine = ParinamikaEngine()

    result = engine.recognize(Path("does-not-matter.png"), page_num=17)

    assert result.engine == "parinamika"
    assert result.text == "देवदत्तो गच्छति"


def test_parinamika_file_mode_reads_json_export(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "PARINAMIKA_MODE", "file")
    monkeypatch.setattr(config, "PARINAMIKA_INPUT_DIR", str(tmp_path))
    (tmp_path / "page-017.json").write_text(
        '{"text": "देवदत्तो गच्छति", "blocks": [{"text": "देवदत्तो गच्छति", "bbox": [0, 0, 10, 10]}]}',
        encoding="utf-8",
    )
    engine = ParinamikaEngine()

    result = engine.recognize(Path("does-not-matter.png"), page_num=17)

    assert result.text == "देवदत्तो गच्छति"
    assert len(result.blocks) == 1


def test_ollama_vision_unavailable_without_model():
    engine = OllamaVisionEngine(model=None)

    with pytest.raises(EngineUnavailableError):
        engine.recognize(Path("does-not-matter.png"), page_num=1)


def test_ollama_vision_engine_name_includes_model():
    engine = OllamaVisionEngine(model="qwen3-vl:8b")

    assert engine.name == "ollama:qwen3-vl:8b"
