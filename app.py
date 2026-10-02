# SPDX-License-Identifier: Apache-2.0
import io
import json
import re
import sqlite3
import zipfile
import csv
import uuid
import hashlib
from datetime import date
from decimal import Decimal
from html import escape

import pandas as pd
import streamlit as st

from core import DATA_ROOT, ROOT, emit_batch, environment, get_points_of_sale, parse_csv, test_pdf


CONFIG_PATH = DATA_ROOT / "config.json"
SAMPLE_PATH = ROOT / "facturas_ejemplo.csv"
MINIMAL_PRODUCTION_PATH = DATA_ROOT / "lote_minimo_local.csv"
FINAL_BATCH_PATH = DATA_ROOT / "lote_definitivo_local.csv"


def money(value):
    return f"$ {Decimal(str(value).replace(",", ".")):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def filename_part(value):
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
    return cleaned.strip("_") or "sin_nombre"


def invoice_preview_html(row, config):
    point = f"{int(config['punto_venta']):05d}" if config else "00000"
    doc_label = f"DNI {escape(row['documento'])}" if row["documento"] else "Doc. (otro) 0"
    description = escape(row.get("observaciones") or (config or {}).get("descripcion_servicio", "Prestación de servicios"))
    return f"""
    <div style="border:1px solid #222; background:white; color:#111; font-family:Arial, sans-serif; max-width:900px;">
      <div style="display:grid; grid-template-columns: 1fr 86px 1fr; border-bottom:1px solid #222;">
        <div style="padding:14px 16px;">
          <div style="font-weight:700; font-size:15px;">Profesional: {escape((config or {}).get('nombre_emisor', 'Emisor sin configurar'))}</div>
          <div style="font-weight:700; font-size:13px; margin-top:4px;">{escape((config or {}).get('profesion', ''))}</div>
          <div style="font-size:12px; margin-top:4px;">Matrícula: {escape(str((config or {}).get('matricula', '')))}</div>
          <div style="font-size:11px; margin-top:8px;">Condición frente al IVA: {escape((config or {}).get("condicion_emisor", "Monotributo"))}</div>
          <div style="font-size:11px;">Domicilio Comercial: {escape((config or {}).get('domicilio_comercial', ''))}</div>
          <div style="font-size:11px;">{escape((config or {}).get('localidad', ''))}</div>
        </div>
        <div style="border-left:1px solid #222; border-right:1px solid #222; text-align:center; padding-top:12px;">
          <div style="font-size:34px; font-weight:700;">C</div>
          <div style="font-size:11px; font-weight:700;">COD. 11</div>
        </div>
        <div style="padding:14px 16px;">
          <div style="font-size:24px; font-weight:700;">FACTURA</div>
          <div style="font-size:13px; margin-top:9px;">Punto de Venta: <b>{point}</b></div>
          <div style="font-size:13px;">Comp. Nro: <b>a asignar</b></div>
          <div style="font-size:13px;">Fecha de Emision: <b>{escape(row['fecha'])}</b></div>
          <div style="font-size:13px;">CUIT: <b>{escape(str((config or {}).get('cuit', '')))}</b></div>
        </div>
      </div>
      <div style="padding:10px 14px; border-bottom:1px solid #222; font-size:12px;">
        Periodo Facturado Desde: <b>{escape(row['desde'])}</b>
        &nbsp;&nbsp; Hasta: <b>{escape(row['hasta'])}</b>
        &nbsp;&nbsp; Fecha Vto. para el pago: <b>{escape(row['vencimiento'])}</b>
      </div>
      <div style="padding:10px 14px; border-bottom:1px solid #222; font-size:12px;">
        Apellido y Nombre / Razon Social: <b>{escape(row['nombre'])}</b><br/>
        Condicion frente al IVA: <b>Consumidor Final</b>
        &nbsp;&nbsp; Documento: <b>{doc_label}</b><br/>
        Condicion de venta: <b>Contado / Transferencia bancaria</b>
      </div>
      <table style="width:100%; border-collapse:collapse; font-size:12px;">
        <thead>
          <tr style="background:#eee;">
            <th style="text-align:left; padding:8px; border-bottom:1px solid #999;">Descripcion</th>
            <th style="text-align:right; padding:8px; border-bottom:1px solid #999;">Cantidad</th>
            <th style="text-align:right; padding:8px; border-bottom:1px solid #999;">Precio Unit.</th>
            <th style="text-align:right; padding:8px; border-bottom:1px solid #999;">Importe</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style="padding:10px 8px; height:70px; vertical-align:top;">{description}</td>
            <td style="padding:10px 8px; text-align:right; vertical-align:top;">{escape(row['sesiones'])}</td>
            <td style="padding:10px 8px; text-align:right; vertical-align:top;">{money(row['precio_sesion'])}</td>
            <td style="padding:10px 8px; text-align:right; vertical-align:top;">{money(row['total'])}</td>
          </tr>
        </tbody>
      </table>
      <div style="display:grid; grid-template-columns: 1.1fr .9fr; border-top:1px solid #222;">
        <div style="padding:12px 14px; border-right:1px solid #222;">
          <div style="font-weight:700; font-size:14px;">DATOS PARA TRANSFERENCIA</div>
          <div style="font-weight:700; font-size:16px; margin-top:8px;">Alias: {escape((config or {}).get('alias', ''))}</div>
          <div style="font-weight:700; font-size:15px; margin-top:5px;">CBU: {escape((config or {}).get('cbu', ''))}</div>
        </div>
        <div style="padding:12px 14px; text-align:right;">
          <div>Subtotal: <b>{money(row['total'])}</b></div>
          <div style="margin-top:6px;">Importe Otros Tributos: <b>$ 0,00</b></div>
          <div style="margin-top:10px; font-size:20px; font-weight:700;">Importe Total: {money(row['total'])}</div>
        </div>
      </div>
      <div style="padding:10px 14px; border-top:1px solid #222; font-size:12px;">
        <b>COMPROBANTE AUTORIZADO</b><br/>
        CAE y QR se completan automaticamente despues de la autorizacion de ARCA.
      </div>
    </div>
    """


