# SPDX-License-Identifier: Apache-2.0
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def widget(items, label):
    return next(item for item in items if item.label == label)


class GuidedUiTests(unittest.TestCase):
    def test_first_use_and_manual_service_without_credentials(self):
        with tempfile.TemporaryDirectory() as folder, patch("core.DATA_ROOT", Path(folder)), patch("core.Arca") as arca:
            app = AppTest.from_file(APP).run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.tabs), 5)
            widget(app.text_input, "Nombre del cliente").set_value("Cliente ficticio")
            widget(app.text_input, "Importe por unidad, en pesos").set_value("12500,50")
            widget(app.text_area, "Descripción del servicio").set_value("Consultoría de diseño")
            widget(app.button, "Agregar a la lista para revisar").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.session_state["draft_rows"]), 1)
            self.assertEqual(app.session_state["draft_rows"][0]["observaciones"], "Consultoría de diseño")
            self.assertTrue(widget(app.button, "Generar comprobantes de prueba").disabled)
            # Forge the action even though the browser button is disabled.
            widget(app.button, "Generar comprobantes de prueba").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any("confirmá el lote" in error.value for error in app.error))
            arca.assert_not_called()

    def test_production_cannot_be_enabled_without_acknowledgement(self):
        with tempfile.TemporaryDirectory() as folder, patch("core.DATA_ROOT", Path(folder)), patch("setup_config.DATA_ROOT", Path(folder)):
            app = AppTest.from_file(APP).run()
            widget(app.text_input, "Nombre o razón social").set_value("Profesional ficticio")
            widget(app.text_input, "CUIT (11 dígitos, sin guiones)").set_value("20123456789")
            widget(app.radio, "¿Dónde querés trabajar?").set_value("Producción: facturas reales")
            widget(app.button, "Guardar mis datos").click().run()
            self.assertFalse(app.exception)
            self.assertFalse((Path(folder) / "config.json").exists())
            self.assertTrue(any("confirmá" in error.value for error in app.error))
