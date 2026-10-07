from app.core.config import normalize_database_url
from app.db.database import engine_options


def test_legacy_render_postgres_url_is_normalized():
    assert normalize_database_url("postgres://user:pass@host/db") == (
        "postgresql+psycopg://user:pass@host/db"
    )


def test_plain_postgresql_url_uses_configured_psycopg_driver():
    assert normalize_database_url("postgresql://user:pass@host/db") == (
        "postgresql+psycopg://user:pass@host/db"
    )


def test_sqlite_engine_options_include_thread_check():
    url, options = engine_options("sqlite:///./test.db")
    assert url == "sqlite:///./test.db"
    assert options == {"check_same_thread": False}


def test_postgres_engine_options_do_not_include_sqlite_arguments():
    url, options = engine_options("postgresql+psycopg://user:pass@host/db")
    assert url == "postgresql+psycopg://user:pass@host/db"
    assert options == {}
