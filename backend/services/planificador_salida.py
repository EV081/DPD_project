"""¿A qué hora salgo para llegar a tiempo? Viaje directo A → B con hora límite de llegada.

Para cada salida posible (cada 10 minutos) se calcula espera, tiempo a bordo, hora de llegada y
aforo al subir, y se recomienda la de menor costo generalizado entre las que llegan con margen:

    2 · espera + multiplicador(hacinamiento) · tiempo a bordo + 0,6 · minutos de anticipación

Los dos primeros términos son el costo del proyecto (``model/recomendacion.py``, Ortúzar y
Willumsen ec. 10.18). El tercero es el costo de llegar antes de lo necesario: Small (1982) estima
que un minuto de anticipación pesa cerca de 0,6 de un minuto de viaje. Llegar tarde no se admite.

Supuestos, todos declarados en la respuesta:

- **Aforo dentro de la hora.** El modelo pronostica por hora. El valor de cada hora se ancla en su
  minuto 30 y se interpola en línea recta entre horas vecinas. Las validaciones ATU son horarias,
  así que este suavizado no se puede validar con datos.
- **Espera.** Es la esperada, sin posición real de los vehículos. "Con margen" exige que aún se
  llegue a tiempo perdiendo un vehículo (un intervalo más).
- **Servicios del Metropolitano.** El aforo es el de la estación, igual para todos los servicios.
  Cada servicio se distingue por su horario, su frecuencia publicada y las paradas que omite:
  cada parada omitida ahorra ``AHORRO_PARADA_MIN``, con tope en la velocidad entre paradas.
"""
from __future__ import annotations

import datetime as dt
import math

from model import recomendacion as R
from services import horarios as H
from services import model_service as MS
from services import recomendacion_viaje as RV
from services.eje2_service import franja_de
from services.mapeo_estaciones import serie_de_estacion
from services.transbordos import PENALIZACION_TRANSBORDO_MIN

PASO_MIN = 10                 # separación entre salidas evaluadas
HORIZONTE_MIN = 240           # se evalúan salidas hasta 4 h antes de la hora límite
VENTANA_MIN = 60              # se muestran las que llegan hasta 60 min antes
PESO_ANTICIPACION = 0.6       # Small (1982): llegar antes pesa ~0,6 del tiempo de viaje
AHORRO_PARADA_MIN = 1.5       # detención + frenado/aceleración omitidos; tope en VEL_CRUCERO_KMH
VEL_CRUCERO_KMH = 35.0        # velocidad entre paradas que reproduce los 25,5 km/h comerciales
# El modelo troncal ordena en una sola línea los dos ramales del centro; cada servicio usa uno
RAMALES_CENTRO = (frozenset({"España", "Quilca", "2 de Mayo"}), frozenset({"Colmena", "Jiron de la Unión", "Tacna"}))
ETIQUETA_CLASE = {"Asientos": "con asientos", "De_pie": "de pie", "Saturado": "saturado"}


