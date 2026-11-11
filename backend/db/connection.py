import os

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event


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
        from db import particiones, tablas                    # noqa: F401  (registra los modelos nuevos)
        if db.engine.dialect.name == "postgresql":
            _crear_esquema_postgres(tablas, particiones)
        else:
            if db.engine.dialect.name == "sqlite":
                # SQLite requiere activar las claves foráneas en cada conexión.
                @event.listens_for(db.engine, "connect")
                def sqlite_foreign_keys(connection, _record):
                    cursor = connection.cursor()
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.close()
            db.create_all()                                   # otros motores: tablas normales (sin particionado)
        from services.usuarios import asegurar_columna_role   # bases anteriores a los roles: agrega users.role
        asegurar_columna_role()


# Clave del bloqueo asesor que serializa la creación del esquema entre procesos (workers de gunicorn, jobs, etc.)
BLOQUEO_ESQUEMA = 727_270_001


def _crear_esquema_postgres(tablas, particiones):
    """Crea las tablas (las grandes, particionadas por mes) sin que varios procesos que arrancan a la vez choquen.

    Con 2 workers de gunicorn arrancando sobre una base vacía, ambos harían ``CREATE TABLE`` al mismo tiempo y uno
    fallaría. El bloqueo asesor de Postgres hace que el segundo espere y luego vea las tablas ya creadas.
    """
    from sqlalchemy import text
    with db.engine.connect() as candado:
        candado.execute(text("SELECT pg_advisory_lock(:k)"), {"k": BLOQUEO_ESQUEMA})
        try:
            todas = db.metadata.sorted_tables
            # tablas normales primero (users, ...); las particionadas se crean con DDL propio (PARTITION BY RANGE mensual)
            db.metadata.create_all(db.engine, tables=[t for t in todas if t.name not in tablas.PARTICIONADAS])
            particiones.crear_tablas_particionadas(
                db.engine, [t for t in todas if t.name in tablas.PARTICIONADAS], tablas.PARTICIONADAS)
        finally:
            candado.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": BLOQUEO_ESQUEMA})
            candado.commit()