def load_config():
    if not CONFIG_PATH.exists():
        return None, "Falta config.json. Copia config.example.json y revisa el punto de venta."
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("La configuración debe ser un objeto JSON")
        return data, None
    except Exception:
        return None, "No pudimos leer tu configuración. Revisá el archivo o volvé a guardar tus datos."


def setup_status(config, config_error):
    from setup_config import validate_config
    valid = False
    if config and not config_error:
        try:
            validate_config(config)
            valid = True
        except (ValueError, TypeError, KeyError):
            pass
    checks = [("Datos del profesional", valid)]
    for field, label in [("certificado", "Certificado ARCA"), ("clave_privada", "Clave privada")]:
        value = (config or {}).get(field, "")
        checks.append((label, valid and isinstance(value, str) and bool(value) and (DATA_ROOT / value).is_file()))
    st.sidebar.subheader("Tu configuración")
    for label, ok in checks:
        st.sidebar.write(("✓ " if ok else "○ ") + label)
    st.sidebar.caption("Completá lo que falta en Configuración. Podés preparar un lote antes de conectar ARCA.")
    return all(ok for _, ok in checks)


def csv_export(rows):
    fields = ["id", "nombre", "documento", "fecha", "desde", "hasta", "vencimiento", "sesiones", "precio_sesion", "condicion_iva", "observaciones", "nota"]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def configuration_screen(config):
    from setup_config import save_config
    current = config or {}
    st.subheader("Tus datos, una sola vez")
    st.write("Completá los datos que aparecerán en tus facturas. Guardar no emite comprobantes ni consulta ARCA.")
    with st.form("configuration"):
        name = st.text_input("Nombre o razón social", value=current.get("nombre_emisor", ""))
        cuit = st.text_input("CUIT (11 dígitos, sin guiones)", value=str(current.get("cuit", "")))
        point = st.number_input("Punto de venta", min_value=1, max_value=99999, value=1 if not str(current.get("punto_venta", 1)).isdigit() else max(1, min(99999, int(current.get("punto_venta", 1)))))
        mode = st.radio("¿Dónde querés trabajar?", ["Pruebas sin validez fiscal", "Producción: facturas reales"], index=1 if current.get("entorno") == "produccion" else 0)
        profession = st.text_input("Actividad o profesión", value=current.get("profesion", ""))
        service = st.text_input("Descripción habitual del servicio", value=current.get("descripcion_servicio", "Prestación de servicios"))
        address = st.text_input("Domicilio comercial", value=current.get("domicilio_comercial", ""))
        city = st.text_input("Localidad", value=current.get("localidad", ""))
        registration = st.text_input("Matrícula (si corresponde)", value=str(current.get("matricula", "")))
        alias = st.text_input("Alias bancario (opcional)", value=current.get("alias", ""))
        cbu = st.text_input("CBU (opcional)", value=current.get("cbu", ""))
        with st.expander("Conexión con ARCA: certificado y clave"):
            st.write("Estos archivos se obtienen en ARCA. Si aún no los tenés, pedí ayuda a tu contador. No los compartas en mensajes ni repositorios.")
            cert = st.text_input("Ruta del certificado", value=current.get("certificado", "certificados/emisor.crt"))
            key = st.text_input("Ruta de la clave privada", value=current.get("clave_privada", "certificados/emisor.key"))
        acknowledge = st.checkbox("Entiendo que Producción permite emitir facturas reales", value=False)
        submitted = st.form_submit_button("Guardar mis datos", type="primary")
    if submitted:
        if mode.startswith("Producción") and not acknowledge:
            st.error("Para activar Producción, confirmá que entendés su alcance.")
        else:
            updated = dict(current, nombre_emisor=name, cuit=cuit.strip(), punto_venta=int(point), entorno="produccion" if mode.startswith("Producción") else "homologacion", profesion=profession, descripcion_servicio=service, domicilio_comercial=address, localidad=city, matricula=registration, alias=alias, cbu=cbu, certificado=cert, clave_privada=key)
            try:
                save_config(updated)
                st.session_state.pop("batch", None)
                st.session_state["configuration_saved"] = True
                st.rerun()
            except (ValueError, TypeError, OSError) as exc:
                st.error(f"No se guardaron los datos: {exc}")
    if st.session_state.pop("configuration_saved", False):
        st.success("Tus datos están guardados. Ya podés preparar facturas.")
    st.caption("Los archivos privados quedan en la carpeta de datos de esta instalación. Consultá la guía de Docker para agregar el certificado y la clave.")


