import subprocess
from typing import Literal

import pytest
from alembic.config import Config
from alembic.script import Script, ScriptDirectory

ALEMBIC_CONFIG = Config("alembic.ini")
ALEMBIC_TIMEOUT = 10


def get_revisions() -> list[Script]:
    revisions_dir = ScriptDirectory.from_config(ALEMBIC_CONFIG)
    revisions = list(revisions_dir.walk_revisions("base", "heads"))
    revisions.reverse()
    return revisions


def run_alembic(command: Literal["upgrade", "downgrade"], revision: str) -> None:
    subprocess.run(["alembic", command, revision], check=True, timeout=ALEMBIC_TIMEOUT)


@pytest.mark.asyncio
@pytest.mark.parametrize("revision", get_revisions())
async def test_migrations_stairway(create_database: None, revision: Script) -> None:
    run_alembic("upgrade", revision.revision)
    run_alembic("downgrade", revision.down_revision or "-1")
    run_alembic("upgrade", revision.revision)
