# SPDX-License-Identifier: Apache-2.0
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import parse_csv, soap_transport
from security import MAX_BATCH_ROWS, MAX_CSV_BYTES, private_file, safe_data_path, write_private_json

HEADER = "id,nombre,documento,fecha,desde,hasta,vencimiento,sesiones,precio_sesion,condicion_iva"
ROW = "{identifier},Cliente,,2026-09-30,2026-09-01,2026-09-30,2026-10-10,1,10,5"


class BoundaryTests(unittest.TestCase):
    def test_oversize_csv_and_batch_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "5 MB"):
            parse_csv(b"x" * (MAX_CSV_BYTES + 1))
        content = HEADER + "\n" + "\n".join(ROW.format(identifier=str(i)) for i in range(MAX_BATCH_ROWS + 1))
        with self.assertRaisesRegex(ValueError, "500"):
            parse_csv(content.encode())

    def test_malformed_headers_extra_cells_and_formula_are_rejected(self):
        for content in [HEADER + ",id\n" + ROW.format(identifier="a") + ",a", HEADER + "\n" + ROW.format(identifier="a") + ",extra", HEADER + "\n" + ROW.format(identifier="=1+1")]:
            with self.subTest(content=content), self.assertRaises(ValueError):
                parse_csv(content.encode())

    def test_path_traversal_and_windows_absolute_paths_are_rejected_on_any_os(self):
        with tempfile.TemporaryDirectory() as folder:
            for value in ["../outside.key", "/outside.key", "C:/private.key", "\\server\share\key.pem", "certificados/key.pem\x00"]:
                with self.subTest(value=value), self.assertRaises(ValueError):
                    safe_data_path(Path(folder), value)

    def test_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root / "target.pem").write_text("fictional")
            try:
                (root / "link.pem").symlink_to(root / "target.pem")
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks are unavailable for this account")
            with self.assertRaises(ValueError):
                safe_data_path(root, "link.pem")

    def test_private_storage_is_atomic_and_restrictive(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            write_private_json(root,"ticket.json",{"token":"fictional"})
            self.assertEqual(json.loads((root / "ticket.json").read_text()),{"token":"fictional"})
            db=private_file(root,"records.sqlite3")
            self.assertEqual(list(root.glob(".private-*")),[])
            if os.name != "nt":
                self.assertEqual(db.stat().st_mode & 0o777,0o600)
                self.assertEqual((root / "ticket.json").stat().st_mode & 0o777,0o600)

    def test_tls_downgrade_is_not_the_default(self):
        with patch.dict(os.environ,{"ARCA_ALLOW_LEGACY_TLS":"0"}):
            transport=soap_transport("produccion")
            self.assertTrue(transport.session.verify)
            self.assertFalse(transport.session.trust_env)
            self.assertEqual(type(transport.session.adapters["https://"]).__name__,"HTTPAdapter")
