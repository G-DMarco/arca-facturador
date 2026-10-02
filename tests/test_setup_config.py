# SPDX-License-Identifier: Apache-2.0
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from setup_config import save_config, validate_config


def example():
    return dict(cuit="20123456789", punto_venta=1, entorno="homologacion", nombre_emisor="Profesional ficticio", certificado="certificados/emisor.crt", clave_privada="certificados/emisor.key")


class SetupTests(unittest.TestCase):
    def test_atomic_save_in_data_directory(self):
        with tempfile.TemporaryDirectory() as folder, patch("setup_config.DATA_ROOT", Path(folder)):
            save_config(example())
            self.assertEqual(json.loads((Path(folder) / "config.json").read_text()), example())
            self.assertEqual(list(Path(folder).glob(".config-*")), [])
            if os.name != "nt":
                self.assertEqual((Path(folder) / "config.json").stat().st_mode & 0o777, 0o600)

    def test_rejects_placeholder_and_outside_paths(self):
        for changes in [dict(cuit="00000000000"), dict(certificado="../outside.crt"), dict(clave_privada="/outside.key"), dict(entorno="unknown"), dict(punto_venta=0)]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_config(dict(example(), **changes))

    def test_invalid_save_preserves_previous_config(self):
        with tempfile.TemporaryDirectory() as folder, patch("setup_config.DATA_ROOT", Path(folder)):
            save_config(example())
            with self.assertRaises(ValueError):
                save_config(dict(example(), cuit="bad"))
            self.assertEqual(json.loads((Path(folder) / "config.json").read_text()), example())
