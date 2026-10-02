---
name: arca-facturador
description: Prepare and review service CSV batches, maintain this local ARCA Streamlit invoice application, and regenerate PDFs from authorized records. Use for this repository, its monthly batches, and public distributions without private data.
license: Apache-2.0
---

# ARCA invoice application

Locate the repository through `app.py`, `core.py`, and `config.example.json`. Distinguish a private installation with real configuration and records from a public distribution with fictional examples. Never transfer credentials or patient data into the public distribution. Resolve project paths from the repository root, not from the skill directory.

## Service CSV batches

Read the existing template header and `core.parse_csv` before preparing a batch. Preserve these column names: `id,nombre,documento,fecha,desde,hasta,vencimiento,sesiones,precio_sesion,condicion_iva,observaciones,nota`. The last two are optional. Save UTF-8. Each row represents a separate invoice. `condicion_iva=5` means final consumer, not five sessions. An empty DNI is allowed; do not invent one. Use ISO dates, positive integer unit counts, and positive prices in pesos with at most two decimal places and no thousands separator. Compute totals with Decimal as quantity multiplied by unit price.

When transcribing an image, check the written month rather than replacing it with an accidentally mentioned month. Preserve names the user has confirmed. Ambiguous additional sessions or prices need clarification; do not infer an extra charge from shorthand alone. Apply explicit corrections to observations as well. Disclose any reused template dates and leave illegible names pending confirmation. Create a separate file for new patients without modifying the previous batch. Preparing a CSV does not authorize issuance.

## Issuance and persistence

`app.py` uploads and previews; `core.py` validates, authenticates, issues, and records. Testing (`homologacion`) and production (`produccion`) have separate databases, WSAA tickets, and locks. The local key is `(scope,id)`; scope includes environment, CUIT, and point of sale. Do not change IDs or delete records to bypass duplicate controls. A pending record blocks the batch: query ARCA and reconcile the result before retrying. An authorized record retains its payload, invoice number, and CAE. Locks coordinate this installation only.

Preparing a CSV, editing code, or regenerating a PDF does not authorize real issuance. Issue only when the user explicitly requests it and the interface confirmation controls are satisfied, including `EMITIR REAL` for production. The core API also requires explicit production confirmation; do not bypass the user-authorized workflow. Editing a CSV does not alter an already authorized invoice; do not silently replace its saved payload.

## PDFs

Use `core.test_pdf`, which delegates to `generate_invoice_pdf.invoice_pdf`. Preserve the header, service period, recipient, session table, subtotal, total, bank alias/CBU, authorization, and production QR layout. Do not replace the invoice with a plain text listing. Regenerate from saved payload and response, opening SQLite in read-only mode. Do not call WSAA or WSFE to change presentation. Testing PDFs must keep their test watermark and must not include a production QR code.

## Public distributions and security

Copy an explicit allowlist of files. Exclude active configuration, certificates, private keys, WSAA tickets, SQLite databases, and real PDFs, ZIP archives, or CSV batches. `.gitignore` only prevents future additions; it does not clean tracked files or history. Replace hardcoded personal and bank details with configuration fields and fictional examples. Review files and run relevant checks before preparing publication. Preparing a distribution does not authorize publishing or pushing; an explicit user request to publish or push does.

Read `SECURITY.md` when reviewing security, launch behavior, credentials, or public distribution. Keep the app bound to localhost and preserve existing confirmation and persistence controls. The Bash launcher sets umask 077 for new files; existing file permissions and Windows ACLs need separate protection. Do not claim that ignore rules, local binding, or the test suite constitute a full security audit.

## Local validation and references

Run commands from the repository root with the project's virtual environment when available:

```bash
python -m unittest discover -s tests
python -m py_compile app.py core.py generate_invoice_pdf.py
```

For CSV changes, run `parse_csv` and verify row count and total. Validation must not issue invoices or connect to ARCA merely to check formatting. Read `docs/arquitectura.md` for components and persistence limits and `README.md` for setup and launch commands. If current tax rules are needed, verify official ARCA documentation; this skill describes the implementation and does not certify tax compliance. Preserve `LICENSE`, `NOTICE`, and existing third-party notices when distributing the project.

## Docker and guided service entry

Read `docs/docker.md` for deployment and `docs/saas.md` for hosted scope. Preserve ROOT as the code directory and DATA_ROOT (ARCA_DATA_DIR) as private storage. The wizard saves configuration through `setup_config.py`; manual entry and CSV share `parse_csv`. CSV names remain compatible: `sesiones` is quantity, `precio_sesion` is unit price, and `observaciones` is the service description. Services are not limited to psychology. Docker publishes locally; hosted Caddy adds HTTPS and a password for one professional, not multiuser isolation. Never delete a production volume or restore old records to bypass pending or duplicate controls.

## Business rules

Read `domain.py` and `docs/business-rules.md` before changing billing semantics. Preserve immutable entities and the domain/persistence acceptance tests across infrastructure changes. CSV names belong to adapters. Incomplete or contradictory ARCA replies stay pending, not rejected; only explicit rejection permits a reviewed retry. Do not change stable IDs or previously recorded payloads as a side effect of a technical migration.
