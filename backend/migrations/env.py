from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.agents import models as agent_models  # noqa: F401
from app.core.config import settings
from app.db.base import Base
from app.mcp import models as mcp_models  # noqa: F401
from app.modules.briefs import models as brief_models  # noqa: F401
from app.modules.captions import models as caption_models  # noqa: F401
from app.modules.discovery import models as discovery_models  # noqa: F401
from app.modules.episodes import models as episode_models  # noqa: F401
from app.modules.integrations import models as integration_models  # noqa: F401
from app.modules.narratives import models as narrative_models  # noqa: F401
from app.modules.outlines import models as outline_models  # noqa: F401
from app.modules.profiles import models as profile_models  # noqa: F401
from app.modules.recordings import models as recording_models  # noqa: F401
from app.modules.research import models as research_models  # noqa: F401
from app.modules.research_sources import models as research_source_models  # noqa: F401
from app.modules.schedules import models as schedule_models  # noqa: F401
from app.modules.series import models  # noqa: F401
from app.modules.settings import models as settings_models  # noqa: F401
from app.modules.strategy import models as strategy_models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", str(settings.database_url).replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
