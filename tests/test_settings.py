import pytest

from ai_gif_studio.configuration.settings import AppSettings


def test_telegram_allowed_user_ids_accepts_comma_separated_string(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "123456789, 987654321")
    settings = AppSettings()
    assert settings.telegram_allowed_user_ids == (123456789, 987654321)


def test_telegram_allowed_user_ids_accepts_single_numeric_string(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "123456789")
    settings = AppSettings()
    assert settings.telegram_allowed_user_ids == (123456789,)
