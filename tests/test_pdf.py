# SPDX-License-Identifier: Apache-2.0
import json
from decimal import Decimal
import unittest
from pathlib import Path
from unittest.mock import patch

from core import parse_csv, test_pdf


class InvoicePdfTests(unittest.TestCase):
    def test_shared_template_generates_pdf_and_only_production_qr(self):
        root = Path(__file__).resolve().parents[1]
        row = parse_csv((root / 'facturas_ejemplo.csv').read_bytes())[0]
        config = json.loads((root / 'config.example.json').read_text(encoding='utf-8'))
        result = {'numero': 7, 'respuesta': {
            'FeCabResp': {'PtoVta': 1},
            'FeDetResp': {'FECAEDetResponse': [{
                'CbteDesde': 7, 'CAE': '12345678901234', 'CAEFchVto': '20261010',
            }]},
        }}
        with patch('generate_invoice_pdf.draw_qr') as qr:
            data = test_pdf(row, result, config)
            self.assertTrue(data.startswith(b'%PDF-'))
            qr.assert_not_called()
            config['entorno'] = 'produccion'
            data = test_pdf(row, result, config)
            self.assertTrue(data.startswith(b'%PDF-'))
            qr.assert_called_once()
            payload = qr.call_args.args[-1]
            self.assertEqual(Decimal(str(payload['importe'])), Decimal(row['total']))
            self.assertEqual(payload['nroCmp'], 7)
            self.assertEqual(payload['ptoVta'], 1)
            self.assertEqual(payload['codAut'], 12345678901234)


if __name__ == '__main__':
    unittest.main()