def build_download(rows, results, config):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "resultados.json",
            json.dumps(results, ensure_ascii=False, indent=2, default=str),
        )
        by_id = {row["id"]: row for row in rows}
        for result in results:
            if result["estado"] == "autorizada":
                row = by_id[result["id"]]
                invoice_number = f"{int(config['punto_venta']):05d}-{int(result['numero']):08d}"
                patient_name = filename_part(row["nombre"])
                archive.writestr(
                    f"{invoice_number}_{patient_name}.pdf",
                    test_pdf(row, result, config),
                )
    return buffer.getvalue()


def load_invoice_records(production_only=False):
    records = []
    if not config or not config.get("cuit") or not config.get("punto_venta"):
        return pd.DataFrame()
    db_names = ("produccion.sqlite3",) if production_only else ("produccion.sqlite3", "homologacion.sqlite3")
    for db_name in db_names:
        db_path = DATA_ROOT / db_name
        if not db_path.exists() or db_path.stat().st_size == 0:
            continue
        db = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)
        try:
            tables = db.execute("select name from sqlite_master").fetchall()
            if ("facturas",) not in tables:
                continue
            rows = db.execute("select scope,id,payload,numero,estado,respuesta from facturas").fetchall()
        finally:
            db.close()
        for scope, invoice_id, payload, number, state, response in rows:
            if config and scope != f"{'prod' if config.get('entorno') == 'produccion' else 'homo'}:{config['cuit']}:{config['punto_venta']}":
                continue
            data = json.loads(payload)
            reply = json.loads(response) if response else {}
            parts = scope.split(":")
            env_label = "produccion" if parts[0] == "prod" else "homologacion"
            point = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
            detail = ((reply.get("FeDetResp") or {}).get("FECAEDetResponse") or [{}])[0]
            total = Decimal(data["total"])
            records.append(
                {
                    "payload": data,
                    "result": {"id": invoice_id, "numero": number, "estado": state, "respuesta": reply},
                    "entorno": env_label,
                    "mes": data["fecha"][:7],
                    "fecha": data["fecha"],
                    "id": invoice_id,
                    "paciente": data["nombre"],
                    "comprobante": f"{point:05d}-{int(number):08d}",
                    "estado": state,
                    "cae": detail.get("CAE"),
                    "total": float(total),
                    "total_texto": money(total),
                }
            )
    return pd.DataFrame(records)


