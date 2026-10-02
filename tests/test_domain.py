# SPDX-License-Identifier: Apache-2.0
import unittest
from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal

from domain import Authorization, BillingEnvironment, BillingPeriod, BusinessRuleError, Customer, InvoiceDraft, InvoiceState, Issuer, ServiceItem


class BusinessRulesTests(unittest.TestCase):
    def test_any_service_uses_exact_decimal_total(self):
        item = ServiceItem("Consultoría de diseño", 3, Decimal("12500.50"))
        invoice = InvoiceDraft("estable-001", Customer("Cliente"), item, BillingPeriod(date(2026, 9, 30), date(2026, 9, 1), date(2026, 9, 30), date(2026, 10, 10)))
        self.assertEqual(invoice.total, Decimal("37501.50"))
        with self.assertRaises(FrozenInstanceError):
            invoice.identifier = "otro"

    def test_invalid_quantities_and_prices_are_rejected(self):
        for quantity, price in [(0, "1"), (-1, "1"), (True, "1"), (1, "0"), (1, "1.001"), (1, "NaN"), (1, "Infinity")]:
            with self.subTest(quantity=quantity, price=price), self.assertRaises(BusinessRuleError):
                ServiceItem("Servicio", quantity, Decimal(price))

    def test_optional_dni_and_supported_customer_condition(self):
        self.assertEqual(Customer("Cliente").dni, "")
        for changes in [dict(name=""), dict(name="Cliente", dni="1234"), dict(name="Cliente", vat_condition=1)]:
            with self.subTest(changes=changes), self.assertRaises(BusinessRuleError):
                Customer(**changes)

    def test_scope_separates_fiscal_identity_and_environment(self):
        a = Issuer("20123456789", 1, "Emisor")
        b = Issuer("20123456789", 1, "Emisor", BillingEnvironment.PRODUCTION)
        c = Issuer("20123456789", 2, "Emisor")
        self.assertEqual(a.scope, "homo:20123456789:1")
        self.assertEqual(len({a.scope, b.scope, c.scope}), 3)

    def test_inconsistent_period_is_rejected(self):
        with self.assertRaises(BusinessRuleError):
            BillingPeriod(date(2026, 9, 30), date(2026, 9, 30), date(2026, 9, 1), date(2026, 10, 10))
        with self.assertRaises(BusinessRuleError):
            BillingPeriod(date(2026, 9, 30), date(2026, 9, 1), date(2026, 9, 30), date(2026, 9, 29))

    def test_only_explicit_rejection_allows_retry(self):
        self.assertFalse(InvoiceState.PENDING.allows_retry)
        self.assertFalse(InvoiceState.AUTHORIZED.allows_retry)
        self.assertTrue(InvoiceState.REJECTED.allows_retry)
        for response in [{}, {"FeDetResp": {"FECAEDetResponse": [{"Resultado": "A"}]}}, {"FeDetResp": {"FECAEDetResponse": [{"Resultado": "R", "CAE": "123"}]}}]:
            self.assertEqual(Authorization.from_response(response).state, InvoiceState.PENDING)
        self.assertEqual(Authorization.from_response({"FeDetResp": {"FECAEDetResponse": [{"Resultado": "R"}]}}).state, InvoiceState.REJECTED)
        self.assertEqual(Authorization.from_response({"FeDetResp": {"FECAEDetResponse": [{"Resultado": "A", "CAE": "123"}]}}).state, InvoiceState.AUTHORIZED)

    def test_authorized_state_requires_cae(self):
        with self.assertRaises(BusinessRuleError):
            Authorization(InvoiceState.AUTHORIZED)
