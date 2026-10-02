# Entidades y reglas de negocio / Business entities and rules

Las entidades están en `domain.py`, usan solo la biblioteca estándar y son inmutables. No dependen de Streamlit, Docker, SQLite, SOAP ni del formato CSV. Los adaptadores convierten las entradas técnicas en entidades; las reglas se mantienen aunque cambien esos adaptadores.

| Entidad | Regla pequeña y estable |
|---|---|
| `Issuer` | CUIT de 11 dígitos no ficticio, punto de venta de 1 a 99999 y nombre obligatorio. El scope distingue entorno, CUIT y punto de venta. |
| `Customer` | Nombre obligatorio; DNI opcional de 7 u 8 dígitos. El alcance actual admite consumidor final (5). |
| `ServiceItem` | Descripción libre de hasta 500 caracteres, cantidad entera positiva e importe positivo con hasta dos decimales. El total se calcula con Decimal. |
| `BillingPeriod` | El inicio no puede ser posterior al fin; el vencimiento del pago no puede preceder a la fecha de factura. |
| `InvoiceDraft` | Identificador estable no vacío; combina cliente, servicio y período. Cambiar de interfaz no debe cambiar ese ID. |
| `Authorization` | Autorizada requiere respuesta A con CAE. Rechazada requiere rechazo R explícito sin CAE. Respuestas incompletas o contradictorias quedan pendientes. |
| `InvoiceState` | Solo un rechazo explícito permite reintento revisado. Un pendiente exige consulta y conciliación; una autorizada devuelve lo guardado. |

`core.parse_csv` adapta el CSV y aplica estas entidades. `setup_config.validate_config` aplica `Issuer` y luego las reglas técnicas de rutas. `core.emit_batch` usa `Authorization` para clasificar respuestas, reserva persistentemente antes de enviar y mantiene la identidad `(scope,id)`. La base impide cambiar el payload ya registrado con el mismo ID y bloquea lotes si hay pendientes. El guardado sigue en SQLite, pero esas condiciones deberán mantenerse en cualquier reemplazo.

Los nombres heredados del CSV son un detalle del adaptador: `sesiones` se convierte en cantidad y `precio_sesion` en precio por unidad. Una entidad de servicio puede representar consultoría, clases, reparaciones u otros servicios dentro del alcance fiscal soportado. No se implementan productos, cantidades fraccionarias, varias líneas por factura ni otros tipos fiscales.

Las reglas expresan el alcance de este programa, no una certificación de la normativa fiscal vigente. La longitud del CUIT es una validación de formato, no una verificación de identidad o autorización ARCA. La emisión real sigue requiriendo autorización explícita del usuario y controles de la interfaz. El scope fiscal no equivale a autenticación o aislamiento SaaS.

## Cómo conservar las reglas

Al reemplazar interfaz, persistencia o proveedor, conservar las entidades y ejecutar `tests/test_domain.py` y `tests/test_emission.py`. Cambiar reglas por una necesidad de negocio explícita, con documentación y pruebas de aceptación; no como efecto secundario de una migración técnica. Mantener el mapeo de IDs existentes y conciliar estados pendientes antes de migrar datos.

## English

`domain.py` contains immutable, standard-library-only entities independent of UI, containers, persistence, SOAP and CSV. `Issuer` defines fiscal scope; `Customer` supports final consumers and optional DNI; `ServiceItem` validates description, positive integer quantity and exact Decimal pricing; `BillingPeriod` checks date coherence; `InvoiceDraft` retains a stable identifier; `Authorization` and `InvoiceState` preserve issuance certainty.

Only explicit rejection permits a reviewed retry. An incomplete response remains pending and blocks further issuance until reconciliation. Authorized records are returned unchanged. Persistence must retain `(scope,id)`, save a reservation before sending, and reject payload changes for existing identifiers. CSV field names belong to the adapter, not the domain.

These rules define supported application behavior, not current legal compliance. A CUIT format check does not establish identity; fiscal scope does not establish SaaS authorization. Preserve domain and persistence acceptance tests when replacing technical components. Change a rule only for an explicit business requirement and document the migration of existing records.
