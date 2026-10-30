import os
import sys
from pathlib import Path

# los tests no tocan la base real ni TomTom: SQLite en memoria y sin clave
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["API_TOMTOM"] = ""
os.environ["TOMMTOM_KEY"] = ""

RAIZ = Path(__file__).resolve().parents[1]
for p in (RAIZ, RAIZ / "model"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
