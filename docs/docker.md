# Empezar con Docker

## En tu computadora: Windows

1. Instalá [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) y abrilo. Su instalación puede requerir habilitar virtualización/WSL y reiniciar; pedí ayuda para esta primera configuración si hace falta.
2. Descargá el proyecto y descomprimilo en una carpeta. No necesitás instalar Python.
3. Hacé doble clic en **Iniciar Windows.cmd**. La primera vez descarga componentes y puede tardar varios minutos. Después abre el navegador.
4. En **Configuración**, completá tus datos y dejá seleccionado **Pruebas sin validez fiscal** para empezar.
5. En **Preparar facturas**, agregá clientes y servicios. No es obligatorio usar Excel o CSV.

La instalación inicial de Docker y la obtención del certificado ARCA pueden requerir asistencia. El uso diario se realiza desde el navegador.

## Linux, macOS o terminal

Con Docker y Compose instalados y funcionando, desde la carpeta del proyecto:

```bash
docker compose up -d --build
```

Abrí http://127.0.0.1:8501. También podés ejecutar `bash run_docker.sh`; en PowerShell, `./run_docker.ps1` inicia y abre el navegador. Para parar: `docker compose stop`. Para volver a abrir: `docker compose start` y visitá la misma dirección.

## Conectar ARCA

Guardá tus datos desde la pantalla. El programa crea `/data/config.json` dentro del volumen privado `arca_data`; no incorpora claves a la imagen. Para colocar los archivos propios (con el contenedor iniciado):

```bash
docker compose cp certificados/emisor.crt facturador:/data/certificados/emisor.crt
docker compose cp certificados/emisor.key facturador:/data/certificados/emisor.key
docker compose exec --user root facturador chown 10001:10001 /data/certificados/emisor.crt /data/certificados/emisor.key
docker compose exec --user root facturador chmod 600 /data/certificados/emisor.crt /data/certificados/emisor.key
```

El paso temporal como root solo ajusta permisos de esos archivos; la aplicación corre como usuario sin privilegios. La clave PEM debe estar sin contraseña en esta versión. Pedí a tu contador ayuda para obtener y autorizar certificado, servicio y punto de venta en el entorno adecuado. Estos comandos no solicitan autorización ni emiten facturas.

Si ya tenés una instalación privada, detené la emisión y migrá **también** sus bases SQLite, tickets y registros, conservando entorno, CUIT, punto de venta e IDs. No migres solamente el CSV o la configuración: perder el historial puede permitir duplicados. La ruta de certificados de la interfaz es relativa a `/data` (en uso local sin Docker, relativa al proyecto). La configuración externa `ARCA_DATA_DIR` permite elegir otra carpeta de datos fuera de Docker.

## Datos y copias de seguridad

La imagen lleva código y ejemplos; el volumen lleva configuración, claves, tickets, locks y registros. Reiniciar o recrear el contenedor conserva el volumen. **No uses `docker compose down -v`: elimina los registros y credenciales.**

Para una copia consistente, detené primero la aplicación y copiá la carpeta completa. Creá previamente la carpeta `backups` (desde el explorador, `mkdir -p backups` en Bash o `New-Item -ItemType Directory -Force backups` en PowerShell):

```bash
docker compose stop
docker compose cp facturador:/data ./backups/copia-privada
docker compose start
```

Cada copia debe tener una carpeta nueva para no mezclar snapshots. Cifrá y restringí las copias: contienen claves y datos de clientes. Para restaurar, primero detené las emisiones y conservá una copia del estado actual; un responsable técnico debe restaurar todo el snapshot en el volumen con UID/GID 10001 y conciliar con ARCA cualquier emisión posterior al snapshot. Una restauración incompleta o antigua puede duplicar facturas.

## Servicio privado por profesional

Para que un profesional entre desde un enlace web, se incluye `compose.hosted.yaml` con Caddy, HTTPS y contraseña. Es una **instalación privada por profesional**, con un solo emisor y volumen por despliegue. Quien opera el servidor debe configurar dominio, DNS, firewall, contraseñas y backups; el profesional usa el navegador.

1. En un servidor con Docker, apuntá un dominio al servidor y habilitá los puertos 80 y 443. El puerto 8501 queda publicado solo en localhost.
2. Copiá `.env.hosted.example` a `.env.hosted`. Completá un dominio real y un nombre de usuario.
3. Generá el hash de la contraseña de acceso sin incluir la contraseña en la línea de comandos:

```bash
docker run --rm -it caddy:2 caddy hash-password
```

Pegá el hash en `ARCA_PASSWORD_HASH` dentro de `.env.hosted`, **entre comillas simples** para conservar los signos `$`. No uses el marcador de ejemplo. Protegé este archivo.

4. Validá y levantá el servicio:

```bash
docker compose --env-file .env.hosted -f compose.yaml -f compose.hosted.yaml config --quiet
docker compose --env-file .env.hosted -f compose.yaml -f compose.hosted.yaml up -d --build
```

Entrá en `https://tu-dominio` con el usuario y contraseña configurados. Caddy obtiene certificados HTTPS cuando el dominio y los puertos son accesibles. No compartas esta cuenta entre profesionales: todos los accesos de esta instalación ven la misma configuración e historial. El HTTPS de Caddy protege el acceso web; el certificado ARCA es otro archivo con otra función.

Esta opción todavía no tiene MFA, recuperación de cuentas, limitación de intentos ni gestión de suscripciones. No debe presentarse como SaaS multiusuario terminado. Ver [plan de servicio](saas.md) y [seguridad](../SECURITY.md). Configurá monitoreo, protección contra intentos repetidos y copias cifradas antes de operar un servicio público. El acceso local directo en el servidor supone que sus usuarios son de confianza.

Referencias: [Compose](https://docs.docker.com/compose/gettingstarted/), [autenticación Caddy](https://caddyserver.com/docs/caddyfile/directives/basic_auth) y [proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).

## English

Run `docker compose up -d --build` and open http://127.0.0.1:8501. On Windows, double-click `Iniciar Windows.cmd` after starting Docker Desktop. Configure issuer details in the browser, start in testing, and add any supported service using the manual form or a compatible CSV.

Code and fictional examples go into the image; configuration, certificates, tickets and SQLite records remain in the persistent `/data` volume. The application runs as UID/GID 10001 with a read-only root filesystem. Add your own ARCA certificate and key using the commands above; protect their permissions. Back up the full data directory while stopped. Never delete the volume or restore old records without reconciling with ARCA.

For one privately hosted professional installation, configure `.env.hosted` and run the two Compose files together. Caddy adds HTTPS and password protection. This is not a shared SaaS: each professional needs a separate deployment, volume, credentials and domain/route. Initial hosting and ARCA setup require technical assistance; daily use happens in the browser. Shared accounts, MFA, recovery, rate limiting and subscriptions are not implemented.
