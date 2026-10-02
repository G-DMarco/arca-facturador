# SPDX-License-Identifier: Apache-2.0
import io
import json
import re
import sqlite3
import zipfile
from decimal import Decimal
from html import escape

import pandas as pd
import streamlit as st

from core import ROOT, emit_batch, environment, get_points_of_sale, parse_csv, test_pdf


CONFIG_PATH = ROOT / "config.json"
SAMPLE_PATH = ROOT / "facturas_ejemplo.csv"
MINIMAL_PRODUCTION_PATH = ROOT / "lote_minimo_local.csv"
FINAL_BATCH_PATH = ROOT / "lote_definitivo_local.csv"


def money(value):
    return f"$ {Decimal(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def filename_part(value):
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
    return cleaned.strip("_") or "sin_nombre"


def invoice_preview_html(row, config):
    point = f"{int(config['punto_venta']):05d}" if config else "00000"
    doc_label = f"DNI {escape(row['documento'])}" if row["documento"] else "Doc. (otro) 0"
    description = f"{escape(row['sesiones'])} sesion(es) de atencion psicologica - {escape(row['nombre'])}"
    return f"""
    <div style="border:1px solid #222; background:white; color:#111; font-family:Arial, sans-serif; max-width:900px;">
      <div style="display:grid; grid-template-columns: 1fr 86px 1fr; border-bottom:1px solid #222;">
        <div style="padding:14px 16px;">
          <div style="font-weight:700; font-size:15px;">Profesional: {escape((config or {}).get('nombre_emisor', 'Emisor sin configurar'))}</div>
          <div style="font-weight:700; font-size:13px; margin-top:4px;">{escape((config or {}).get('profesion', ''))}</div>
          <div style="font-size:12px; margin-top:4px;">Matrícula: {escape(str((config or {}).get('matricula', '')))}</div>
          <div style="font-size:11px; margin-top:8px;">Condicion frente al IVA: Monotributo</div>
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
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, f"No se pudo leer config.json: {exc}"


def setup_status(config, config_error):
    cert_path = ROOT / config.get("certificado", "") if config else ROOT / "certificados" / "emisor.crt"
    key_path = ROOT / config.get("clave_privada", "") if config else ROOT / "certificados" / "emisor.key"
    checks = [
        ("config.json", CONFIG_PATH.exists() and not config_error),
        (str(config.get("certificado", "certificado")) if config else "certificado", cert_path.exists()),
        (str(config.get("clave_privada", "clave privada")) if config else "clave privada", key_path.exists()),
        ("facturas_ejemplo.csv", SAMPLE_PATH.exists()),
    ]

    st.sidebar.header("Estado")
    for label, ok in checks:
        st.sidebar.write(("OK " if ok else "Falta ") + label)

    st.sidebar.divider()
    if config:
        st.sidebar.caption(f"Entorno ARCA: {config.get('entorno', 'homologacion')}")
    return all(ok for _, ok in checks)


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
    db_names = ("produccion.sqlite3",) if production_only else ("produccion.sqlite3", "homologacion.sqlite3")
    for db_name in db_names:
        db_path = ROOT / db_name
        if not db_path.exists() or db_path.stat().st_size == 0:
            continue
        db = sqlite3.connect(db_path)
        try:
            tables = db.execute("select name from sqlite_master").fetchall()
            if ("facturas",) not in tables:
                continue
            rows = db.execute("select scope,id,payload,numero,estado,respuesta from facturas").fetchall()
        finally:
            db.close()
        for scope, invoice_id, payload, number, state, response in rows:
            data = json.loads(payload)
            reply = json.loads(response) if response else {}
            parts = scope.split(":")
            env_label = "produccion" if parts[0] == "prod" else "homologacion"
            point = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
            detail = ((reply.get("FeDetResp") or {}).get("FECAEDetResponse") or [{}])[0]
            total = Decimal(data["total"])
            records.append(
                {
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


st.set_page_config(page_title="Facturador ARCA", layout="wide")

config, config_error = load_config()
ready = setup_status(config, config_error)
try:
    env_name, env = environment(config or {"entorno": "homologacion"})
except Exception as exc:
    env_name, env = "homologacion", {}
    ready = False
    config_error = str(exc)

st.title("Facturador ARCA")
st.caption("CSV -> revision -> emision -> descarga")

if config_error:
    st.warning(config_error)
    st.code("Copy-Item config.example.json config.json", language="powershell")

if env_name == "produccion":
    st.error("MODO PRODUCCION: los comprobantes autorizados tienen validez fiscal.")
else:
    st.info("Esta interfaz trabaja en homologacion. Los comprobantes generados no tienen validez fiscal.")

with st.sidebar.expander("Diagnostico ARCA"):
    if st.button("Consultar puntos de venta", disabled=not ready, use_container_width=True):
        try:
            st.session_state["ptos_venta"] = get_points_of_sale(config)
        except Exception as exc:
            st.error(f"{type(exc).__name__}: {exc}")
    if "ptos_venta" in st.session_state:
        st.json(st.session_state["ptos_venta"])

upload_tab, results_tab, management_tab = st.tabs(["Preparar lote", "Resultados", "Gestion mensual"])

with upload_tab:
    left, right = st.columns([2, 1])

    with left:
        uploaded_test = st.file_uploader("Cargar CSV de prueba", type=["csv"], key="test_csv")
        uploaded_final = st.file_uploader(
            "Cargar CSV definitivo para crear facturas",
            type=["csv"],
            key="final_csv",
        )

    with right:
        if MINIMAL_PRODUCTION_PATH.exists():
            st.download_button(
                "Descargar lote mínimo local",
                MINIMAL_PRODUCTION_PATH.read_bytes(),
                "lote_minimo_local.csv",
                "text/csv",
                use_container_width=True,
            )
        if FINAL_BATCH_PATH.exists():
            st.download_button(
                "Descargar lote definitivo",
                FINAL_BATCH_PATH.read_bytes(),
                "lote_definitivo_local.csv",
                "text/csv",
                use_container_width=True,
            )
        if SAMPLE_PATH.exists():
            st.download_button(
                "Descargar ejemplo",
                SAMPLE_PATH.read_bytes(),
                "facturas_ejemplo.csv",
                "text/csv",
                use_container_width=True,
            )

    uploaded = uploaded_final or uploaded_test
    upload_mode = "definitivo" if uploaded_final else "prueba"

    if uploaded:
        try:
            rows = parse_csv(uploaded.getvalue())
        except Exception as exc:
            st.error(str(exc))
            st.stop()

        total = sum(Decimal(row["total"]) for row in rows)
        patients = len({row["documento"] or row["nombre"] for row in rows})

        metric_cols = st.columns(3)
        metric_cols[0].metric("Facturas", len(rows))
        metric_cols[1].metric("Pacientes", patients)
        metric_cols[2].metric("Total lote", money(total))

        st.subheader("Vista previa")
        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
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

        st.subheader("Preview de factura")
        preview_options = {
            f"{row['id']} - {row['nombre']} - {money(row['total'])}": row
            for row in rows
        }
        selected_preview = st.selectbox("Factura a previsualizar", list(preview_options.keys()))
        st.markdown(invoice_preview_html(preview_options[selected_preview], config), unsafe_allow_html=True)

        st.subheader(f"Crear facturas en {env_name}")
        if not ready:
            st.error("Completa la configuracion antes de emitir.")

        if upload_mode == "definitivo":
            level = st.error if env_name == "produccion" else st.warning
            level(f"Lote definitivo cargado: se crearan {len(rows)} factura(s) individuales en {env_name} por {money(total)}.")
        else:
            st.warning(
                f"Se crearan {len(rows)} factura(s) individuales en {env_name} por un total de {money(total)}."
            )
        with st.expander("Confirmacion de creacion", expanded=True):
            st.write(f"Tipo de carga: {upload_mode}")
            st.write("Cada fila del CSV se emite como una factura separada.")
            st.write(f"Periodo: {rows[0]['desde']} a {rows[0]['hasta']}")
            st.write(f"Fecha de factura: {rows[0]['fecha']}")
            st.write(f"Primer paciente: {rows[0]['nombre']}")
            st.write(f"Total a emitir: {money(total)}")
            if config:
                st.write(f"Punto de venta: {int(config['punto_venta']):05d}")

        confirmed = st.checkbox(
            f"Confirmo crear {len(rows)} factura(s) del lote {upload_mode} en ARCA {env_name}"
        )
        production_text_ok = True
        if env_name == "produccion":
            typed = st.text_input("Para produccion escribi EMITIR REAL")
            production_text_ok = typed.strip().upper() == "EMITIR REAL"
        emit = st.button(
            "Crear factura(s) del lote definitivo" if upload_mode == "definitivo" else "Crear factura(s) de prueba",
            type="primary",
            disabled=not (ready and confirmed and production_text_ok),
            use_container_width=True,
        )

        if emit:
            try:
                with st.spinner(f"Solicitando autorizaciones a ARCA {env_name}..."):
                    results = emit_batch(rows, config)
                st.session_state["batch"] = (rows, results, config)
                st.success("Creacion finalizada. Revisa la pestana Resultados.")
            except Exception as exc:
                st.error(f"{type(exc).__name__}: {exc}")
                st.warning(
                    "Si hubo un fallo de conexion durante el envio, no cambies los ID. "
                    "Primero hay que consultar y conciliar el resultado."
                )
    else:
        st.write("Carga un CSV para validar importes, fechas, DNI e IDs duplicados.")

with results_tab:
    if "batch" not in st.session_state:
        st.write("Todavia no hay resultados en esta sesion.")
    else:
        rows, results, config = st.session_state["batch"]
        accepted = sum(1 for result in results if result["estado"] == "autorizada")
        rejected = sum(1 for result in results if result["estado"] == "rechazada")

        metric_cols = st.columns(3)
        metric_cols[0].metric("Procesadas", len(results))
        metric_cols[1].metric("Autorizadas", accepted)
        metric_cols[2].metric("Rechazadas", rejected)

        st.dataframe(results, use_container_width=True, hide_index=True)
        st.download_button(
            "Descargar resultados y PDFs individuales",
            build_download(rows, results, config),
            f"resultados_{config.get('entorno', 'homologacion')}.zip",
            "application/zip",
            use_container_width=True,
        )

        with st.expander("Respuesta tecnica"):
            st.json(results)

with management_tab:
    st.subheader("Gestion mensual de produccion")
    records = load_invoice_records(production_only=True)
    if records.empty:
        st.write("Todavia no hay facturas de produccion registradas para visualizar.")
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
        st.dataframe(detail, use_container_width=True, hide_index=True)
