# SPDX-License-Identifier: Apache-2.0
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core import ROOT, emit_batch, parse_csv


class EmissionPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.rows = parse_csv((ROOT / "facturas_ejemplo.csv").read_bytes())
        self.config = dict(entorno="homologacion", cuit="20123456789", punto_venta=1)
        self.api = MagicMock()
        self.api.ws.service.FECompUltimoAutorizado.return_value = SimpleNamespace(Errors=None, CbteNro=0)

    def test_production_requires_confirmation_before_any_write_or_network(self):
        with tempfile.TemporaryDirectory() as folder, patch("core.DATA_ROOT", Path(folder)), patch("core.Arca") as create_api:
            with self.assertRaisesRegex(ValueError, "confirmación"):
                emit_batch(self.rows,dict(self.config,entorno="produccion"))
            self.assertEqual(list(Path(folder).iterdir()),[])
            create_api.assert_not_called()

    def test_uncertain_reply_remains_pending_and_blocks_next_call(self):
        self.api.issue.return_value = {}
        with tempfile.TemporaryDirectory() as folder, patch("core.DATA_ROOT", Path(folder)), patch("core.Arca", return_value=self.api) as create_api:
            result = emit_batch(self.rows, self.config)
            self.assertEqual(result[0]["estado"], "pendiente")
            with self.assertRaisesRegex(ValueError, "inciertas"):
                emit_batch(self.rows, self.config)
            create_api.assert_called_once()
            self.api.issue.assert_called_once()

    def test_authorized_record_is_reused_without_network_or_payload_change(self):
        self.api.issue.return_value = {"FeDetResp": {"FECAEDetResponse": [{"Resultado": "A", "CAE": "12345678901234"}]}}
        with tempfile.TemporaryDirectory() as folder, patch("core.DATA_ROOT", Path(folder)), patch("core.Arca", return_value=self.api) as create_api:
            first = emit_batch(self.rows, self.config)
            again = emit_batch(self.rows, self.config)
            self.assertEqual(first, again)
            create_api.assert_called_once()
            changed = [dict(self.rows[0], total="999.00")]
            with self.assertRaisesRegex(ValueError, "datos distintos"):
                emit_batch(changed, self.config)
            self.api.issue.assert_called_once()