def interpolar(valores: list, minuto: float):
    """Valor en ``minuto`` del día (0-1439) a partir de 24 valores horarios anclados en el minuto 30.

    Sin dato en la hora devuelve None; si falta la hora vecina (p. ej. sin servicio) no interpola.
    """
    propio = valores[min(23, int(minuto // 60))]
    if propio is None:
        return None
    x = (minuto - 30.0) / 60.0
    i = math.floor(x)
    a, b = valores[max(0, min(23, i))], valores[max(0, min(23, i + 1))]
    if a is None or b is None:
        return propio
    return a + (b - a) * (x - i)


def clase_de(ocupacion: float, veh) -> str:
    """Clase de aforo con los umbrales del vehículo (asientos y umbral de saturación)."""
    carga = ocupacion * veh.capacidad
    return "Saturado" if carga > veh.umbral_saturado else ("De_pie" if carga > veh.asientos else "Asientos")


def _hhmm(minuto: float) -> str:
    m = int(round(minuto))
    return f"{(m // 60) % 24:02d}:{m % 60:02d}"


def _minuto(texto: str) -> int:
    try:
        h, m = str(texto).strip().split(":")[:2]
        h, m = int(h), int(m)
    except ValueError:
        raise MS.PrediccionError("llegada debe tener el formato HH:MM") from None
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise MS.PrediccionError("llegada debe ser una hora entre 00:00 y 23:59")
    return h * 60 + m


# --------------------------------------------------------------------------- servicios troncales
def _viaje_servicio(linea, a: str, b: str, paradas: list[str]) -> tuple[float, int]:
    """(minutos a bordo, paradas intermedias) de un servicio entre dos estaciones que atiende."""
    est = linea.estaciones
    km = dict(zip(est, linea.cfg["km"]))
    dist = abs(km[a] - km[b])
    base = dist / float(linea.cfg["velocidad_comercial_kmh"]) * 60.0
    i, j = sorted((est.index(a), est.index(b)))
    usados = [r for r in RAMALES_CENTRO if r & set(paradas)]
    ajeno = set().union(*(r for r in RAMALES_CENTRO if r not in usados)) if usados else set(RAMALES_CENTRO[1])
    intermedias = abs(paradas.index(b) - paradas.index(a)) - 1
    omitidas = max(0, len(set(est[i + 1:j]) - ajeno) - intermedias)
    return max(base - AHORRO_PARADA_MIN * omitidas, dist / VEL_CRUCERO_KMH * 60.0), intermedias


def _tramos_servicio(a: str, b: str, sentido: str):
    """Servicios cuyo recorrido en ``sentido`` pasa por ``a`` y después por ``b``."""
    for nombre, reg in H.servicios("metropolitano").items():
        paradas = (reg.get("paradas") or {}).get(sentido) or []
        if a in paradas and b in paradas and paradas.index(a) < paradas.index(b):
            yield nombre, reg, paradas


def _espera(intervalo: float, cv: float, p_no_subir: float) -> float:
    """Espera media con llegadas al azar más la probabilidad de no poder subir (``model/ocupacion.espera``)."""
    return intervalo * (1 + cv ** 2) / 2.0 + intervalo * p_no_subir


def _opcion_troncal(linea, a: str, b: str, sentido: str, momento: dt.datetime, intervalo_modelo: float,
                    p_no_subir: float, mult: float) -> dict | None:
    """Mejor forma de ir de ``a`` a ``b`` en ``momento``: servicio directo o, si no hay, un transbordo."""
    def tramo(nombre, reg, paradas, x, y):
        viaje, intermedias = _viaje_servicio(linea, x, y, paradas)
        publicado = H.intervalo_min(reg, momento)
        return {"servicio": nombre, "sube": x, "baja": y, "viaje_min": viaje, "paradas_intermedias": intermedias,
                "intervalo_min": publicado or intervalo_modelo, "frecuencia_publicada": publicado is not None,
                "espera_min": _espera(publicado or intervalo_modelo, linea.cv, p_no_subir)}

    def costo(tramos):
        return (R.A_ESPERA * sum(t["espera_min"] for t in tramos) + mult * sum(t["viaje_min"] for t in tramos)
                + PENALIZACION_TRANSBORDO_MIN * (len(tramos) - 1))

    activos = [(n, r, p) for n, r in H.servicios("metropolitano").items()
               if H.opera(r, sentido, momento) and (p := (r.get("paradas") or {}).get(sentido))]
    directos = [[tramo(n, r, p, a, b)] for n, r, p in activos if a in p and b in p and p.index(a) < p.index(b)]
    if directos:
        return {"tramos": min(directos, key=costo)}
    mejor = None
    for n1, r1, p1 in activos:
        if a not in p1:
            continue
        for n2, r2, p2 in activos:
            if n2 == n1 or b not in p2:
                continue
            for x in p1[p1.index(a) + 1:]:
                if x in linea.estaciones and x in p2[:p2.index(b)]:
                    tramos = [tramo(n1, r1, p1, a, x), tramo(n2, r2, p2, x, b)]
                    if mejor is None or costo(tramos) < costo(mejor):
                        mejor = tramos
    return {"tramos": mejor} if mejor else None


# --------------------------------------------------------------------------- planificador
def _validar_par(est_a: dict | None, est_b: dict | None):
    if est_a is None or est_b is None:
        raise MS.PrediccionError("Estación de origen o de destino no encontrada", 404)
    sistema, serie = serie_de_estacion(est_a)
    sistema_b, serie_b = serie_de_estacion(est_b)
    if serie is None or serie_b is None:
        raise MS.PrediccionError("Uno de los dos paraderos no tiene pronóstico disponible", 404)
    if sistema != sistema_b:
        raise MS.PrediccionError("Por ahora el viaje debe ser dentro del mismo sistema (sin transbordo entre sistemas)", 422)
    if sistema in ("corredor", "alimentador") and serie != serie_b:
        raise MS.PrediccionError("Los dos paraderos deben ser de la misma ruta", 422)
    if (est_a["id"], est_a["name"]) == (est_b["id"], est_b["name"]) or (sistema in ("metro_l1", "troncal") and serie == serie_b):
        raise MS.PrediccionError("El destino coincide con el origen", 422)
    if sistema == "corredor" and not RV._sentido_valido(sistema, serie, est_a, est_b):
        raise MS.PrediccionError("En esa ruta el paradero de destino queda antes que el de subida: elige el "
                                 "paradero del sentido contrario", 422)
    return sistema, serie, serie_b


def _contexto(est_a: dict, est_b: dict | None, fecha: dt.date) -> dict:
    """Pronóstico del día en el paradero de subida y todo lo necesario para evaluar una salida.

    Sin ``est_b`` (solo se conoce el paradero) no hay tiempo a bordo ni servicio: se evalúan aforo y espera.
    """
    from routes.predictions import _item   # evita import circular

    if est_b is not None:
        sistema, serie, serie_b = _validar_par(est_a, est_b)
    else:
        (sistema, serie), serie_b = serie_de_estacion(est_a), None
        if serie is None:
            raise MS.PrediccionError("Este paradero no tiene pronóstico disponible", 404)
    hacia = serie_b if sistema in ("metro_l1", "troncal") else None
    paradero = (est_a.get("raw_properties") or {}).get("cod_paradero") if sistema == "corredor" else None
    res = MS.prediccion_serie(sistema, serie, fecha.isoformat(), hacia=hacia, paradero=paradero)
    horas = [_item(f, res["sentido"], res["sentidos"]) for f in res["filas"]]
    linea = MS.modelo(sistema).linea
    if est_b is None:
        viaje_base = None
    elif sistema == "alimentador":    # sin orden de paradas: distancia recta con factor de rodeo
        viaje_base = RV._haversine_m(est_a, est_b) / 1000.0 * RV.FACTOR_RODEO / linea.velocidad_kmh() * 60.0
    else:
        viaje_base = RV._viaje_min(sistema, serie, est_a, est_b)
    con_servicio = [h["eta_min"] is not None for h in horas]
    serie_de = lambda campo: [h.get(campo) if ok else None for h, ok in zip(horas, con_servicio)]  # noqa: E731
    return {
        "sistema": sistema, "serie": serie, "serie_b": serie_b, "fecha": fecha, "res": res, "horas": horas, "linea": linea,
        "veh": linea.veh if hasattr(linea, "veh") else linea.vehiculo(serie), "viaje_base": viaje_base,
        "reg_linea": None if sistema == "troncal" else H.servicio(sistema, serie),
        "ocupacion": serie_de("crowding"), "multiplicador": serie_de("multiplicador_hacinamiento"),
        "p_no_subir": serie_de("probabilidad_no_subir"),
    }


def _evaluar(ctx: dict, salida: int, esperas: dict[int, float] | None = None) -> dict | None:
    """Una salida en el minuto ``salida`` del día; None si no hay servicio a esa hora.

    ``esperas`` reemplaza la espera del modelo en las horas indicadas (p. ej. la hora actual ya
    corregida con el tráfico en vivo).
    """
    hora = ctx["horas"][salida // 60]
    momento = dt.datetime.combine(ctx["fecha"], dt.time(salida // 60, salida % 60))
    ocup = interpolar(ctx["ocupacion"], salida)
    if ocup is None:
        return None                                                # el modelo no da servicio a esa hora
    mult = interpolar(ctx["multiplicador"], salida) or 1.0
    pns = interpolar(ctx["p_no_subir"], salida) or 0.0
    intervalo = hora.get("intervalo_min") or (hora["eta2_min"] - hora["eta_min"])
    tramos = None
    if ctx["sistema"] == "troncal" and ctx["serie_b"]:
        opcion = _opcion_troncal(ctx["linea"], ctx["serie"], ctx["serie_b"], ctx["res"]["sentido"], momento, intervalo, pns, mult)
        if opcion is None:
            return None                                            # ningún servicio publicado une A y B a esa hora
        tramos = opcion["tramos"]
        espera, viaje = sum(t["espera_min"] for t in tramos), sum(t["viaje_min"] for t in tramos)
    else:
        if H.opera(ctx["reg_linea"], None, momento) is False:
            return None                                            # fuera del horario publicado
        espera, viaje = (esperas or {}).get(salida // 60, hora["eta_min"]), ctx["viaje_base"]
    return {
        "salida": _hhmm(salida), "llegada": _hhmm(salida + espera + viaje) if viaje is not None else None,
        "espera_min": round(espera, 1), "viaje_min": round(viaje, 1) if viaje is not None else None,
        "intervalo_min": round(intervalo, 1), "ocupacion": round(ocup, 3), "clase": clase_de(ocup, ctx["veh"]),
        "franja": franja_de(momento),
        "tramos": [{**t, "viaje_min": round(t["viaje_min"], 1), "espera_min": round(t["espera_min"], 1),
                    "intervalo_min": round(t["intervalo_min"], 1)} for t in tramos] if tramos else None,
        "_exacto": (espera, viaje, mult, intervalo),               # valores sin redondear; no se devuelven
    }


def proximas_salidas(est_a: dict, est_b: dict | None, ahora: dt.datetime, cuantas: int = 6,
                     esperas: dict[int, float] | None = None) -> dict:
    """Aforo interpolado de este momento y las próximas salidas, cada 10 minutos, del mismo día.

    Con ``est_b`` cada salida trae la hora estimada de llegada y, en el Metropolitano, el servicio.
    """
    ctx = _contexto(est_a, est_b, ahora.date())
    minuto = ahora.hour * 60 + ahora.minute
    ocup = interpolar(ctx["ocupacion"], minuto)
    salidas = []
    for salida in range(-(-minuto // PASO_MIN) * PASO_MIN, 24 * 60, PASO_MIN):
        if len(salidas) >= cuantas:
            break
        o = _evaluar(ctx, salida, esperas)
        if o is not None:
            o.pop("_exacto")
            salidas.append(o)
    return {
        "ahora": None if ocup is None else {"hora": _hhmm(minuto), "crowding": round(ocup, 3), "class": clase_de(ocup, ctx["veh"])},
        "proximas_salidas": salidas,
    }


def planificar(est_a: dict | None, est_b: dict | None, dia: str | None, llegada: str) -> dict:
    """Salidas posibles para llegar a ``est_b`` antes de ``llegada`` (HH:MM) y la recomendada."""
    if est_a is None or est_b is None:
        raise MS.PrediccionError("Estación de origen o de destino no encontrada", 404)
    limite = _minuto(llegada)
    fecha = MS.parsear_dia(dia)
    ctx = _contexto(est_a, est_b, fecha)
    sistema, serie, serie_b, res, linea = ctx["sistema"], ctx["serie"], ctx["serie_b"], ctx["res"], ctx["linea"]
    troncal = sistema == "troncal"

    opciones = []
    for salida in range((limite // PASO_MIN) * PASO_MIN, max(-1, limite - HORIZONTE_MIN - 1), -PASO_MIN):
        o = _evaluar(ctx, salida)
        if o is None:
            continue
        espera, viaje, mult, intervalo = o.pop("_exacto")
        margen = limite - (salida + espera + viaje)
        transbordo = bool(o["tramos"]) and len(o["tramos"]) > 1
        opciones.append({
            **o, "margen_min": round(margen, 1),
            "estado": "tarde" if margen < 0 else ("con_margen" if margen >= intervalo else "justo"),
            "costo_min": round(float(R.costo(espera, viaje, mult)) + PENALIZACION_TRANSBORDO_MIN * transbordo
                               + PESO_ANTICIPACION * max(margen, 0.0), 1),
        })
    opciones.reverse()                                             # de la más temprana a la más tardía

    a_tiempo = [o for o in opciones if o["estado"] != "tarde"]
    candidatas = [o for o in a_tiempo if o["estado"] == "con_margen"] or a_tiempo
    recomendada = min(candidatas, key=lambda o: o["costo_min"]) if candidatas else None
    ultima = a_tiempo[-1] if a_tiempo else None
    tarde = [o for o in opciones if o["estado"] == "tarde"][:2]     # dos salidas tardías bastan como referencia
    visibles = [o for o in opciones if (o["estado"] != "tarde" and o["margen_min"] <= VENTANA_MIN)
                or o is recomendada or o in tarde]
    comoda = min((o for o in visibles if o["estado"] != "tarde"), key=lambda o: (o["ocupacion"], -_minuto(o["salida"])), default=None)

    return {
        "origen": {"id": est_a["id"], "name": est_a["name"]}, "destino": {"id": est_b["id"], "name": est_b["name"]},
        "system": sistema, "series": serie, "sentido": (res["sentidos"] or {}).get(res["sentido"]) if res["sentido"] else None,
        "dia": fecha.isoformat(), "tipo_dia": H.tipo_dia(fecha), "llegada_limite": _hhmm(limite),
        "referencia": res["referencia"],
        "opciones": visibles,
        "recomendada": recomendada["salida"] if recomendada else None,
        "ultima_puntual": ultima["salida"] if ultima else None,
        "mas_comoda": comoda["salida"] if comoda else None,
        "motivo": _motivo(recomendada, ultima, bool(opciones)),
        "servicios": _servicios(sistema, serie, serie_b, res["sentido"], linea, fecha, recomendada or ultima, limite),
        "seguridad": _seguridad(recomendada or ultima),
        "supuestos": [
            "El aforo se pronostica por hora; dentro de la hora se interpola entre horas vecinas (aproximado).",
            "La espera es la esperada según la frecuencia: no hay posición en vivo de los vehículos.",
            "«Con margen» significa que llegas a tiempo aunque pierdas un vehículo.",
            *(["En el Metropolitano el aforo es el de la estación, igual para todos los servicios; cada parada "
               f"omitida por un expreso ahorra {str(AHORRO_PARADA_MIN).replace('.', ',')} min (supuesto)."] if troncal else []),
            *(["En alimentadores el aforo es el del sentido más cargado de la ruta y el tiempo a bordo se estima "
               "con la distancia en línea recta entre los dos paraderos."] if sistema == "alimentador" else []),
        ],
        "fuente_horarios": H.fuente(),
    }


def _motivo(rec: dict | None, ultima: dict | None, hay_servicio: bool) -> str:
    if rec is None:
        return ("No hay una salida que llegue a tiempo ese día: prueba con una hora de llegada más tarde."
                if hay_servicio else "No hay servicio publicado para ese viaje en las horas previas a tu llegada.")
    base = f"Llegas a las {rec['llegada']}, {round(rec['margen_min'])} min antes, y viajas {ETIQUETA_CLASE[rec['clase']]}."
    if rec["estado"] == "justo":
        return base + " Vas con el tiempo justo: si pierdes un vehículo, llegas tarde."
    if ultima and ultima is not rec and ultima["clase"] != rec["clase"]:
        return base + f" Si sales a las {ultima['salida']} también llegas, pero viajas {ETIQUETA_CLASE[ultima['clase']]}."
    if ultima and ultima is not rec:
        return base + f" La salida de las {ultima['salida']} también llega, pero sin margen para perder un vehículo."
    return base


def _seguridad(opcion: dict | None) -> dict | None:
    if opcion is None:
        return None
    llega = int(opcion["llegada"][:2])
    return {"franja_salida": opcion["franja"], "franja_llegada": "noche" if llega >= 18 or llega < 6 else "dia",
            "nota": "La franja (día: 06:00-17:59; noche: el resto) es la que usa la ruta peatonal segura. Para el tramo "
                    "a pie, abre la estación en el mapa. El riesgo se basa en denuncias: hay subregistro y sesgo social."}


def _servicios(sistema, serie, serie_b, sentido, linea, fecha, opcion, limite) -> list[dict]:
    """Servicios que unen A y B, con su horario del día y si circulan a la hora de la salida elegida."""
    minuto = _minuto(opcion["salida"]) if opcion else max(0, limite - 30)
    momento = dt.datetime.combine(fecha, dt.time(minuto // 60, minuto % 60))

    def fila(nombre, reg, sent, extra=None):
        return {"nombre": nombre, "opera": H.opera(reg, sent, momento), "horario": H.texto_horario(reg, sent, fecha),
                "intervalo_min": H.intervalo_min(reg, momento), "url": (reg or {}).get("url"),
                "notas": (reg or {}).get("notas") or [], **(extra or {})}

    if sistema != "troncal":
        nombre = {"metro_l1": "Línea 1", "corredor": f"Ruta {serie}", "alimentador": f"Alimentador {serie}"}[sistema]
        return [fila(nombre, H.servicio(sistema, serie), None)]
    out = []
    for nombre, reg, paradas in _tramos_servicio(serie, serie_b, sentido):
        if sentido not in (reg.get("horario") or {}):
            continue                                               # no circula en este sentido
        viaje, intermedias = _viaje_servicio(linea, serie, serie_b, paradas)
        out.append(fila(nombre, reg, sentido, {"viaje_min": round(viaje, 1), "paradas_intermedias": intermedias}))
    return sorted(out, key=lambda s: (not s["opera"], s["viaje_min"]))
