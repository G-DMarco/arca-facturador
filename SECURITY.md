# Seguridad / Security

Revisión estática local: 2026-10-02. No es una auditoría independiente ni un análisis de vulnerabilidades de todas las dependencias. No se hicieron llamadas de emisión a ARCA.

## Hallazgos y gaps

| Prioridad | Hallazgo y alcance | Mitigación / pendiente |
|---|---|---|
| Alta si se expone | No hay autenticación ni aislamiento multiusuario; la interfaz permite emitir y visualizar datos locales. | Uso local en 127.0.0.1; dentro de Docker se escucha en 0.0.0.0 con publicación solo en localhost. La variante hosted agrega contraseña y HTTPS en Caddy para un profesional, sin aislamiento multiusuario. No publicar el puerto ni abrir túneles. Un despliegue compartido necesita autenticación, autorización y aislamiento antes de usarse. |
| Alta en equipo compartido | Clave PEM sin contraseña, tokens WSAA y SQLite en texto claro; pueden incluir DNI, nombres y sesiones. | Bash aplica umask 077 a archivos nuevos. Restringir permisos/ACL de archivos existentes y backups; usar cifrado del disco. Falta soporte de claves cifradas y permisos reforzados desde Python cuando se arranca por otras vías. |
| Media | `core.soap_transport` reduce la seguridad criptográfica de OpenSSL a SECLEVEL=1 en producción. La validación del certificado sigue activa. | Revisar compatibilidad con ARCA y retirar o acotar el adaptador tras probar homologación y producción. No desactivar la validación TLS. |
| Media | `requirements.txt` usa rangos sin lock ni hashes; no hay escaneo automatizado de dependencias. | Pendiente fijar y verificar dependencias transitivas y automatizar un escaneo de vulnerabilidades. No se certifica aqué que las versiones instaladas están libres de CVE. |
| Media | El CSV y la generación de ZIP/PDF tienen un límite de carga de 5 MB en la interfaz y 500 caracteres de descripción, pero no un límite propio de cantidad de filas ni de otros campos; errores técnicos se muestran en la interfaz. | Usar lotes conocidos en equipo local; agregar límites y mensajes redactados antes de ampliar el acceso. |
| Media | El lock funciona en esta instalación; otras aplicaciones o equipos pueden competir por números. Conciliación manual de pendientes. | Un único emisor activo por punto de venta, backups y conciliación antes de reintentar. La confirmación de producción está en la interfaz, no en `emit_batch`. |
| Alta al publicar | `.gitignore` no limpia archivos ya versionados ni historial. | Se ampliaron exclusiones de configuraciones privadas y claves. Revisar contenido e historial antes de publicar; si se filtró una clave, revocarla/reemplazarla. |

Controles observados: endpoints HTTPS definidos en código; validación de CSV y cálculo Decimal; consultas SQL parametrizadas para datos variables; escape HTML de datos en la vista previa; homologación/producción separadas; reserva persistente antes de emitir y bloqueo de pendientes. Son controles parciales, no una garantía de seguridad completa.

## Reportar problemas

No publicar credenciales, tickets, DNI, pacientes, comprobantes ni bases en issues. Para fallos que puedan exponer datos o permitir emisión no autorizada, acordar un canal privado con el mantenedor antes de compartir detalles. No hay un correo privado designado en este repositorio. Usar ejemplos ficticios para reportes públicos y contribuciones.

## English

Local static review dated 2026-10-02. No independent audit, full dependency vulnerability scan, or invoice issuance was performed.

Remaining gaps: no authentication or multiuser isolation; unencrypted PEM keys, WSAA tokens and databases; production TLS compatibility adapter lowers OpenSSL to SECLEVEL=1 while keeping certificate verification; dependency ranges without a lock file, hashes or automated vulnerability scan; 5 MB UI uploads and 500-character descriptions, but no application-specific row limit or limits on other fields; technical errors visible in the UI; locks cover only this installation and pending invoices need manual reconciliation. Production confirmation exists in the UI, not in the core API.

Launchers bind to localhost. Bash restricts permissions of newly created files with umask 077; existing files and Windows ACLs require separate protection. Keep the app on a trusted local machine, protect backups, use disk encryption, start in testing, and reconcile uncertain results before retrying. A shared deployment requires authentication, authorization and isolation first.

Ignore rules now cover private config variants and additional key formats, but cannot remove tracked files or history. Review both before publication and revoke any exposed key. Observed controls include HTTPS endpoints, CSV validation, Decimal totals, parameterized SQL, HTML escaping, separated environments, persistent reservations and blocking pending records; these do not guarantee complete security.

Never post private records or credentials in issues. Agree on a private channel with the maintainer for sensitive reports; this repository currently provides no dedicated private email. Use fictional examples for public reports and contributions.

## Docker y acceso web

La imagen copia solo una lista de archivos públicos y corre sin root, con filesystem de código de solo lectura, capacidades eliminadas y volumen privado. El contenedor escucha en 0.0.0.0; Compose publica el puerto solo en localhost. El modo hosted usa Caddy para HTTPS y contraseña, sin MFA, recuperación ni límites de intentos. Todos los usuarios de una instalación comparten datos y permisos; no es una plataforma compartida. El volumen contiene secretos sin cifrado de aplicación: restringir acceso al host y cifrar backups. `.env.hosted` queda excluido de Git y de la imagen. No se deben crear varias réplicas de emisión sobre este SQLite.