st.set_page_config(page_title="Mis facturas · ARCA", page_icon="🧾", layout="wide")
st.markdown("""<style>
.stApp { background: #f6f8fb; }
.block-container { max-width: 1150px; padding-top: 2rem; }
[data-testid="stWidgetLabel"] p, [data-testid="stMarkdownContainer"] p { font-size: 1.08rem; }
.stButton button, .stDownloadButton button { min-height: 3rem; font-size: 1.08rem; }
[data-testid="stMetric"] { background: white; border: 1px solid #d6dce5; border-radius: 12px; padding: 16px; }
button:focus-visible, input:focus-visible { outline: 3px solid #176b52 !important; }
</style>""", unsafe_allow_html=True)
config, config_error = load_config()
ready = setup_status(config, config_error)
try:
    env_name, env = environment(config or {"entorno": "homologacion"})
except (ValueError, TypeError) as exc:
    env_name, env = "homologacion", {}
    ready = False
    config_error = str(exc)
st.title("Tus facturas, paso a paso")
st.write("Cargá tus servicios, revisá los importes y descargá tus comprobantes.")
if env_name == "produccion":
    st.warning("FACTURAS REALES · Estás en Producción. Cada emisión autorizada tiene validez fiscal.")
else:
    st.info("MODO PRUEBA · Podés practicar. Los comprobantes no tienen validez fiscal.")
if not ready:
    st.info("Primer uso: abrí Configuración y completá tus datos. También podés explorar la carga de servicios.")
with st.sidebar.expander("Ayuda de conexión"):
    if st.button("Consultar puntos de venta", disabled=not ready, use_container_width=True):
        try:
            st.session_state["ptos_venta"] = get_points_of_sale(config)
        except Exception:
            st.error("No pudimos consultar ARCA. Revisá el certificado, la clave y tu conexión.")
    if "ptos_venta" in st.session_state:
        st.json(st.session_state["ptos_venta"])
setup_tab, upload_tab, results_tab, management_tab, help_tab = st.tabs(["1 · Configuración", "2 · Preparar facturas", "3 · Descargar", "Historial", "Ayuda"])
with setup_tab:
    configuration_screen(config)
