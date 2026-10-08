from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True), override=False)
except Exception:
    pass

_CODE_DIR = Path(__file__).resolve().parents[1]
_WEEK10_DIR = _CODE_DIR.parent

DATA_DIR = Path(os.getenv("DATA_DIR", str(_WEEK10_DIR / "data_processed")))
CLEAN_DIR = DATA_DIR / "clean"
EXPORT_DIR = Path(os.getenv("EXPORT_DIR", str(_WEEK10_DIR / "export")))
MODELO_OUTPUTS_DIR = Path(
    os.getenv("MODELO_OUTPUTS_DIR", str(_CODE_DIR / "model" / "outputs"))
)

TOMTOM_API_KEY = os.getenv("API_TOMTOM")
TOMTOM_TIMEOUT = float(os.getenv("TOMTOM_TIMEOUT", "4.0"))
TOMTOM_SEGMENT = os.getenv("TOMTOM_SEGMENT", "10")  # metros del segmento relativo

# Si alguno no coincide, la ingesta falla en lugar de cargar datos corruptos.
FILAS_ESPERADAS = {
    "troncal_hora": 398_928,
    "metro_l1_hora": 341_640,
    "metro_l1_total_hora": 170_820,
    "corredores_hora": 8_253_635,
    "alimentador_hora": 4_670_304,
    "alimentador_tarifa": 804_864,
    "cobertura_unidad": 125,
}

FIABLE_ESPERADO = {
    "corredor": 7_111_955,
    "alimentador": 4_667_184,
    "troncal": 394_200,
    "metro_l1": 170_820,
}
FIABLE_TOTAL_ESPERADO = 12_344_159
