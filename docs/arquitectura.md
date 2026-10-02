# Arquitectura del facturador

Aplicación local Python. Streamlit permite configurar al emisor, cargar servicios en pantalla o desde CSV, presenta la lista, pide confirmación de emisión y permite descargar comprobantes. El núcleo calcula importes con Decimal y coordina la autenticación y la persistencia.

```mermaid
flowchart TD
    U[Usuario en navegador local] --> UI[app.py · Streamlit]
    CSV[CSV mensual] --> UI
    CFG[config.json privado] --> UI
    UI --> VALID[core.parse_csv · validación y total]
    VALID --> PRE[Vista previa del lote]
    PRE --> CONF[Confirmación de emisión]
    CONF --> BATCH[core.emit_batch]
    BATCH --> LOCK[FileLock por entorno]
    BATCH <--> DB[(SQLite por entorno)]
    BATCH --> API[core.Arca · cliente SOAP]
    CERT[Certificado y clave privados] --> AUTH[Firma CMS · autenticación WSAA]
    API --> AUTH
    AUTH <--> TA[Ticket WSAA local por entorno]
    AUTH <--> WSAA[ARCA WSAA]
    API <--> WSFE[ARCA WSFEv1]
    WSFE --> RESP[Respuesta · CAE o rechazo]
    RESP --> DB
    RESP --> ZIP[build_download · ZIP]
    VALID --> ZIP
    ZIP --> PDF[core.test_pdf → invoice_pdf]
    PDF --> OUT[PDF con detalle, CAE y QR]
    ZIP --> JSON[Resultados JSON]
    DB --> MGMT[Gestión mensual]
    MGMT --> UI
```

## Estados del registro

```mermaid
stateDiagram-v2
    [*] --> pendiente: reservar número y guardar payload
    pendiente --> autorizada: respuesta con autorización
    pendiente --> rechazada: respuesta de rechazo
    pendiente --> pendiente: error o resultado incierto
    rechazada --> pendiente: reintento revisado con el mismo ID
    autorizada --> autorizada: devolver resultado guardado
```

Un pendiente existente impide continuar con nuevos lotes. La consulta `Arca.query` permite investigar el comprobante; no existe una interfaz completa de conciliación. El bloqueo coordina procesos en la instalación local, no otras aplicaciones ni equipos.

Homologación y producción usan endpoints, bases, locks y tickets separados. SQLite registra scope (entorno/CUIT/punto de venta), ID, payload, número, estado y respuesta. Los certificados y la configuración activa se obtienen fuera del repositorio. Los PDF y el ZIP se construyen localmente: cambiar su diseño no requiere una nueva emisión.

## Límites actuales

Factura C, servicios, pesos argentinos y consumidor final. La descripción y los datos de transferencia pertenecen al PDF local; WSFE recibe importes y campos fiscales, no esa descripción como detalle de ítems. El proyecto incluye despliegue Docker con volumen privado y una variante de acceso web con Caddy, HTTPS y contraseña para un único profesional. No incluye aislamiento multiusuario ni conciliación automática. Ver `docs/docker.md` y `docs/saas.md`. El diseño del PDF no equivale a una validación legal de sus datos fiscales.

## Datos persistentes

`ROOT` identifica el código; `DATA_ROOT` identifica los datos privados y toma `ARCA_DATA_DIR` (por defecto `ROOT`). Configuración, certificados relativos, tickets, locks y SQLite se leen o escriben en `DATA_ROOT`. Docker usa `/app` para código y `/data` para un volumen privado persistente. `setup_config.py` valida y guarda configuración de forma atómica. El historial abre SQLite en modo de solo lectura y filtra el scope del emisor configurado.

## Dominio

`domain.py` contiene entidades inmutables y reglas sin dependencias de infraestructura. `core.parse_csv` y `setup_config.py` adaptan entradas al dominio. `Authorization` distingue autorización, rechazo explícito y respuesta incierta; una respuesta incierta permanece pendiente. Ver `docs/business-rules.md`.
