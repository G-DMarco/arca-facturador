# SPDX-License-Identifier: Apache-2.0
import base64
import json
import io
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas



def pesos(value):
    amount = Decimal(str(value))
    return f"$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def draw_box(c, x, y, w, h, stroke=1):
    c.setLineWidth(stroke)
    c.rect(x, y, w, h)


def draw_text(c, x, y, text, size=9, bold=False):
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    c.drawString(x, y, text)


def draw_right(c, x, y, text, size=9, bold=False):
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    c.drawRightString(x, y, text)


def draw_qr(c, x, y, size, data):
    encoded = base64.b64encode(json.dumps(data, separators=(",", ":")).encode()).decode()
    url = "https://www.afip.gob.ar/fe/qr/?p=" + quote(encoded)
    qr = QrCodeWidget(url)
    bounds = qr.getBounds()
    drawing = Drawing(
        size,
        size,
        transform=[size / (bounds[2] - bounds[0]), 0, 0, size / (bounds[3] - bounds[1]), 0, 0],
    )
    drawing.add(qr)
    renderPDF.draw(drawing, c, x, y)


def invoice_pdf(invoice, result, config):
    detail = result["respuesta"]["FeDetResp"]["FECAEDetResponse"][0]

    pto_vta = result["respuesta"]["FeCabResp"]["PtoVta"]
    numero = detail["CbteDesde"]
    total = Decimal(invoice["total"])
    doc_tipo = 96 if invoice.get("documento") else 99
    doc_nro = int(invoice.get("documento") or 0)
    cae = detail["CAE"]
    cae_vto = detail["CAEFchVto"]

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    page_w, page_h = A4
    margin = 15 * mm
    x0 = margin
    y = page_h - margin
    width = page_w - 2 * margin

    production = config.get("entorno", "homologacion") == "produccion"
    draw_text(c, x0, y, "ORIGINAL" if production else "PRUEBA DE HOMOLOGACION - SIN VALIDEZ FISCAL", 9, True)
    y -= 9 * mm

    header_h = 42 * mm
    draw_box(c, x0, y - header_h, width, header_h)
    c.line(x0 + width * 0.45, y, x0 + width * 0.45, y - header_h)
    c.line(x0 + width * 0.55, y, x0 + width * 0.55, y - header_h)
    draw_box(c, x0 + width * 0.45, y - 14 * mm, width * 0.10, 14 * mm)

    draw_text(c, x0 + 4 * mm, y - 7 * mm, f"Profesional: {config['nombre_emisor']}", 9, True)
    draw_text(c, x0 + 4 * mm, y - 13 * mm, config.get('profesion', ''), 8, True)
    draw_text(c, x0 + 4 * mm, y - 19 * mm, f"Matrícula: {config.get('matricula', '')}", 7)
    draw_text(c, x0 + 4 * mm, y - 25 * mm, "Condicion frente al IVA: Monotributo", 7)
    draw_text(c, x0 + 4 * mm, y - 31 * mm, f"Domicilio Comercial: {config.get('domicilio_comercial', '')}", 6.5)
    draw_text(c, x0 + 4 * mm, y - 37 * mm, config.get('localidad', ''), 6.5)

    draw_text(c, x0 + width * 0.487, y - 9 * mm, "C", 20, True)
    draw_text(c, x0 + width * 0.478, y - 17 * mm, "COD. 11", 7, True)

    right_x = x0 + width * 0.58
    draw_text(c, right_x, y - 8 * mm, "FACTURA", 16, True)
    draw_text(c, right_x, y - 18 * mm, f"Punto de Venta: {pto_vta:05d}", 9)
    draw_text(c, right_x, y - 22 * mm, f"Comp. Nro: {numero:08d}", 9)
    draw_text(c, right_x, y - 26 * mm, f"Fecha de Emision: {invoice['fecha']}", 9)
    draw_text(c, right_x, y - 34 * mm, f"CUIT: {config['cuit']}", 9)
    draw_text(c, right_x, y - 40 * mm, "Ingresos Brutos: Exento / Monotributo", 8)
    y -= header_h + 6 * mm

    period_h = 13 * mm
    draw_box(c, x0, y - period_h, width, period_h)
    draw_text(c, x0 + 4 * mm, y - 5 * mm, f"Periodo Facturado Desde: {invoice['desde']}", 8)
    draw_text(c, x0 + 65 * mm, y - 5 * mm, f"Hasta: {invoice['hasta']}", 8)
    draw_text(c, x0 + 112 * mm, y - 5 * mm, f"Fecha Vto. para el pago: {invoice['vencimiento']}", 8)
    y -= period_h + 4 * mm

    rec_h = 23 * mm
    draw_box(c, x0, y - rec_h, width, rec_h)
    draw_text(c, x0 + 4 * mm, y - 6 * mm, f"Apellido y Nombre / Razon Social: {invoice['nombre']}", 8)
    draw_text(c, x0 + 4 * mm, y - 13 * mm, "Condicion frente al IVA: Consumidor Final", 8)
    draw_text(c, x0 + 100 * mm, y - 13 * mm, f"DNI: {doc_nro}" if doc_tipo == 96 else "Doc. (Otro): 0", 8)
    draw_text(c, x0 + 4 * mm, y - 20 * mm, "Condicion de venta: Contado / Transferencia bancaria", 8)
    y -= rec_h + 5 * mm

    table_h = 58 * mm
    draw_box(c, x0, y - table_h, width, table_h)
    header_y = y - 9 * mm
    c.setFillColor(colors.lightgrey)
    c.rect(x0, header_y, width, 9 * mm, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.line(x0, header_y, x0 + width, header_y)
    draw_text(c, x0 + 3 * mm, y - 6 * mm, "Descripcion", 8, True)
    draw_right(c, x0 + 120 * mm, y - 6 * mm, "Cantidad", 8, True)
    draw_right(c, x0 + 147 * mm, y - 6 * mm, "Precio Unit.", 8, True)
    draw_right(c, x0 + width - 3 * mm, y - 6 * mm, "Importe", 8, True)
    desc = invoice.get("observaciones") or config.get("descripcion_servicio", "Prestación de servicios")
    from html import escape
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle
    text_width, text_height = 100 * mm, 43 * mm
    font_size = 8
    while True:
        paragraph = Paragraph(escape(desc).replace("\n", "<br/>"), ParagraphStyle("service", fontName="Helvetica", fontSize=font_size, leading=font_size * 1.25))
        _, height = paragraph.wrap(text_width, text_height)
        if height <= text_height or font_size <= 4:
            break
        font_size -= 0.5
    if height > text_height:
        raise ValueError("La descripción es demasiado extensa para el PDF; revisá su longitud.")
    paragraph.drawOn(c, x0 + 3 * mm, header_y - 3 * mm - height)
    draw_right(c, x0 + 120 * mm, y - 18 * mm, invoice["sesiones"], 8)
    draw_right(c, x0 + 147 * mm, y - 18 * mm, pesos(invoice["precio_sesion"]), 8)
    draw_right(c, x0 + width - 3 * mm, y - 18 * mm, pesos(total), 8)
    y -= table_h + 4 * mm

    total_h = 34 * mm
    draw_box(c, x0, y - total_h, width * 0.52, total_h)
    draw_box(c, x0 + width * 0.55, y - total_h, width * 0.45, total_h)
    draw_right(c, x0 + width - 4 * mm, y - 8 * mm, f"Subtotal: {pesos(total)}", 9)
    draw_right(c, x0 + width - 4 * mm, y - 16 * mm, "Importe Otros Tributos: $ 0,00", 9)
    draw_right(c, x0 + width - 4 * mm, y - 24 * mm, f"Importe Total: {pesos(total)}", 11, True)
    draw_text(c, x0 + 4 * mm, y - 8 * mm, "DATOS PARA TRANSFERENCIA", 10, True)
    draw_text(c, x0 + 4 * mm, y - 17 * mm, f"Alias: {config['alias']}", 12, True)
    draw_text(c, x0 + 4 * mm, y - 26 * mm, f"CBU: {config.get('cbu', '')}", 11, True)
    y -= total_h + 7 * mm

    qr_data = {
        "ver": 1,
        "fecha": invoice["fecha"],
        "cuit": int(config['cuit']),
        "ptoVta": pto_vta,
        "tipoCmp": 11,
        "nroCmp": numero,
        "importe": float(total),
        "moneda": "PES",
        "ctz": 1,
        "tipoDocRec": doc_tipo,
        "nroDocRec": doc_nro,
        "tipoCodAut": "E",
        "codAut": int(cae),
    }
    auth_h = 46 * mm
    draw_box(c, x0, y - auth_h, width, auth_h)
    draw_text(c, x0 + 4 * mm, y - 8 * mm, "COMPROBANTE AUTORIZADO" if production else "COMPROBANTE DE PRUEBA", 12, True)
    draw_text(c, x0 + 4 * mm, y - 17 * mm, f"CAE Nro: {cae}", 11, True)
    draw_text(c, x0 + 4 * mm, y - 26 * mm, f"Fecha Vto. CAE: {cae_vto}", 10)
    draw_text(c, x0 + 4 * mm, y - 35 * mm, "Esta factura fue generada por sistema propio via ARCA WSFE.", 8)
    draw_text(c, x0 + 4 * mm, y - 41 * mm, "El QR permite constatar el comprobante autorizado.", 8)
    if production:
        draw_qr(c, x0 + width - 44 * mm, y - 43 * mm, 38 * mm, qr_data)

    c.showPage()
    c.save()
    return buffer.getvalue()
