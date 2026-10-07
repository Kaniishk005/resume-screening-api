from pathlib import Path

from alembic import command
from alembic.config import Config


def upgrade_database() -> None:
    project_root = Path(__file__).resolve().parents[2]
    config = Config(str(project_root / "alembic.ini"))
    command.upgrade(config, "head")
