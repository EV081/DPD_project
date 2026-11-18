"""Pruebas mínimas del escenario demostrativo (solo biblioteca estándar)."""
from __future__ import annotations

import unittest
from datetime import date

from analytics.generar_simulacion import AFOROS, catalogos, generar, resumen


class SimulacionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.filas = generar(600, date(2026, 11, 12), 20261112)

    def test_reproducible_y_tamano_solicitado(self) -> None:
        segunda = generar(600, date(2026, 11, 12), 20261112)
        self.assertEqual(self.filas, segunda)
        self.assertEqual(len(self.filas), 600)
        self.assertEqual(len({fila.sesion_id for fila in self.filas}), 600)
        self.assertEqual(len({fila.usuario_id for fila in self.filas}), 600)
        self.assertTrue(all(fila.usuario_id.startswith("USR-SIM-") for fila in self.filas))

    def test_solo_usa_estaciones_del_proyecto(self) -> None:
        permitidas = {sistema: {nombre for nombre, _ in filas} for sistema, filas in catalogos().items()}
        self.assertTrue(all(fila.estacion in permitidas[fila.sistema] for fila in self.filas))

    def test_embudo_y_metricas_tienen_sentido(self) -> None:
        consultas = len(self.filas)
        vistas = sum(fila.recomendacion_vista for fila in self.filas)
        abordajes = sum(fila.abordaje_confirmado for fila in self.filas)
        feedback = sum(fila.feedback_enviado for fila in self.filas)
        self.assertGreaterEqual(consultas, vistas)
        self.assertGreaterEqual(vistas, abordajes)
        self.assertGreaterEqual(abordajes, feedback)
        datos = resumen(self.filas, 20261112, date(2026, 11, 12))
        self.assertEqual(datos["metadatos"]["modo_datos"], "simulado")
        self.assertEqual(datos["indicadores_control"]["usuarios_simulados"], 600)
        self.assertGreater(datos["indicadores_control"]["api_exito"], .9)

    def test_aforo_usa_las_clases_del_producto_y_no_inventa_encuesta(self) -> None:
        self.assertEqual(AFOROS, ("Asientos", "De_pie", "Saturado"))
        self.assertTrue(all(fila.aforo_pred in AFOROS for fila in self.filas))
        self.assertTrue(all(fila.aforo_observado in AFOROS for fila in self.filas if fila.aforo_observado))
        self.assertTrue(all("satisfaccion" not in fila.__dict__ for fila in self.filas))
        advertencia = resumen(self.filas, 20261112, date(2026, 11, 12))["metadatos"]["advertencia"]
        self.assertIn("no son predicciones LightGBM", advertencia)

    def test_no_contiene_datos_personales(self) -> None:
        for fila in self.filas:
            serializado = str(fila).lower()
            self.assertNotIn("@", serializado)
            self.assertNotIn("correo", serializado)
            self.assertNotIn("telefono", serializado)


if __name__ == "__main__":
    unittest.main()
