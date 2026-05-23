"""
Servidor local para generar PDFs desde el cotizador.
USO: python3 cotizador_server.py
Luego abrí cotizador.html en el navegador.
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json, os, sys, tempfile, threading, webbrowser
from datetime import date, timedelta

# Copiar la logica del cotizador
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

VERDE_OSCURO  = colors.HexColor('#004225')
VERDE_MEDIO   = colors.HexColor('#2E7D32')
VERDE_CLARO   = colors.HexColor('#EAF3DE')
VERDE_BORDE   = colors.HexColor('#C0DD97')
GRIS_CLARO    = colors.HexColor('#F5F5F0')
GRIS_TEXTO    = colors.HexColor('#666666')
GRIS_LINEA    = colors.HexColor('#E0E0D8')
ROJO          = colors.HexColor('#791F1F')
AZUL          = colors.HexColor('#0C447C')
BLANCO        = colors.white
MESES_ES = {1:'enero',2:'febrero',3:'marzo',4:'abril',5:'mayo',6:'junio',
            7:'julio',8:'agosto',9:'septiembre',10:'octubre',11:'noviembre',12:'diciembre'}

def fmt_fecha(d):
    return f"{d.day} de {MESES_ES[d.month]} de {d.year}"
def fmt_mes_anio(d):
    return f"{MESES_ES[d.month].capitalize()} {d.year}"

def calcular_plan(fecha_viaje_str, total_usd, n_cuotas):
    partes = fecha_viaje_str.split('/')
    fecha_viaje = date(int(partes[2]), int(partes[1]), int(partes[0]))
    fecha_limite = fecha_viaje - timedelta(days=45)
    if fecha_limite.day > 15:
        ultimo_pago = date(fecha_limite.year, fecha_limite.month, 15)
    else:
        ultimo_pago = date(fecha_limite.year, fecha_limite.month, 1)
    if ultimo_pago > fecha_limite:
        m = fecha_limite.month - 1 or 12
        y = fecha_limite.year - (1 if fecha_limite.month == 1 else 0)
        ultimo_pago = date(y, m, 15)
    fechas = []
    mes_actual, anio_actual, dia_pago = ultimo_pago.month, ultimo_pago.year, ultimo_pago.day
    for _ in range(n_cuotas):
        fechas.append(date(anio_actual, mes_actual, dia_pago))
        mes_actual -= 1
        if mes_actual == 0:
            mes_actual, anio_actual = 12, anio_actual - 1
    fechas.reverse()
    monto_base = round(total_usd / n_cuotas, 0)
    ultima_cuota = round(total_usd - monto_base * (n_cuotas - 1), 0)
    cuotas = [{'n': i+1, 'fecha': f, 'monto': (ultima_cuota if i == n_cuotas-1 else monto_base)} for i, f in enumerate(fechas)]
    return cuotas, fecha_viaje, ultimo_pago

def generar_cotizacion_bytes(datos):
    import io
    buf = io.BytesIO()
    E = {
        'titulo': ParagraphStyle('t', fontName='Helvetica-Bold', fontSize=22, textColor=BLANCO, alignment=TA_CENTER, spaceAfter=4),
        'subtitulo': ParagraphStyle('s', fontName='Helvetica', fontSize=11, textColor=colors.HexColor('#C8E6C9'), alignment=TA_CENTER),
        'seccion': ParagraphStyle('sec', fontName='Helvetica-Bold', fontSize=9, textColor=VERDE_OSCURO, spaceAfter=6, spaceBefore=2),
        'label': ParagraphStyle('l', fontName='Helvetica', fontSize=8, textColor=GRIS_TEXTO),
        'valor': ParagraphStyle('v', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#1A1A1A')),
        'normal': ParagraphStyle('n', fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#333333'), leading=14),
        'cuota_num': ParagraphStyle('cn', fontName='Helvetica-Bold', fontSize=9, textColor=BLANCO, alignment=TA_CENTER),
        'cuota_texto': ParagraphStyle('ct', fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#1A1A1A')),
        'cuota_monto': ParagraphStyle('cm', fontName='Helvetica-Bold', fontSize=10, textColor=VERDE_OSCURO, alignment=TA_RIGHT),
        'importante': ParagraphStyle('imp', fontName='Helvetica-Bold', fontSize=8, textColor=ROJO),
        'pie': ParagraphStyle('p', fontName='Helvetica', fontSize=7, textColor=GRIS_TEXTO, alignment=TA_CENTER, leading=10),
        'nota': ParagraphStyle('nota', fontName='Helvetica-Oblique', fontSize=8, textColor=GRIS_TEXTO, leading=11),
    }
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=15*mm, bottomMargin=15*mm)
    W = A4[0] - 36*mm
    nombre = datos['nombre']
    programa = datos['programa']
    valor = float(datos.get('valor', 0))
    descuento = float(datos.get('descuento', 0))
    upgrade = float(datos.get('upgrade', 0))
    reprog = float(datos.get('reprog', 0))
    n_cuotas = int(datos['cuotas'])
    quien = datos.get('quien', 'Equipo TEB')
    notas_extra = datos.get('notas', '')
    total = valor - descuento + upgrade + reprog
    cuotas, fv, fl = calcular_plan(datos['fecha_viaje'], total, n_cuotas)
    story = []

    # Header
    ht = Table([[Paragraph('The Experience Bureau', E['titulo'])]], colWidths=[W])
    ht.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),VERDE_OSCURO),('TOPPADDING',(0,0),(-1,-1),16),('BOTTOMPADDING',(0,0),(-1,-1),8),('LEFTPADDING',(0,0),(-1,-1),20)]))
    story.append(ht)
    st = Table([[Paragraph('Propuesta de plan de pagos · Broadway NYC', E['subtitulo'])]], colWidths=[W])
    st.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),VERDE_MEDIO),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    story.append(st)
    story.append(Spacer(1,6*mm))

    # Alumno
    story.append(Paragraph('Datos del alumno', E['seccion']))
    at = Table([[Paragraph('Nombre',E['label']),Paragraph('Programa',E['label']),Paragraph('Fecha de viaje',E['label'])],[Paragraph(nombre,E['valor']),Paragraph(programa,E['valor']),Paragraph(fmt_fecha(fv),E['valor'])]], colWidths=[W*0.4,W*0.3,W*0.3])
    at.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),GRIS_CLARO),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('LEFTPADDING',(0,0),(-1,-1),12),('LINEBELOW',(0,0),(-1,0),0.5,GRIS_LINEA)]))
    story.append(at)
    story.append(Spacer(1,5*mm))

    # Económico
    story.append(Paragraph('Detalle economico', E['seccion']))
    filas_eco = [[Paragraph('Concepto',E['label']),Paragraph('',E['label']),Paragraph('Importe',E['label'])],[Paragraph('Valor del programa',E['normal']),Paragraph('',E['normal']),Paragraph(f'USD {valor:,.0f}',E['normal'])]]
    if descuento > 0: filas_eco.append([Paragraph('Beca / descuento aplicado',E['normal']),Paragraph('',E['normal']),Paragraph(f'- USD {descuento:,.0f}',ParagraphStyle('d',fontName='Helvetica',fontSize=10,textColor=VERDE_MEDIO))])
    if upgrade > 0: filas_eco.append([Paragraph('Upgrade de plan',E['normal']),Paragraph('',E['normal']),Paragraph(f'+ USD {upgrade:,.0f}',ParagraphStyle('u',fontName='Helvetica',fontSize=10,textColor=AZUL))])
    if reprog > 0: filas_eco.append([Paragraph('Costo de reprogramacion',E['normal']),Paragraph('',E['normal']),Paragraph(f'+ USD {reprog:,.0f}',ParagraphStyle('r',fontName='Helvetica',fontSize=10,textColor=ROJO))])
    filas_eco.append(['','',''])
    filas_eco.append([Paragraph('TOTAL A ABONAR',ParagraphStyle('tl',fontName='Helvetica-Bold',fontSize=11,textColor=VERDE_OSCURO)),Paragraph('',E['normal']),Paragraph(f'USD {total:,.0f}',ParagraphStyle('tv',fontName='Helvetica-Bold',fontSize=14,textColor=VERDE_OSCURO,alignment=TA_RIGHT))])
    nf = len(filas_eco)
    eco_t = Table(filas_eco, colWidths=[W*0.55,W*0.05,W*0.4])
    eco_t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),BLANCO),('LINEBELOW',(0,0),(-1,0),0.5,GRIS_LINEA),('LINEABOVE',(0,nf-1),(-1,nf-1),1,VERDE_BORDE),('BACKGROUND',(0,nf-1),(-1,nf-1),VERDE_CLARO),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LEFTPADDING',(0,0),(-1,-1),12),('ALIGN',(2,0),(2,-1),'RIGHT'),('RIGHTPADDING',(2,0),(2,-1),12),('BOX',(0,0),(-1,-1),0.5,GRIS_LINEA)]))
    story.append(eco_t)
    story.append(Spacer(1,5*mm))

    # Cuotas
    story.append(Paragraph('Plan de pagos', E['seccion']))
    resumen = f"{n_cuotas} cuotas de USD {cuotas[0]['monto']:,.0f} ({fmt_mes_anio(cuotas[0]['fecha'])} a {fmt_mes_anio(cuotas[-1]['fecha'])}) · Pagos del 1 al 15 de cada mes"
    story.append(Paragraph(resumen, E['normal']))
    story.append(Spacer(1,3*mm))
    ch = [Paragraph('#',E['cuota_num']),Paragraph('Periodo',E['cuota_num']),Paragraph('Vencimiento',E['cuota_num']),Paragraph('Importe',E['cuota_num']),Paragraph('Estado',E['cuota_num'])]
    cr = [ch]
    for c in cuotas:
        cr.append([Paragraph(str(c['n']),ParagraphStyle('x',fontName='Helvetica-Bold',fontSize=9,alignment=TA_CENTER,textColor=VERDE_OSCURO)),Paragraph(fmt_mes_anio(c['fecha']),E['cuota_texto']),Paragraph(f"Del 1 al 15 de {MESES_ES[c['fecha'].month]}",E['cuota_texto']),Paragraph(f"USD {c['monto']:,.0f}",E['cuota_monto']),Paragraph('Pendiente',ParagraphStyle('p',fontName='Helvetica',fontSize=8,textColor=colors.HexColor('#633806'),alignment=TA_CENTER))])
    ct = Table(cr, colWidths=[W*0.07,W*0.22,W*0.30,W*0.20,W*0.21], repeatRows=1)
    cst = [('BACKGROUND',(0,0),(-1,0),VERDE_OSCURO),('TOPPADDING',(0,0),(-1,0),8),('BOTTOMPADDING',(0,0),(-1,0),8),('ROWBACKGROUNDS',(0,1),(-1,-1),[BLANCO,GRIS_CLARO]),('TOPPADDING',(0,1),(-1,-1),7),('BOTTOMPADDING',(0,1),(-1,-1),7),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('ALIGN',(0,0),(0,-1),'CENTER'),('ALIGN',(3,0),(3,-1),'RIGHT'),('ALIGN',(4,0),(4,-1),'CENTER'),('BOX',(0,0),(-1,-1),0.5,GRIS_LINEA),('INNERGRID',(0,1),(-1,-1),0.3,GRIS_LINEA),('BACKGROUND',(0,len(cuotas)),(-1,len(cuotas)),VERDE_CLARO),('LINEABOVE',(0,len(cuotas)),(-1,len(cuotas)),1,VERDE_BORDE)]
    ct.setStyle(TableStyle(cst))
    story.append(ct)
    story.append(Spacer(1,3*mm))

    # Alerta
    alt = Table([[Paragraph(f"IMPORTANTE: El ultimo pago debe acreditarse antes del {fmt_fecha(fl)} (45 dias previos al inicio del viaje el {fmt_fecha(fv)}).", E['importante'])]], colWidths=[W])
    alt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#FCEBEB')),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('LEFTPADDING',(0,0),(-1,-1),12),('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#F7C1C1'))]))
    story.append(alt)
    story.append(Spacer(1,4*mm))

    # Métodos
    story.append(Paragraph('Medios de pago aceptados', E['seccion']))
    mt = Table([[Paragraph('Stripe (tarjeta)',E['normal']),Paragraph('Transferencia bancaria',E['normal']),Paragraph('MercadoPago',E['normal']),Paragraph('BOFA / Wire transfer',E['normal'])]], colWidths=[W/4]*4)
    mt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),GRIS_CLARO),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('LEFTPADDING',(0,0),(-1,-1),10),('INNERGRID',(0,0),(-1,-1),0.3,GRIS_LINEA),('BOX',(0,0),(-1,-1),0.5,GRIS_LINEA),('ALIGN',(0,0),(-1,-1),'CENTER')]))
    story.append(mt)

    if notas_extra:
        story.append(Spacer(1,3*mm))
        nt = Table([[Paragraph(notas_extra, E['nota'])]], colWidths=[W])
        nt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#E6F1FB')),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('LEFTPADDING',(0,0),(-1,-1),12),('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#B5D4F4'))]))
        story.append(nt)

    story.append(HRFlowable(width=W, thickness=0.5, color=GRIS_LINEA))
    story.append(Spacer(1,2*mm))
    story.append(Paragraph(f"Propuesta emitida el {fmt_fecha(date.today())} por {quien}  ·  The Experience Bureau  ·  Importes en USD  ·  Validez: 15 dias.", E['pie']))

    doc.build(story)
    return buf.getvalue()


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/generar-cotizacion':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            datos = json.loads(body)
            try:
                pdf_bytes = generar_cotizacion_bytes(datos)
                nombre_archivo = f"TEB_cotizacion_{datos.get('nombre','alumno').replace(' ','_')}.pdf"
                self.send_response(200)
                self.send_header('Content-Type', 'application/pdf')
                self.send_header('Content-Disposition', f'attachment; filename="{nombre_archivo}"')
                self.send_header('Content-Length', str(len(pdf_bytes)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(pdf_bytes)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            super().do_POST()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        print(f"[TEB Server] {format % args}")

if __name__ == '__main__':
    PORT = 8765
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = HTTPServer(('localhost', PORT), Handler)
    print(f"\n✓ Servidor TEB corriendo en http://localhost:{PORT}")
    print(f"✓ Abrí cotizador.html en tu navegador")
    print(f"  (o entrá a http://localhost:{PORT}/cotizador.html)")
    print(f"\nPresioná Ctrl+C para detener.\n")
    threading.Timer(1.5, lambda: webbrowser.open(f'http://localhost:{PORT}/cotizador.html')).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
