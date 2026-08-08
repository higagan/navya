from pathlib import Path

import pytest

import config
from ocr_engines import EngineUnavailableError, ParinamikaEngine


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
