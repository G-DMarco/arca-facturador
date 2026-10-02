# SPDX-License-Identifier: Apache-2.0
"""Business entities. No UI, filesystem, database, network or framework imports."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum


class BusinessRuleError(ValueError):
    """An invoice violates the supported business rules."""


class BillingEnvironment(str, Enum):
    TESTING = "homologacion"
    PRODUCTION = "produccion"


class InvoiceState(str, Enum):
    PENDING = "pendiente"
    AUTHORIZED = "autorizada"
    REJECTED = "rechazada"

    @property
    def allows_retry(self):
        return self is InvoiceState.REJECTED


@dataclass(frozen=True)
class Issuer:
    cuit: str
    point_of_sale: int
    name: str
    environment: BillingEnvironment = BillingEnvironment.TESTING

    def __post_init__(self):
        if not self.cuit.isascii() or not self.cuit.isdigit() or len(self.cuit) != 11 or self.cuit == "00000000000":
            raise BusinessRuleError("Ingresá tu CUIT de 11 dígitos, sin guiones.")
        if not isinstance(self.point_of_sale, int) or isinstance(self.point_of_sale, bool) or not 1 <= self.point_of_sale <= 99999:
            raise BusinessRuleError("El punto de venta debe estar entre 1 y 99999.")
        if not self.name.strip():
            raise BusinessRuleError("Ingresá el nombre del profesional.")
        if not isinstance(self.environment, BillingEnvironment):
            raise BusinessRuleError("Entorno de facturación inválido")

    @property
    def scope(self):
        prefix = "prod" if self.environment is BillingEnvironment.PRODUCTION else "homo"
        return f"{prefix}:{self.cuit}:{self.point_of_sale}"


@dataclass(frozen=True)
class Customer:
    name: str
    dni: str = ""
    vat_condition: int = 5

    def __post_init__(self):
        if not self.name.strip():
            raise BusinessRuleError("Nombre del cliente vacío")
        if self.dni and (not self.dni.isascii() or not self.dni.isdigit() or not 7 <= len(self.dni) <= 8):
            raise BusinessRuleError("DNI inválido; si se informa debe tener 7 u 8 dígitos")
        if self.vat_condition != 5:
            raise BusinessRuleError("Esta versión admite solamente consumidor final (5)")


@dataclass(frozen=True)
class ServiceItem:
    description: str
    quantity: int
    unit_price: Decimal

    def __post_init__(self):
        if not isinstance(self.quantity, int) or isinstance(self.quantity, bool) or self.quantity <= 0:
            raise BusinessRuleError("La cantidad debe ser un entero positivo")
        try:
            valid_price = isinstance(self.unit_price, Decimal) and self.unit_price.is_finite() and self.unit_price > 0 and self.unit_price == self.unit_price.quantize(Decimal("0.01"))
        except InvalidOperation:
            valid_price = False
        if not valid_price:
            raise BusinessRuleError("Precio inválido; máximo 2 decimales")
        if not self.description.strip():
            raise BusinessRuleError("La descripción del servicio no puede estar vacía")
        if len(self.description) > 500:
            raise BusinessRuleError("La descripción del servicio admite hasta 500 caracteres")

    @property
    def total(self):
        return (self.unit_price * self.quantity).quantize(Decimal("0.01"))


@dataclass(frozen=True)
class BillingPeriod:
    invoice_date: date
    start: date
    end: date
    due_date: date

    def __post_init__(self):
        if self.start > self.end or self.due_date < self.invoice_date:
            raise BusinessRuleError("Período o vencimiento incoherente")


@dataclass(frozen=True)
class InvoiceDraft:
    identifier: str
    customer: Customer
    service: ServiceItem
    period: BillingPeriod

    def __post_init__(self):
        if not self.identifier.strip():
            raise BusinessRuleError("ID vacío")

    @property
    def total(self):
        return self.service.total



@dataclass(frozen=True)
class Authorization:
    state: InvoiceState
    cae: str = ""

    def __post_init__(self):
        if not isinstance(self.state, InvoiceState):
            raise BusinessRuleError("Estado de autorización inválido")
        if self.state is InvoiceState.AUTHORIZED and not self.cae:
            raise BusinessRuleError("Una factura autorizada requiere CAE")
        if self.state is not InvoiceState.AUTHORIZED and self.cae:
            raise BusinessRuleError("Un CAE no puede acompañar un estado sin autorización")

    @classmethod
    def from_response(cls, response):
        details = (response.get("FeDetResp") or {}).get("FECAEDetResponse") or []
        if len(details) != 1:
            return cls(InvoiceState.PENDING)
        detail = details[0]
        result, cae = detail.get("Resultado"), detail.get("CAE")
        if result == "A" and cae:
            return cls(InvoiceState.AUTHORIZED, str(cae))
        if result == "R" and not cae:
            return cls(InvoiceState.REJECTED)
        # Missing, contradictory or unrecognized replies are uncertain, not rejections.
        return cls(InvoiceState.PENDING)
