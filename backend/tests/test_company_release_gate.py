"""Company deployment safety tests: no public customer data on accidental disposable paths."""
import pytest
from app.main import validate_deployment_settings


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('MASR_DURABLE_STORAGE_CONFIRMED', 'yes')
    monkeypatch.setenv('BACKUP_RECOVERY_VERIFIED', 'yes')
    monkeypatch.setenv('MASR_USER_DB', '/data/travelers.sqlite3')
    monkeypatch.setenv('DATABASE_PATH', '/data/catalog.sqlite3')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only-not-a-real-key')
    monkeypatch.delenv('TRUST_PROXY_HEADERS', raising=False)
    return monkeypatch


def test_production_gate_accepts_explicit_configuration_without_claiming_its_verification(production):
    validate_deployment_settings()


def test_production_gate_requires_verified_backup_restore(production):
    production.delenv('BACKUP_RECOVERY_VERIFIED')
    with pytest.raises(RuntimeError, match='backup and recovery'):
        validate_deployment_settings()


@pytest.mark.parametrize('key', ['MASR_USER_DB', 'DATABASE_PATH'])
def test_production_rejects_implicit_and_relative_database_paths(production, key):
    production.delenv(key)
    with pytest.raises(RuntimeError, match=key):
        validate_deployment_settings()
    production.setenv(key, 'relative/travelers.sqlite3')
    with pytest.raises(RuntimeError, match=key):
        validate_deployment_settings()


def test_production_rejects_database_files_inside_backend_source(production):
    from app import main
    production.setenv('MASR_USER_DB', str(main.Path(main.__file__).resolve().parents[1] / 'data' / 'account.sqlite3'))
    with pytest.raises(RuntimeError, match='source tree'):
        validate_deployment_settings()


def test_production_rejects_same_database_file(production):
    production.setenv('MASR_USER_DB', '/data/same.sqlite3')
    production.setenv('DATABASE_PATH', '/data/same.sqlite3')
    with pytest.raises(RuntimeError, match='separate'):
        validate_deployment_settings()


def test_production_requires_ai_provider(production):
    production.delenv('GEMINI_API_KEY')
    production.delenv('OPENAI_API_KEY', raising=False)
    with pytest.raises(RuntimeError, match='provider key'):
        validate_deployment_settings()


def test_production_trusted_proxy_must_have_ip_allowlist(production):
    production.setenv('TRUST_PROXY_HEADERS', 'true')
    production.delenv('TRUSTED_PROXY_IPS', raising=False)
    with pytest.raises(RuntimeError, match='TRUSTED_PROXY_IPS'):
        validate_deployment_settings()


def test_portfolio_preview_does_not_require_production_secrets(production):
    production.setenv('APP_ENV', 'portfolio')
    production.delenv('GEMINI_API_KEY')
    production.delenv('BACKUP_RECOVERY_VERIFIED')
    validate_deployment_settings()
