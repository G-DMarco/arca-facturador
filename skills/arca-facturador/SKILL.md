---
name: arca-facturador
description: Preparar y revisar CSV de sesiones, mantener el facturador local Streamlit de ARCA y regenerar sus PDFs desde comprobantes autorizados. Usar para este proyecto, sus lotes mensuales y su versión pública sin credenciales.
---

# Facturador ARCA

Identificar primero la carpeta de trabajo: la instalación privada contiene configuración y registros reales; la distribución pública contiene ejemplos ficticios. No trasladar credenciales ni pacientes entre ambas.

## CSV de sesiones

Leer el encabezado del modelo existente y `core.parse_csv`. Las columnas son `id,nombre,documento,fecha,desde,hasta,vencimiento,sesiones,precio_sesion,condicion_iva,observaciones,nota`; las últimas dos son opcionales. Guardar UTF-8. Cada fila representa una factura independiente. `condicion_iva=5` significa consumidor final, no cinco sesiones. DNI vacío está admitido; no inventarlo. Fechas ISO, sesiones enteras positivas y precios en pesos sin separador de miles. Calcular total con Decimal como sesiones por precio.

Al transcribir una foto, comprobar el mes escrito y no cambiarlo por un mes mencionado por error en conversación. Conservar los nombres del CSV cuando el usuario confirme que son correctos. Un apunte como `4 × 55 + 1` no permite decidir por sí solo cantidad y precio del adicional. Aplicar las correcciones explícitas del usuario y actualizar también observaciones. Si se reutilizan fechas del modelo, indicarlo; nombres ilegibles deben quedar pendientes de confirmación. Generar un archivo separado para pacientes nuevos, sin modificar el lote anterior ni emitir por el mero pedido de un CSV.

## Emisión y persistencia

`app.py` carga y previsualiza; `core.py` valida, autentica, emite y registra. Entornos separados: homologación y producción, con sus propias bases, tickets y locks. La clave local es `(scope,id)` y scope incluye entorno, CUIT y punto de venta. No cambiar IDs ni borrar registros para evitar controles de duplicados. Un pendiente bloquea el lote: consultar y conciliar el resultado antes de reintentar. Un registro autorizado mantiene payload, número y CAE.

Preparar un CSV, corregir código o regenerar un PDF no autoriza una emisión real. Emitir solamente cuando el pedido lo incluya y se cumplan los controles de la interfaz. No modificar silenciosamente una factura ya autorizada: una corrección en su CSV no cambia el comprobante registrado.

## PDFs

La descarga debe usar `core.test_pdf`, que delega en `generate_invoice_pdf.invoice_pdf`. Mantener el diseño con encabezado, período, receptor, tabla de sesiones, subtotal, total, alias/CBU y autorización/QR. No sustituirlo por un listado de texto. Regenerar desde payload y respuesta guardados, abriendo SQLite en modo de solo lectura. No llamar a WSAA/WSFE para cambiar presentación. Homologación debe conservar su marca de prueba y no presentar un QR de producción.

## Distribución pública

Copiar por lista explícita de archivos. Excluir configuración activa, certificados, claves, tickets WSAA, SQLite, PDFs, ZIP y CSV reales; `.gitignore` solo evita adiciones futuras y no limpia historial. Sustituir datos personales y bancarios escritos en código por campos de configuración y ejemplos ficticios. Revisar los archivos y ejecutar pruebas antes de preparar la publicación. No publicar ni subir por el mero pedido de preparar una versión.

Validación local: `python -m unittest discover -s tests` y compilación de módulos modificados. Para CSV, ejecutar `parse_csv` y comprobar cantidad de filas y suma. Consultar `docs/arquitectura.md` dentro del proyecto para componentes y límites de persistencia. Si el pedido exige reglas fiscales actuales, verificar documentación oficial de ARCA; esta skill describe el código, no certifica cumplimiento fiscal.
