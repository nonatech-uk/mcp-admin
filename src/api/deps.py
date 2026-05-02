"""Connection pool init plus shared dependencies."""

from mees_shared.db import close_pool, get_conn, init_pool as _init_pool  # noqa: F401
import mees_shared.db as _db_mod

from config.settings import settings


def init_pool() -> None:
    _init_pool(settings.dsn, settings.db_pool_min, settings.db_pool_max)
