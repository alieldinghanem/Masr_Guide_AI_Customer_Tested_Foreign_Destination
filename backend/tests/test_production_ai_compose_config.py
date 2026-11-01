"""Regression: deployed AI configuration must match the backend feature flags.

This deliberately reads Compose as plain text so it runs with normal backend
requirements; deployment tooling should validate the YAML independently.
"""
from pathlib import Path

COMPOSE = Path(__file__).resolve().parents[2] / "docker-compose.prod.yml"


def _prod_compose():
    return COMPOSE.read_text(encoding="utf-8")


def test_production_can_select_a_provider_and_preserves_both_api_keys():
    text = _prod_compose()
    assert "AI_PROVIDER: ${AI_PROVIDER:-gemini}" in text
    assert "GEMINI_API_KEY: ${GEMINI_API_KEY:-}" in text
    assert "OPENAI_API_KEY: ${OPENAI_API_KEY:-}" in text
    assert "OPENAI_MODEL: ${OPENAI_MODEL:-gpt-4o-mini}" in text


def test_production_search_flag_is_passed_through_but_opt_in():
    text = _prod_compose()
    assert "GEMINI_MODEL: ${GEMINI_MODEL:-gemini-2.5-flash}" in text
    assert "GEMINI_SEARCH_GROUNDING: ${GEMINI_SEARCH_GROUNDING:-false}" in text


def test_production_retains_storage_and_backup_release_gates():
    text = _prod_compose()
    for setting in ("APP_ENV: production", "MASR_DURABLE_STORAGE_CONFIRMED:",
                    "BACKUP_RECOVERY_VERIFIED:", "MASR_USER_DB: /app/data/traveler.sqlite3",
                    "DATABASE_PATH: /app/data/tourism.db"):
        assert setting in text


def test_render_preview_cannot_silently_use_legacy_model_or_omit_search_toggle():
    text = (COMPOSE.parent / "render.yaml").read_text(encoding="utf-8")
    assert "value: gemini-2.5-flash" in text
    assert "key: GEMINI_SEARCH_GROUNDING" in text
    assert "key: AI_PROVIDER" in text
    assert "key: OPENAI_API_KEY" in text
    assert "gemini-flash-latest" not in text
    assert "value: portfolio" in text
