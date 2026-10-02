# Security / Seguridad

Review date: 2026-10-02. Local static review, adversarial regression tests, Docker checks, and a pip-audit scan of `requirements.lock`. No real ARCA issuance or independent penetration test was performed.

## Controls implemented

| Attack or exposure | Control |
|---|---|
| Forged browser action bypassing a disabled button | Emission checks configuration and confirmation again on the server. Production also requires explicit `production_confirmation="EMITIR REAL"` in `emit_batch`, before filesystem or network effects. This is an operator confirmation, not authentication. |
| Large or malicious CSV causing resource exhaustion | 5 MB input, 500 invoices per batch, 2000 characters per field, 500-character service descriptions; duplicate headers and undeclared cells rejected. CSV text starting with spreadsheet formula markers is rejected. |
| Cross-origin browser requests or accidental static publication | Streamlit CORS and XSRF protections explicitly enabled; static serving disabled; websocket messages capped at 8 MB. Hosted mode configures the public browser hostname. |
| Traversal, Windows absolute paths on Linux, or private-file symlinks | Shared path validation in configuration, credential loading, tickets and records. Private paths stay inside the data directory; supported certificate/key suffixes are checked. |
| Ticket leaks, permissive new files, or partial JSON writes | Configuration and tickets are atomically stored as private files. New SQLite and lock files use mode 600 on POSIX. Windows requires ACL protection separately. |
| Weak TLS compatibility applied silently | Normal verified TLS is the default. `ARCA_ALLOW_LEGACY_TLS=1` is an explicit opt-in, restricted to production ARCA endpoints. Proxy environment variables are not automatically inherited by SOAP sessions. |
| Malicious XML declarations or oversized authentication reply | Zeep forbids DTD, entity and external declarations. The WSAA reply is bounded and entity declarations rejected. |
| Application crashes revealing paths or secrets in the browser | Detailed Streamlit errors disabled; raw emission exceptions are not displayed. Authorized results still contain intended fiscal data and must remain private. |
| Container compromise and CPU/memory exhaustion | Non-root app, read-only code filesystem, dropped capabilities, no-new-privileges, limited memory, CPU and process count. Docker build uses a public-file allowlist; no private data enters the image. |
| Accidental public exposure, cached pages or clickjacking | Localhost-only app port. Hosted Caddy uses HTTPS/password authentication, request-body limits, HSTS, no-store, framing prevention and no-referrer headers. Caddy admin API disabled; Authorization header removed before forwarding. |
| Unreviewed dependency drift | Exact constraints in `requirements.lock`; Python and Caddy image digests pinned. pip-audit reported no known vulnerabilities in the locked Python packages on the review date. |
| Duplicate issuance after an uncertain response | Reservation persisted before sending; uncertain replies stay pending and block the batch. Authorized payloads cannot be replaced under the same scope/ID; only explicit rejection allows a reviewed retry. |

## Remaining risks and deployment limits

- A stolen hosted password gives the attacker the same configuration, invoice and download permissions as the professional. Basic authentication has no MFA, recovery, per-user roles or built-in login throttling. Production confirmation does not stop an authenticated attacker. Put a public installation behind a VPN or an identity gateway with MFA and rate limiting before offering it as a service.
- Each installation has one issuer and shared data. It is not a multiuser SaaS. The fiscal scope filters records but does not replace account authorization or tenant isolation.
- Keys, tickets and SQLite are not encrypted by the application. Restrict host/volume access, protect Windows ACLs and use encrypted backups. An attacker who controls the host or can alter the data directory is outside this isolation boundary.
- The request-body limit does not rate-limit login guesses or every websocket frame. Container limits reduce impact, not the possibility of denial of service.
- The dependency scan covers known Python advisories, not every OS package, unpublished vulnerability or malicious package release. Package artifact hashes and automated recurring scans remain pending. Digest/lock updates require review and retesting.
- Legacy TLS opt-in lowers cryptographic policy. Its necessity must be tested with ARCA before use; endpoint compatibility was not checked through real issuance.
- Local locks do not coordinate multiple servers or other invoicing applications. Do not run multiple emission replicas. Restoring old records requires reconciliation with ARCA.

## Privacy review

Tracked files and reachable historical file trees were checked for personal home-directory paths, private keys, access-token patterns and private binary artifacts. None were found in the checked contents. Historical commit author/committer identity was found and is being replaced with a project identity; local SSH configuration uses a home-relative path. This review does not inspect or delete actual professional credentials, production records or data outside the repository.

Changing public history replaces commit IDs. Existing forks, clones, pull-request references and cached pages can retain old information. See [GitHub's sensitive-data removal guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository). Do not promise total erasure across third-party copies.

## Reporting

Do not post credentials, tickets, names, DNI, invoices or databases in issues. Agree on a private channel with the maintainer before sending sensitive details; this repository has no designated private security email. Use fictional reproductions for public reports.

## Español

Se reforzaron controles de confirmación en el servidor, límites de archivos y lotes, validación de rutas y enlaces, permisos privados y escritura atómica, TLS por defecto, XML, errores visibles, recursos Docker y cabeceras del proxy. La auditoría de dependencias fijadas no encontró vulnerabilidades conocidas en la fecha indicada; no constituye una garantía completa.

El principal riesgo pendiente es el robo o ataque a la contraseña compartida: quien la obtiene puede configurar, emitir y descargar con los permisos del profesional. Esta versión no tiene MFA, límites de intentos ni aislamiento por cuentas. Para ofrecerla públicamente, usar VPN o una capa de identidad con MFA y protección contra intentos repetidos. Los secretos siguen sin cifrado de aplicación y los backups deben protegerse. No ejecutar varias réplicas de emisión ni restaurar registros antiguos sin conciliación.

La revisión de archivos e historial de contenidos no encontró rutas personales ni patrones de claves/tokens en lo versionado. Los autores del historial sí contenían identidad y se prepara su anonimización. Las credenciales y registros fiscales reales se conservan fuera de la distribución pública. La limpieza de GitHub requiere actualizar todas las referencias afectadas; no elimina copias de terceros ni garantiza que desaparezcan vistas antiguas de PRs.

References: [Streamlit configuration](https://docs.streamlit.io/develop/api-reference/configuration/config.toml), [Caddy request-body limits](https://caddyserver.com/docs/caddyfile/directives/request_body), [Caddy authentication](https://caddyserver.com/docs/caddyfile/directives/basic_auth).
