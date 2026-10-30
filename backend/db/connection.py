import os

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def _database_uri():
    """DATABASE_URL (Postgres en producción); SQLite local si no está definida."""
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return "sqlite:///urbansafe.db"
    # Render/Heroku entregan "postgres://"; se fija psycopg2 (SQLAlchemy nuevo asume psycopg3 por defecto)
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg2://" + url[len(prefix):]
    return url


def init_db(app):

    app.config["SQLALCHEMY_DATABASE_URI"] = _database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

    db.init_app(app)

    with app.app_context():
        db.create_all()
