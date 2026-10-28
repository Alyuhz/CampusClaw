from campusclaw.db import init_db


def test_database_initialization_is_idempotent(app):
    init_db(app)
    init_db(app)