with help_tab:
    st.subheader("Cómo usar el facturador")
    st.write("1. Guardá tus datos en Configuración y conectá tu certificado y clave de ARCA.")
    st.write("2. En Preparar facturas, agregá un cliente, describí el servicio e indicá la cantidad y el importe por unidad. También podés importar un CSV.")
    st.write("3. Revisá cada factura y el total. Confirmá la emisión cuando todo esté correcto.")
    st.write("4. En Descargar, guardá tus comprobantes. En Historial podés consultar lo registrado.")
    st.warning("Si se corta la conexión al emitir, no vuelvas a cargar la factura con otro identificador. Hay que consultar ARCA y conciliar el resultado antes de reintentar.")
    st.caption("Factura C · servicios en pesos · consumidor final. Los datos fiscales deben corresponder a tu situación. Si necesitás otro tipo de factura, consultá a tu contador.")
with upload_tab:
    st.subheader("Agregá los servicios que querés facturar")
    method = st.radio("¿Cómo preferís cargar?", ["Completar en pantalla", "Importar archivo CSV"], horizontal=True)
    uploaded = None
    rows = None
    upload_mode = "revisado"
    if method == "Completar en pantalla":
        with st.form("add_service", clear_on_submit=False):
            name = st.text_input("Nombre del cliente")
            doc = st.text_input("DNI (opcional)")
            description = st.text_area("Descripción del servicio", value=(config or {}).get("descripcion_servicio", "Prestación de servicios"), max_chars=500)
            left, right = st.columns(2)
            quantity = left.number_input("Cantidad", min_value=1, value=1, step=1)
            price = right.text_input("Importe por unidad, en pesos", placeholder="Ejemplo: 25000,50")
            first, second = st.columns(2)
            invoice_date = first.date_input("Fecha de la factura", value=date.today())
            due = second.date_input("Fecha de vencimiento del pago", value=date.today())
            first, second = st.columns(2)
            since = first.date_input("Servicio desde", value=date.today())
            until = second.date_input("Servicio hasta", value=date.today())
            reference = st.text_input("Identificador del servicio (opcional)", help="Si ya cargaste este servicio antes, usá su mismo identificador. Si lo dejás vacío se crea uno nuevo.")
            add = st.form_submit_button("Agregar a la lista para revisar", type="primary")
        if add:
            candidate = dict(id=reference.strip() or str(uuid.uuid4()), nombre=name.strip(), documento=doc.strip(), fecha=invoice_date.isoformat(), desde=since.isoformat(), hasta=until.isoformat(), vencimiento=due.isoformat(), sesiones=str(quantity), precio_sesion=price.strip(), condicion_iva="5", observaciones=description.strip(), nota="")
            try:
                pending = st.session_state.get("draft_rows", []) + [candidate]
                parse_csv(csv_export(pending))
                st.session_state["draft_rows"] = pending
                st.session_state.pop("batch", None)
                st.success("Servicio agregado. Revisá la lista debajo antes de emitir.")
            except (ValueError, UnicodeError) as exc:
                st.error(f"Revisá los datos: {exc}")
        if st.session_state.get("draft_rows"):
            rows = parse_csv(csv_export(st.session_state["draft_rows"]))
            st.download_button("Guardar esta lista como CSV", csv_export(rows), "servicios.csv", "text/csv")
            st.caption("Guardá el CSV para conservar los identificadores. Cargar el mismo servicio con un ID nuevo puede duplicar la factura.")
            remove = st.selectbox("Servicio a quitar de la lista", [r["id"] for r in rows], format_func=lambda value: next(r["nombre"] + " · " + value for r in rows if r["id"] == value))
            if st.button("Quitar el servicio seleccionado"):
                st.session_state["draft_rows"] = [r for r in st.session_state["draft_rows"] if r["id"] != remove]
                st.rerun()
    else:
        st.write("Cada fila del archivo será una factura. Se conserva el formato de los CSV anteriores.")
        uploaded = st.file_uploader("Elegí tu archivo CSV", type=["csv"], key="services_csv")
        if SAMPLE_PATH.exists():
            st.download_button("Descargar un ejemplo para completar", SAMPLE_PATH.read_bytes(), "facturas_ejemplo.csv", "text/csv")
    if uploaded:
        try:
            rows = parse_csv(uploaded.getvalue())
        except (ValueError, UnicodeError, IndexError) as exc:
            st.error(f"No pudimos leer el archivo. Revisá sus columnas y valores: {exc}")
    if rows:
        total = sum(Decimal(row["total"]) for row in rows)
        patients = len({row["documento"] or row["nombre"] for row in rows})

        metric_cols = st.columns(3)
        metric_cols[0].metric("Facturas", len(rows))
        metric_cols[1].metric("Clientes", patients)
        metric_cols[2].metric("Total lote", money(total))

        st.subheader("Revisá tu lista")
        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
            column_config={"nombre": "Cliente", "documento": "DNI", "sesiones": "Cantidad", "precio_sesion": "Importe por unidad", "observaciones": "Servicio", "total": "Total"},
            column_order=[
                "id",
                "nombre",
                "documento",
                "fecha",
                "desde",
                "hasta",
                "sesiones",
                "precio_sesion",
                "total",
                "observaciones",
            ],
        )

        st.subheader("Así se verá tu factura")
        preview_options = {
            f"{row['id']} - {row['nombre']} - {money(row['total'])}": row
            for row in rows
        }
        selected_preview = st.selectbox("Factura a previsualizar", list(preview_options.keys()))
        st.markdown(invoice_preview_html(preview_options[selected_preview], config), unsafe_allow_html=True)

        st.subheader("Último paso: confirmar la emisión")
        if not ready:
            st.error("Completa la configuracion antes de emitir.")

        st.warning(f"Vas a generar {len(rows)} factura(s) en {env_name} por un total de {money(total)}.")
        with st.expander("Resumen antes de emitir", expanded=True):
            st.write("Cada fila del CSV se emite como una factura separada.")
            st.write("Revisá las fechas y el período de cada fila en la lista.")
            st.write("Cada factura conserva su propia fecha.")
            st.write(f"Primer cliente: {rows[0]['nombre']}")
            st.write(f"Total a emitir: {money(total)}")
            if config:
                st.write(f"Punto de venta: {int(config['punto_venta']):05d}")

        review_key = hashlib.sha256(json.dumps({"rows": rows, "config": config}, sort_keys=True, default=str).encode()).hexdigest()
        confirmed = st.checkbox(
            f"Revisé los datos y confirmo crear {len(rows)} factura(s) en {env_name}", key=f"confirm_{review_key}"
        )
        production_text_ok = True
        if env_name == "produccion":
            typed = st.text_input("Para producción escribí EMITIR REAL", key=f"production_{review_key}")
            production_text_ok = typed.strip().upper() == "EMITIR REAL"
        emit = st.button(
            "Emitir facturas reales" if env_name == "produccion" else "Generar comprobantes de prueba",
            type="primary",
            disabled=not (ready and confirmed and production_text_ok),
            use_container_width=True,
        )

        if emit:
            try:
                with st.spinner(f"Solicitando autorizaciones a ARCA {env_name}..."):
                    results = emit_batch(rows, config)
                st.session_state["batch"] = (rows, results, config)
                accepted_ids = {item["id"] for item in results if item["estado"] == "autorizada"}
                st.session_state["draft_rows"] = [r for r in st.session_state.get("draft_rows", []) if r["id"] not in accepted_ids]
                st.success("Proceso finalizado. Abrí Descargar para guardar tus comprobantes.")
            except Exception as exc:
                st.error("No pudimos completar la emisión. Revisá el mensaje de ARCA antes de reintentar.")
                with st.expander("Detalle para soporte (no compartir datos privados)"):
                    st.code(str(exc))
                st.warning(
                    "Si hubo un fallo de conexion durante el envio, no cambies los ID. "
                    "Primero hay que consultar y conciliar el resultado."
                )
    else:
        st.write("Agregá un servicio o importá un archivo para comenzar. Todavía no se emitió ninguna factura.")

