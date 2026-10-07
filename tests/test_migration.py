from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def run_upgrade(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")


def test_migration_adds_missing_analysis_status(tmp_path, monkeypatch):
    database_path = tmp_path / "old.db"
    url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE analysis (id INTEGER PRIMARY KEY)"))

    run_upgrade(database_path)

    columns = {column["name"] for column in inspect(engine).get_columns("analysis")}
    assert columns == {"id", "status", "match_breakdown"}
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert revision == "20261008_01"


def test_migration_is_safe_when_status_already_exists(tmp_path, monkeypatch):
    database_path = tmp_path / "current.db"
    url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE analysis "
                "(id INTEGER PRIMARY KEY, status VARCHAR(11) NOT NULL DEFAULT 'NEW')"
            )
        )

    run_upgrade(database_path)

    columns = [column["name"] for column in inspect(engine).get_columns("analysis")]
    assert columns.count("status") == 1
    assert columns.count("match_breakdown") == 1


def test_match_breakdown_migration_is_safe_when_column_already_exists(tmp_path, monkeypatch):
    database_path = tmp_path / "phase3.db"
    url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE analysis ("
                "id INTEGER PRIMARY KEY, "
                "status VARCHAR(11) NOT NULL DEFAULT 'NEW', "
                "match_breakdown TEXT NULL)"
            )
        )

    run_upgrade(database_path)

    columns = [column["name"] for column in inspect(engine).get_columns("analysis")]
    assert columns.count("match_breakdown") == 1
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert revision == "20261008_01"
