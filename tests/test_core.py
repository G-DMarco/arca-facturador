# SPDX-License-Identifier: Apache-2.0
import unittest

from core import parse_csv


HEADER = (
    "id,nombre,documento,fecha,desde,hasta,vencimiento,"
    "sesiones,precio_sesion,condicion_iva"
)


def csv_bytes(*rows):
    return ("\n".join((HEADER, *rows)) + "\n").encode("utf-8")


class ParseCsvTests(unittest.TestCase):
    def test_valid_monthly_invoice_row_calculates_total_and_description(self):
        rows = parse_csv(
            csv_bytes(
                "2026-09-P001,Paciente Ejemplo,12345678,2026-09-30,"
                "2026-09-01,2026-09-30,2026-10-10,4,25000,5"
            )
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["total"], "100000.00")
        self.assertTrue(rows[0]["descripcion"].startswith("4 unidades de servicio"))
        self.assertIn("Cliente: Paciente Ejemplo", rows[0]["descripcion"])
        self.assertIn("2026-09-01 a 2026-09-30", rows[0]["descripcion"])

    def test_semicolon_csv_accepts_quoted_decimal_comma(self):
        data = (
            "id;nombre;documento;fecha;desde;hasta;vencimiento;"
            "sesiones;precio_sesion;condicion_iva\n"
            '2026-09-P002;Paciente Dos;23456789;2026-09-30;'
            '2026-09-01;2026-09-30;2026-10-10;2;"12500,50";5\n'
        ).encode("utf-8")

        rows = parse_csv(data)

        self.assertEqual(rows[0]["total"], "25001.00")

    def test_rejects_missing_required_columns(self):
        with self.assertRaisesRegex(ValueError, "Faltan columnas"):
            parse_csv(b"nombre,dni,periodo,sesiones,precio_sesion\nPaciente,12345678,2026-09,4,25000\n")

    def test_rejects_duplicate_ids(self):
        row = (
            "2026-09-P001,Paciente Ejemplo,12345678,2026-09-30,"
            "2026-09-01,2026-09-30,2026-10-10,4,25000,5"
        )

        with self.assertRaisesRegex(ValueError, "Fila 3"):
            parse_csv(csv_bytes(row, row))

    def test_rejects_invalid_dni(self):
        with self.assertRaisesRegex(ValueError, "DNI"):
            parse_csv(
                csv_bytes(
                    "2026-09-P001,Paciente Ejemplo,1234,2026-09-30,"
                    "2026-09-01,2026-09-30,2026-10-10,4,25000,5"
                )
            )

    def test_accepts_empty_dni_and_uses_observaciones_as_description(self):
        data = (
            HEADER + ",observaciones\n"
            "2026-09-P001,Paciente Ejemplo,,2026-09-30,"
            "2026-09-01,2026-09-30,2026-10-10,4,25000,5,"
            '"Observacion personalizada"\n'
        ).encode("utf-8")

        rows = parse_csv(data)

        self.assertEqual(rows[0]["documento"], "")
        self.assertEqual(rows[0]["descripcion"], "Observacion personalizada")

    def test_rejects_invalid_period_or_due_date(self):
        with self.assertRaisesRegex(ValueError, "Periodo|Per.odo|incoherente"):
            parse_csv(
                csv_bytes(
                    "2026-09-P001,Paciente Ejemplo,12345678,2026-09-30,"
                    "2026-09-30,2026-09-01,2026-10-10,4,25000,5"
                )
            )

    def test_rejects_more_than_two_price_decimals(self):
        with self.assertRaisesRegex(ValueError, "decimales"):
            parse_csv(
                csv_bytes(
                    "2026-09-P001,Paciente Ejemplo,12345678,2026-09-30,"
                    "2026-09-01,2026-09-30,2026-10-10,4,25000.999,5"
                )
            )

    def test_rejects_non_consumidor_final_condition(self):
        with self.assertRaisesRegex(ValueError, "consumidor final"):
            parse_csv(
                csv_bytes(
                    "2026-09-P001,Paciente Ejemplo,12345678,2026-09-30,"
                    "2026-09-01,2026-09-30,2026-10-10,4,25000,1"
                )
            )


if __name__ == "__main__":
    unittest.main()
