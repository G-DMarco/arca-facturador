# Facturador ARCA

[Español](#descripción-y-origen) · [English](#english)

## Descripción y origen

Este proyecto nació de una sesión de **vibe coding**, después del cansancio de tener que generar las facturas una por una. Se comparte como software abierto para que otras personas puedan utilizarlo, estudiarlo, adaptarlo y mejorarlo con conciencia: revisar los datos, proteger la información privada y comprender qué se va a emitir antes de confirmar.

La comunidad está invitada a aportar mejoras, pruebas y documentación. Al abrir issues o pull requests, utilizar exclusivamente datos ficticios. Las contribuciones intencionalmente enviadas para incorporar al proyecto se reciben bajo Apache-2.0, salvo declaración explícita en contrario.


Aplicación local Python y Streamlit para cargar servicios en pantalla o importar un CSV, revisar el lote, solicitar autorización en WSFEv1 y descargar PDFs con CAE y QR. Incluye homologación y producción con persistencia separada. Alcance actual: factura C, servicios en pesos y consumidor final, con DNI opcional.

Esta distribución contiene solo código y datos ficticios. No contiene configuración activa, claves, certificados, tickets, pacientes ni facturas reales. No reutilizar el historial de una instalación privada para publicar este proyecto.

## Empezar con Docker (recomendado para uso guiado)

Con Docker Desktop abierto, hacé doble clic en **Iniciar Windows.cmd**. También podés ejecutar:

```bash
docker compose up -d --build
```

Abrí http://127.0.0.1:8501. La pantalla te guía por **Configuración → Preparar facturas → Descargar**. Podés cargar servicios directamente, sin CSV; la descripción es libre y no se limita a sesiones. Incluye botones grandes, ejemplos y un historial desde el que volver a descargar PDFs. Guardá tu lista como CSV para conservar los identificadores.

[Guía de instalación, certificados y backups](docs/docker.md). Para un servicio web privado hay una configuración con HTTPS y contraseña: [servicio por profesional y evolución a SaaS](docs/saas.md). La variante compartida con cuentas independientes aún requiere desarrollo.

## Instalación en Windows

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item config.example.json config.json
New-Item -ItemType Directory -Force certificados
```

Completar `config.json` con los datos del emisor y las rutas del certificado y clave autorizados para el entorno correspondiente. El CUIT de ejemplo es un marcador y debe reemplazarse. La clave PEM debe estar sin contraseña para esta versión. Los datos profesionales, domicilio, matrícula, alias y CBU son configurables. Conservar estos archivos fuera del control de versiones.

```powershell
.venv\Scripts\python -m streamlit run app.py --server.address 127.0.0.1
```

Comenzar por homologación. Producción utiliza `config.produccion.example.json` como plantilla y requiere el certificado, autorización y punto de venta correspondientes. La interfaz mantiene la confirmación de emisión real. Revisar datos fiscales y presentación antes de usar producción.

## Instalación en Linux / macOS / WSL (Bash)

Requiere Python 3.10 o posterior con `venv` y Bash. En WSL, instalar Python dentro de Linux y crear allí el entorno; no reutilizar el entorno de Windows.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
(umask 077; cp -n config.example.json config.json; mkdir -p certificados)
# Completar config.json e instalar el certificado y la clave propios.
chmod 700 certificados
chmod 600 config.json certificados/*  # después de colocar los archivos
bash run_local.sh
```

`run_local.sh` utiliza `.venv`, funciona desde cualquier directorio y aplica `umask 077` a los archivos nuevos. También admite Git Bash con `.venv/Scripts/python.exe`. No instala paquetes ni crea o sobrescribe configuraciones. Abre http://127.0.0.1:8501 y detén el servidor con Ctrl+C. En Windows puedes usar `./run_local.ps1` después de instalar las dependencias; restringe los archivos privados con los permisos de Windows (ACL).

## Servicios y CSV compatible

Usar `facturas_ejemplo.csv`, que contiene un cliente ficticio. Actualizar fechas antes de probar. Cada fila es una factura independiente; `total` se calcula como sesiones por precio y no es una columna de entrada.

| Columna | Contenido |
|---|---|
| id | Identificador único y estable de la obligación |
| nombre | Cliente/receptor |
| documento | DNI de 7 u 8 dígitos, o vacío |
| fecha, desde, hasta, vencimiento | YYYY-MM-DD |
| sesiones | Cantidad de unidades, entero positivo |
| condicion_iva | 5: consumidor final |
| observaciones, nota | Texto opcional |

Se admite CSV UTF-8 con coma o punto y coma. Para decimal con coma, encerrar el campo entre comillas. Los lotes se suben por la interfaz. Opcionalmente, `lote_minimo_local.csv` y `lote_definitivo_local.csv` habilitan accesos locales; quedan ignorados por Git.

## Registros y comprobantes

En Docker, la carpeta de datos es `/data` y se conserva en un volumen; fuera de Docker se usa la carpeta del proyecto, salvo que se configure `ARCA_DATA_DIR`. Cada entorno guarda su SQLite, lock y ticket WSAA. No borrar registros ni cambiar IDs para reenviar una emisión incierta. Un autorizado devuelve su resultado guardado y un pendiente bloquea el lote. La consulta del núcleo permite investigar; la conciliación requiere revisión manual.

Los PDFs usan una plantilla común con recuadros, período, receptor, sesiones, importes, transferencia y autorización. Homologación se identifica como prueba. La descripción y la transferencia se incorporan al PDF local, no como ítems enviados a WSFE.

## Desarrollo

```powershell
python -m unittest discover -s tests
python -m py_compile app.py core.py generate_invoice_pdf.py
```

[Diagrama y descripción de arquitectura](docs/arquitectura.md). La [skill arca-facturador](skills/arca-facturador/SKILL.md) documenta el flujo de CSV, emisión, PDFs y preparación de distribuciones sin datos privados.

Antes de publicar, revisar archivos e historial. `.gitignore` excluye configuración privada, credenciales, datos y comprobantes; no elimina archivos ya versionados. Esta carpeta se prepara para un repositorio nuevo, sin historial de producción.

## Seguridad

La [revisión de seguridad y gaps](SECURITY.md) describe hallazgos, controles y tareas pendientes. Esta herramienta está diseñada para una persona en un equipo local de confianza. Empieza en homologación, revisa cada lote y guarda copias de los registros antes de emitir en producción.

## Licencia

El código original y la documentación de este repositorio se distribuyen bajo **Apache License 2.0**: ver [LICENSE](LICENSE) y [NOTICE](NOTICE). Permite usar, modificar y redistribuir, incluso comercialmente, cumpliendo sus condiciones de atribución y distribución. El pedido de uso consciente es una invitación, no una restricción adicional de licencia. Las dependencias conservan sus propias licencias; al distribuir paquetes o ejecutables también debes conservar los avisos que correspondan. El software se ofrece sin garantías según la licencia. Proyecto independiente, sin afiliación ni respaldo de ARCA.

Referencia: [texto oficial Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0).

## English

### Description and origin

Facturador ARCA is a local Python and Streamlit application that accepts service descriptions, quantities, and unit prices through a guided form or CSV import, previews invoice batches, requests authorization through ARCA WSFEv1, and generates PDF invoices with CAE and production QR codes. It supports separate testing (homologación) and production records. Current scope: type C invoices, services in Argentine pesos, and final consumers, with optional DNI.

This project started as **vibe coding**, after getting tired of creating invoices one at a time. It is shared openly so the community can use, study, adapt, and improve it consciously: protect private information, review inputs, and understand the invoices before confirming issuance. Contributions, tests, and documentation are welcome. Use fictional data in issues and pull requests. Contributions intentionally submitted for inclusion default to Apache-2.0 unless explicitly stated otherwise.

### Docker and guided interface

Start Docker, run `docker compose up -d --build`, and open http://127.0.0.1:8501. On Windows you can double-click **Iniciar Windows.cmd**. The interface guides configuration, service entry, review, issuance, and downloads. CSV files remain compatible: `sesiones` now means quantity and `precio_sesion` means unit price. Service descriptions come from `observaciones` or the configured default.

See the [Docker guide](docs/docker.md) for certificates and persistent data. An optional Caddy deployment adds HTTPS and password protection for a private installation per professional. A shared SaaS with independent accounts is still future work: see the [service plan](docs/saas.md).

### Setup and launch

Requires Python 3.10+ and Bash for the shell launcher. On Linux, macOS, or WSL:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
(umask 077; cp -n config.example.json config.json; mkdir -p certificados)
# Fill in config.json and add your own certificate and private key.
chmod 700 certificados
chmod 600 config.json certificados/*  # after adding the files
bash run_local.sh
```

On Windows PowerShell:

```powershell
py -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
Copy-Item config.example.json config.json
New-Item -ItemType Directory -Force certificados
# Fill in config.json and add your own certificate and private key.
./run_local.ps1
```

Both launchers use the local virtual environment and bind to 127.0.0.1. Open http://127.0.0.1:8501; stop with Ctrl+C. Bash also supports Git Bash on Windows and sets `umask 077` for new files. Configure Windows ACLs separately. In WSL create a Linux virtual environment. Launchers do not install dependencies or overwrite configuration.

Replace the placeholder CUIT and configure your issuer details, point of sale, certificate, key, address, and bank details. This version requires an unencrypted PEM private key. Keep all private files outside version control. Start with `config.example.json` for testing. Use `config.produccion.example.json` as the production template, copied to `config.json`; production needs its own authorized certificate and point of sale. The UI requires explicit confirmation and `EMITIR REAL` for real issuance.

### CSV and records

Use `facturas_ejemplo.csv` with fictional data and update its dates. Required columns: `id,nombre,documento,fecha,desde,hasta,vencimiento,sesiones,precio_sesion,condicion_iva`; optional columns: `observaciones,nota`. Dates use YYYY-MM-DD; sessions are positive integers; prices are positive pesos with at most two decimal places and no thousands separator. `condicion_iva` must be 5 (final consumer). DNI may be empty or contain 7–8 digits. Each row creates a separate invoice; totals are calculated as sessions multiplied by price. Keep IDs stable and unique. UTF-8, comma or semicolon separators are supported.

Testing and production have separate SQLite databases, locks, and WSAA tickets. Never delete records or change IDs to retry an uncertain issuance. Pending records block further batches; query ARCA and reconcile manually first. Authorized records return their stored results. Local locks coordinate only this installation. PDFs and ZIP downloads are built locally; PDF changes do not require another issuance.

### Security, development, and license

Read [SECURITY.md](SECURITY.md) for the review and remaining gaps. This application is intended for a trusted local computer and a single operator. The public distribution uses fictional examples; review files and Git history before publishing, because `.gitignore` does not remove previously tracked data.

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m py_compile app.py core.py generate_invoice_pdf.py
```

See [architecture](docs/arquitectura.md) and the [project skill](skills/arca-facturador/SKILL.md) (English).

Original project code and documentation are licensed under **Apache License 2.0**; see [LICENSE](LICENSE), [NOTICE](NOTICE), and the [official terms](https://www.apache.org/licenses/LICENSE-2.0). Use, modification, redistribution, and commercial use are permitted subject to its terms. Conscious use is encouraged and adds no license restriction. Dependencies retain their own licenses and notices. The software is provided without warranties under the license. This independent project is not affiliated with or endorsed by ARCA.

## Skills para asistentes / Assistant skills

- **Codex (English):** [skills/arca-facturador/SKILL.md](skills/arca-facturador/SKILL.md). Copia la carpeta `arca-facturador` a tu directorio de skills de Codex para instalarla. / Copy the `arca-facturador` folder into your Codex skills directory to install it.
- **Claude Code (English):** [.claude/skills/arca-facturador/SKILL.md](.claude/skills/arca-facturador/SKILL.md). Skill del repositorio; usa `/arca-facturador` seguido de tu tarea. / Repository skill; invoke `/arca-facturador` followed by your task. See the [official Claude Code skill documentation](https://code.claude.com/docs/en/skills).

Ambas conservan los controles de privacidad, emisión y conciliación. Crear un CSV o regenerar un PDF no autoriza emitir facturas reales. / Both preserve privacy, issuance, and reconciliation controls. Creating a CSV or regenerating a PDF does not authorize real invoice issuance.

Los nombres técnicos del CSV se conservan por compatibilidad: `sesiones` es la cantidad de unidades y `precio_sesion` el importe por unidad. `observaciones` contiene la descripción del servicio; `descripcion_servicio` configura la descripción predeterminada. El alcance fiscal sigue siendo factura C para servicios en pesos y consumidor final.

## Entidades y reglas / Entities and rules

[Reglas de negocio](docs/business-rules.md) documenta las entidades inmutables de `domain.py`, independientes de la interfaz y la infraestructura. Los adaptadores de CSV y configuración las aplican, y la emisión conserva como pendiente cualquier respuesta incierta. / [Business rules](docs/business-rules.md) documents immutable entities independent of UI and infrastructure, with acceptance tests that protect totals, identity and issuance certainty across technical changes.
