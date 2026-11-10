from flask import Flask, render_template, request, send_file, abort
from werkzeug.exceptions import HTTPException
import requests
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from xml.sax.saxutils import escape
from io import BytesIO
import os

app = Flask(__name__)
# Debe coincidir con el nombre de la variable definida en docker-compose.yml
BACKEND_URL = os.getenv('BACKEND_API_URL', 'http://backend:8000')


def texto(valor):
    """Escapa caracteres especiales (&, <, >) y convierte saltos de línea
    en <br/>, porque Paragraph interpreta su contenido como mini-HTML."""
    return escape(str(valor)).replace('\n', '<br/>')


def moneda(valor):
    """Formatea un número como moneda: 1250.5 -> '1,250.50 €'."""
    return f"{valor:,.2f} €"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generar-pdf', methods=['POST'])
def generar_pdf():
    try:
        id_factura = request.form['id_factura'].strip()
        response = requests.get(f'{BACKEND_URL}/facturas/v1/{id_factura}', timeout=10)

        if response.status_code != 200:
            abort(404, description="Factura no encontrada")

        factura = response.json()

        # Crear buffer y doc para la creación del PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=20 * mm, rightMargin=20 * mm,
            topMargin=20 * mm, bottomMargin=20 * mm,
            title=f"Factura {factura['numero_factura']}",
        )
        styles = getSampleStyleSheet()
        normal = styles['Normal']
        elements = []

        # Adicionar el Título, ID
        elements.append(Paragraph("FACTURA", styles['Title']))
        elements.append(Paragraph(
            f"<b>Número:</b> {texto(factura['numero_factura'])}<br/>"
            f"<b>Fecha de emisión:</b> {texto(factura['fecha_emision'])}",
            normal,
        ))
        elements.append(Spacer(1, 8 * mm))

        # Agregar Información de la Empresa y del Cliente (lado a lado)
        empresa = factura['empresa']
        cliente = factura['cliente']

        bloque_empresa = Paragraph(
            f"<b>EMISOR</b><br/>"
            f"{texto(empresa['nombre'])}<br/>"
            f"{texto(empresa['direccion'])}<br/>"
            f"Tel: {texto(empresa['telefono'])}<br/>"
            f"{texto(empresa['email'])}",
            normal,
        )
        bloque_cliente = Paragraph(
            f"<b>CLIENTE</b><br/>"
            f"{texto(cliente['nombre'])}<br/>"
            f"{texto(cliente['direccion'])}<br/>"
            f"Tel: {texto(cliente['telefono'])}",
            normal,
        )
        partes = Table([[bloque_empresa, bloque_cliente]], colWidths=[85 * mm, 85 * mm])
        partes.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (0, 0), 0.5, colors.grey),
            ('BOX', (1, 0), (1, 0), 0.5, colors.grey),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(partes)
        elements.append(Spacer(1, 8 * mm))

        # Adicionar el Detalle: cantidad, descripción, precio unitario y total
        filas = [["Cant.", "Descripción", "Precio unit.", "Total"]]
        for item in factura['detalle']:
            filas.append([
                item['cantidad'],
                Paragraph(texto(item['descripcion']), normal),  # Paragraph = ajuste de línea
                moneda(item['precio_unitario']),
                moneda(item['total']),
            ])

        tabla_detalle = Table(filas, colWidths=[18 * mm, 92 * mm, 30 * mm, 30 * mm], repeatRows=1)
        tabla_detalle.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f2f2')]),
        ]))
        elements.append(tabla_detalle)
        elements.append(Spacer(1, 6 * mm))

        # Adicionar Subtotal, impuesto y Total
        tabla_totales = Table([
            ["Subtotal", moneda(factura['subtotal'])],
            ["IVA (21%)", moneda(factura['impuesto'])],
            ["TOTAL", moneda(factura['total'])],
        ], colWidths=[30 * mm, 30 * mm], hAlign='RIGHT')
        tabla_totales.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('LINEABOVE', (0, 2), (-1, 2), 1, colors.black),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 2), (-1, 2), 12),
        ]))
        elements.append(tabla_totales)

        # Generar el doc y limpiar el buffer
        doc.build(elements)
        buffer.seek(0)

        # Retornar a la página el PDF para visualizar y descargar
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=False,  # False = se abre en el navegador (desde ahí se puede descargar o imprimir)
            download_name=f"factura_{id_factura}.pdf",
        )

    except HTTPException:
        # Deja pasar los abort() (404, etc.) sin convertirlos en error 500
        raise
    except requests.exceptions.ConnectionError:
        abort(503, description="Error de conexión con el servidor")
    except Exception as e:
        abort(500, description=str(e))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
