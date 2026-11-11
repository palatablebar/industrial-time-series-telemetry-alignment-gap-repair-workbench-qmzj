# Schema baseline

Runtime schema is created by SQLAlchemy `Base.metadata.create_all()` on backend startup
(see `src/config/database.py`), which keeps the 5-service demo stack one-command startable.
`versions/001_initial.sql` is the reviewable baseline DDL kept in sync with the models for
teams that prefer explicit migrations / Alembic bootstrapping.