with results_tab:
    if "batch" not in st.session_state:
        st.write("Tus comprobantes aparecerán aquí después de emitir desde Preparar facturas.")
    else:
        rows, results, batch_config = st.session_state["batch"]
        accepted = sum(1 for result in results if result["estado"] == "autorizada")
        rejected = sum(1 for result in results if result["estado"] == "rechazada")

        metric_cols = st.columns(3)
        metric_cols[0].metric("Procesadas", len(results))
        metric_cols[1].metric("Autorizadas", accepted)
        metric_cols[2].metric("Rechazadas", rejected)

        st.dataframe(pd.DataFrame(results)[["id", "numero", "estado"]], use_container_width=True, hide_index=True)
        if rejected:
            st.warning("Hay facturas rechazadas. Revisá el detalle antes de corregir o reintentar.")
        st.download_button("Guardar CSV con los identificadores originales", csv_export(rows), "servicios_emitidos.csv", "text/csv")
        st.download_button(
            "Descargar resultados y PDFs individuales",
            build_download(rows, results, batch_config),
            f"resultados_{batch_config.get('entorno', 'homologacion')}.zip",
            "application/zip",
            use_container_width=True,
        )

        with st.expander("Respuesta tecnica"):
            st.json(results)

with management_tab:
    st.subheader("Tus facturas registradas")
    records = load_invoice_records(production_only=(env_name == "produccion"))
    if not records.empty:
        records = records[records["entorno"] == env_name]
    if records.empty:
        st.write("Todavía no hay facturas registradas en este modo.")
    else:
        filtered = records.copy()

        authorized = filtered[filtered["estado"] == "autorizada"].copy()
        monthly = (
            authorized.groupby("mes", as_index=False)
            .agg(ingresos=("total", "sum"), facturas=("id", "count"))
            .sort_values("mes")
        )
        rejected_by_month = (
            filtered[filtered["estado"] == "rechazada"]
            .groupby("mes", as_index=False)
            .agg(rechazadas=("id", "count"))
        )
        monthly = monthly.merge(rejected_by_month, on="mes", how="left").fillna({"rechazadas": 0})
        monthly["rechazadas"] = monthly["rechazadas"].astype(int)
        monthly["ingresos_texto"] = monthly["ingresos"].map(money)

        totals = st.columns(3)
        totals[0].metric("Ingreso autorizado", money(authorized["total"].sum() if not authorized.empty else 0))
        totals[1].metric("Facturas autorizadas", len(authorized))
        totals[2].metric("Rechazadas", len(filtered[filtered["estado"] == "rechazada"]))

        if monthly.empty:
            st.write("No hay facturas de produccion autorizadas.")
        else:
            chart_data = monthly.set_index("mes")[["ingresos"]]
            st.bar_chart(chart_data, use_container_width=True)
            st.dataframe(
                monthly[["mes", "facturas", "rechazadas", "ingresos_texto"]],
                use_container_width=True,
                hide_index=True,
            )

        st.subheader("Detalle de facturas")
        detail = filtered.sort_values(["fecha", "comprobante"])[
            ["fecha", "paciente", "comprobante", "estado", "cae", "total_texto"]
        ]
        st.dataframe(detail, use_container_width=True, hide_index=True, column_config={"paciente": "Cliente", "cae": "Autorización CAE", "total_texto": "Total"})
        if config and not authorized.empty:
            options = authorized.to_dict("records")
            selected = st.selectbox("Comprobante para volver a descargar", range(len(options)), format_func=lambda index: options[index]["comprobante"] + " · " + options[index]["paciente"])
            saved = options[selected]
            st.download_button("Descargar PDF guardado", test_pdf(saved["payload"], saved["result"], config), saved["comprobante"] + ".pdf", "application/pdf")
