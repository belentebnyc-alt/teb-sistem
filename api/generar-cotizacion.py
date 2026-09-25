from http.server import BaseHTTPRequestHandler
import json, io
from datetime import date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

NEGRO  = colors.HexColor('#111111')
GRIS1  = colors.HexColor('#333333')
GRIS2  = colors.HexColor('#555555')
GRIS3  = colors.HexColor('#888888')
GRIS_F = colors.HexColor('#F5F5F0')
GRIS_L = colors.HexColor('#E0E0D8')
GRIS_M = colors.HexColor('#F0F0F0')
BLANCO = colors.white
ROJO   = colors.HexColor('#791F1F')
ROJO_F = colors.HexColor('#FCEBEB')
ROJO_B = colors.HexColor('#F7C1C1')

MESES = {1:'enero',2:'febrero',3:'marzo',4:'abril',5:'mayo',6:'junio',
         7:'julio',8:'agosto',9:'septiembre',10:'octubre',11:'noviembre',12:'diciembre'}

EDICIONES = {
    'Julio 2026': {'inicio': date(2026,7,10), 'checkin':'10 de julio de 2026 a las 4:00 PM',  'checkout':'31 de julio de 2026 a las 12:00 PM',  'label':'TEB NYC — Julio 2026',  'duracion':'21 dias'},
    'Enero 2027': {'inicio': date(2027,1,27), 'checkin':'27 de enero de 2027 a las 4:00 PM',  'checkout':'10 de febrero de 2027 a las 12:00 PM','label':'TEB NYC — Enero 2027',  'duracion':'14 dias'},
    'Julio 2027': {'inicio': date(2027,7,16), 'checkin':'16 de julio de 2027 a las 4:00 PM',  'checkout':'30 de julio de 2027 a las 12:00 PM', 'label':'TEB NYC — Julio 2027',  'duracion':'14 dias'},
    'Enero 2028': {'inicio': date(2028,1,15), 'checkin':'A confirmar', 'checkout':'A confirmar', 'label':'TEB NYC — Enero 2028', 'duracion':'A confirmar'},
    'Julio 2028': {'inicio': date(2028,7,15), 'checkin':'A confirmar', 'checkout':'A confirmar', 'label':'TEB NYC — Julio 2028', 'duracion':'A confirmar'},
    'Enero 2029': {'inicio': date(2029,1,15), 'checkin':'A confirmar', 'checkout':'A confirmar', 'label':'TEB NYC — Enero 2029', 'duracion':'A confirmar'},
    'Julio 2029': {'inicio': date(2029,7,15), 'checkin':'A confirmar', 'checkout':'A confirmar', 'label':'TEB NYC — Julio 2029', 'duracion':'A confirmar'},
}

PLAN_DESC = {
    'Economy':       'Habitacion compartida en hotel seleccionado por TEB NYC.',
    'Comfort':       'Habitacion doble o triple en hotel de categoria superior.',
    'Comfort Stay+': 'Habitacion individual o suite. Maxima comodidad y privacidad.',
    'Sin hotel':     'El alumno gestiona su propio alojamiento. No incluye hospedaje.',
}

INFO_LEGAL = 'Tu Experiencia Broadway, Inc. · 20801 Biscayne Blvd, Suite 403, PMB 1006, Aventura, Florida, 33180, Estados Unidos'

def fmt(d):
    return f"{d.day} de {MESES[d.month]} de {d.year}"

def fmt_mes(d):
    return f"{MESES[d.month].capitalize()} {d.year}"

def calcular_cuotas(fecha_viaje, total, n):
    limite = fecha_viaje - timedelta(days=45)
    m, y = limite.month, limite.year
    candidato = date(y, m, 15)
    if candidato > limite:
        m -= 1
        if m == 0: m, y = 12, y - 1
        candidato = date(y, m, 15)
    fechas, cm, cy = [], candidato.month, candidato.year
    for _ in range(n):
        fechas.append(date(cy, cm, 15))
        cm -= 1
        if cm == 0: cm, cy = 12, cy - 1
    fechas.reverse()
    base = round(total / n, 0)
    ult = round(total - base * (n - 1), 0)
    return [{'n': i+1, 'fecha': f, 'monto': (ult if i==n-1 else base), 'ultima': i==n-1} for i, f in enumerate(fechas)], candidato

def estilos():
    return {
        'tit':   ParagraphStyle('tit',   fontName='Helvetica-Bold',   fontSize=24, textColor=BLANCO,  alignment=TA_CENTER),
        'sub':   ParagraphStyle('sub',   fontName='Helvetica',         fontSize=10, textColor=colors.HexColor('#999999'), alignment=TA_CENTER, leading=14),
        'edi':   ParagraphStyle('edi',   fontName='Helvetica-Bold',    fontSize=12, textColor=colors.HexColor('#aaaaaa'), alignment=TA_CENTER),
        'sec':   ParagraphStyle('sec',   fontName='Helvetica-Bold',    fontSize=9,  textColor=NEGRO,   spaceAfter=5, leading=12),
        'lbl':   ParagraphStyle('lbl',   fontName='Helvetica',         fontSize=8,  textColor=GRIS3),
        'val':   ParagraphStyle('val',   fontName='Helvetica-Bold',    fontSize=12, textColor=NEGRO),
        'nor':   ParagraphStyle('nor',   fontName='Helvetica',         fontSize=10, textColor=GRIS1,   leading=14),
        'pie':   ParagraphStyle('pie',   fontName='Helvetica',         fontSize=7,  textColor=GRIS3,   alignment=TA_CENTER, leading=10),
        'nota':  ParagraphStyle('nota',  fontName='Helvetica-Oblique', fontSize=8,  textColor=GRIS2,   leading=11),
        'legal': ParagraphStyle('legal', fontName='Helvetica',         fontSize=7,  textColor=GRIS3,   alignment=TA_CENTER, leading=10),
        'plan_n':ParagraphStyle('plan_n',fontName='Helvetica-Bold',    fontSize=20, textColor=BLANCO,  leading=24),
        'plan_s':ParagraphStyle('plan_s',fontName='Helvetica',         fontSize=11, textColor=colors.HexColor('#cccccc'), leading=15),
        'plan_d':ParagraphStyle('plan_d',fontName='Helvetica',         fontSize=9,  textColor=colors.HexColor('#999999'), leading=13),
        'imp':   ParagraphStyle('imp',   fontName='Helvetica-Bold',    fontSize=8,  textColor=ROJO),
    }

def generar_pdf(datos):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=14*mm, bottomMargin=14*mm)
    W = A4[0] - 36*mm
    E = estilos()
    st = []

    nombre   = datos['nombre']
    programa = datos['programa']
    ed_key   = datos.get('edicion', '')
    plan_key = datos.get('plan', 'Economy')
    valor    = float(datos.get('valor_programa', 0))
    desc     = float(datos.get('descuento', 0))
    desc5    = float(datos.get('descuento5', 0))
    upgrade  = float(datos.get('upgrade', 0))
    reprog   = float(datos.get('reprogramacion', 0))
    n_cuotas = int(datos['cuotas'])
    quien    = datos.get('quien_recibe', 'TEB NYC')
    notas_x  = datos.get('notas', '')
    total    = valor - desc - desc5 + upgrade + reprog

    ed = EDICIONES.get(ed_key, {})
    fv = ed.get('inicio', date.today() + timedelta(days=180))

    pago_inicial_400 = datos.get('pago_inicial_400', False)
    total_cuotas = total - 400 if pago_inicial_400 else total

    # Si vienen fechas manuales, usarlas directamente (sin regla 45 días)
    cuotas_fechas_str = datos.get('cuotas_fechas', None)
    if cuotas_fechas_str:
        fechas_manual = [date.fromisoformat(s) for s in cuotas_fechas_str]
        n_cuotas  = len(fechas_manual)
        base      = round(total_cuotas / n_cuotas, 0)
        ult       = round(total_cuotas - base * (n_cuotas - 1), 0)
        cuotas    = [{'n':i+1,'fecha':f,'monto':(ult if i==n_cuotas-1 else base),'ultima':i==n_cuotas-1} for i,f in enumerate(fechas_manual)]
        fecha_lim = fechas_manual[-1]    else:
        cuotas, fecha_lim = calcular_cuotas(fv, total_cuotas, n_cuotas)

    # ── ENCABEZADO ───────────────────────────────────────────
    h_rows = [[Paragraph('TEB NYC', E['tit'])]]
    if ed_key in EDICIONES:
        h_rows.append([Paragraph(ed_key, E['edi'])])
    ht = Table(h_rows, colWidths=[W])
    ht.setStyle(TableStyle([
        ('BACKGROUND',   (0,0),(-1,-1), NEGRO),
        ('TOPPADDING',   (0,0),(-1, 0), 18),
        ('BOTTOMPADDING',(0,-1),(-1,-1), 14),
        ('TOPPADDING',   (0,1),(-1,-1), 3),
        ('LEFTPADDING',  (0,0),(-1,-1), 20),
        ('RIGHTPADDING', (0,0),(-1,-1), 20),
    ]))
    st.append(ht)
    barra = Table([[Paragraph('Propuesta de plan de pagos personalizado', E['sub'])]], colWidths=[W])
    barra.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),GRIS1),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    st.append(barra)
    st.append(Spacer(1, 5*mm))

    # ── DATOS DEL ALUMNO ─────────────────────────────────────
    st.append(Paragraph('Datos del alumno', E['sec']))
    at = Table([
        [Paragraph('Nombre', E['lbl']),  Paragraph('Programa', E['lbl']), Paragraph('Edicion', E['lbl'])],
        [Paragraph(nombre, E['val']),    Paragraph(programa, E['val']),   Paragraph(ed_key or '—', E['val'])],
    ], colWidths=[W*0.38, W*0.28, W*0.34])
    at.setStyle(TableStyle([
        ('BACKGROUND',   (0,0),(-1,-1), GRIS_F),
        ('TOPPADDING',   (0,0),(-1,-1), 8),('BOTTOMPADDING',(0,0),(-1,-1), 8),
        ('LEFTPADDING',  (0,0),(-1,-1), 12),
        ('LINEBELOW',    (0,0),(-1, 0), 0.5, GRIS_L),('BOX',(0,0),(-1,-1),0.5,GRIS_L),
    ]))
    st.append(at)
    st.append(Spacer(1, 4*mm))

    # ── PLAN DE HOSPEDAJE ────────────────────────────────────
    st.append(Paragraph('Plan de hospedaje', E['sec']))
    plan_n = ParagraphStyle('pl', fontName='Helvetica-Bold', fontSize=13, textColor=NEGRO)
    plan_d = ParagraphStyle('pd', fontName='Helvetica',      fontSize=9,  textColor=GRIS3, leading=12)
    pt = Table([[Paragraph(plan_key, plan_n), Paragraph(PLAN_DESC.get(plan_key,''), plan_d)]], colWidths=[W*0.28, W*0.72])
    pt.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),GRIS_F),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),
        ('LEFTPADDING',(0,0),(-1,-1),14),('RIGHTPADDING',(0,0),(-1,-1),14),
        ('BOX',(0,0),(-1,-1),1,GRIS_L),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
    ]))
    st.append(pt)
    st.append(Spacer(1, 4*mm))

    # ── DETALLE ECONOMICO ────────────────────────────────────
    st.append(Paragraph('Detalle economico', E['sec']))
    eco = [
        [Paragraph('Concepto', E['lbl']), '', Paragraph('Importe', E['lbl'])],
        [Paragraph('Valor del programa', E['nor']), '', Paragraph(f'USD {valor:,.0f}', E['nor'])],
    ]
    if desc > 0:
        eco.append([Paragraph('Beca / descuento aplicado', E['nor']), '', Paragraph(f'- USD {desc:,.0f}', ParagraphStyle('d',fontName='Helvetica',fontSize=10,textColor=GRIS2))])
    if desc5 > 0:
        eco.append([Paragraph('Descuento 5% promocional Enero 2027', E['nor']), '', Paragraph(f'- USD {desc5:,.0f}', ParagraphStyle('d5',fontName='Helvetica',fontSize=10,textColor=GRIS2))])
    if upgrade > 0:
        eco.append([Paragraph('Upgrade de hospedaje', E['nor']), '', Paragraph(f'+ USD {upgrade:,.0f}', ParagraphStyle('u',fontName='Helvetica',fontSize=10,textColor=GRIS1))])
    if upgrade < 0:
        eco.append([Paragraph('Descuento sin hotel', E['nor']), '', Paragraph(f'- USD {abs(upgrade):,.0f}', ParagraphStyle('sh',fontName='Helvetica',fontSize=10,textColor=GRIS2))])
    if reprog > 0:
        eco.append([Paragraph('Costo de reprogramacion', E['nor']), '', Paragraph(f'+ USD {reprog:,.0f}', ParagraphStyle('r',fontName='Helvetica',fontSize=10,textColor=ROJO))])
    eco.append(['','',''])
    eco.append([Paragraph('TOTAL A ABONAR', ParagraphStyle('tl',fontName='Helvetica-Bold',fontSize=11,textColor=NEGRO)), '',
                Paragraph(f'USD {total:,.0f}', ParagraphStyle('tv',fontName='Helvetica-Bold',fontSize=15,textColor=NEGRO,alignment=TA_RIGHT))])
    nf = len(eco)
    et = Table(eco, colWidths=[W*0.55, W*0.05, W*0.40])
    et.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),BLANCO),('LINEBELOW',(0,0),(-1,0),0.5,GRIS_L),
        ('LINEABOVE',(0,nf-1),(-1,nf-1),1,GRIS_L),('BACKGROUND',(0,nf-1),(-1,nf-1),GRIS_F),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),12),('ALIGN',(2,0),(2,-1),'RIGHT'),
        ('RIGHTPADDING',(2,0),(2,-1),12),('BOX',(0,0),(-1,-1),0.5,GRIS_L),
    ]))
    st.append(et)
    st.append(Spacer(1, 5*mm))

    # ── PLAN DE PAGOS — BLOQUE DESTACADO ─────────────────────
    primer_mes  = fmt_mes(cuotas[0]['fecha'])
    ultimo_mes  = fmt_mes(cuotas[-1]['fecha'])
    rango       = primer_mes if n_cuotas==1 else f"{primer_mes}  a  {ultimo_mes}"
    monto_cuota = cuotas[0]['monto']
    plan_rows = []
    if pago_inicial_400:
        mes_inicial   = datos.get('pago_ini_display') or '—'
        rango_cuotas  = fmt_mes(cuotas[0]['fecha']) if n_cuotas == 1 else f"{fmt_mes(cuotas[0]['fecha'])}  a  {fmt_mes(cuotas[-1]['fecha'])}"
        plan_rows.append([Paragraph(f"Pago inicial:  USD 400  —  {mes_inicial}", E['plan_s'])])
        plan_rows.append([Paragraph(" ", ParagraphStyle('sp', fontSize=4))])
        plan_rows += [
            [Paragraph(f"{n_cuotas} {'cuota' if n_cuotas==1 else 'cuotas'}  de  USD {monto_cuota:,.0f}", E['plan_n'])],
            [Paragraph(f"{rango_cuotas}", E['plan_s'])],
            [Paragraph(f"Del 1 al 15 de cada mes  ·  Ultimo pago: antes del {fmt(fecha_lim)}", E['plan_d'])],
        ]
    else:
        plan_rows += [
            [Paragraph(f"{n_cuotas} {'pago unico' if n_cuotas==1 else 'cuotas'}  de  USD {monto_cuota:,.0f}", E['plan_n'])],
            [Paragraph(f"{rango}", E['plan_s'])],
            [Paragraph(f"Del 1 al 15 de cada mes  ·  Ultimo pago: antes del {fmt(fecha_lim)}", E['plan_d'])],
        ]
    plan_data = plan_rows
    plan_t = Table(plan_data, colWidths=[W])
    plan_t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), NEGRO),
        ('TOPPADDING',    (0,0),(-1,-1), 5),('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('TOPPADDING',    (0,0),(-1, 0), 14),('BOTTOMPADDING',(0,-1),(-1,-1), 14),
        ('LEFTPADDING',   (0,0),(-1,-1), 18),('RIGHTPADDING',(0,0),(-1,-1), 18),
    ]))
    st.append(plan_t)
    st.append(Spacer(1, 3*mm))

    alerta_txt = f"IMPORTANTE: El ultimo pago debe realizarse antes del {fmt(fecha_lim)}."
    alt = Table([[Paragraph(alerta_txt, E['imp'])]], colWidths=[W])
    alt.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),ROJO_F),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('BOX',(0,0),(-1,-1),0.5,ROJO_B),
    ]))
    st.append(alt)
    st.append(Spacer(1, 5*mm))

    # ── MEDIOS DE PAGO ───────────────────────────────────────
    metodos_pago = datos.get('metodos_pago', ['Transferencia internacional a Bank of America','Tarjeta de credito o debito'])
    if not metodos_pago:
        metodos_pago = ['A coordinar con el equipo de TEB NYC']
    st.append(Paragraph('Medios de pago aceptados', E['sec']))
    met_s = ParagraphStyle('met', fontName='Helvetica', fontSize=9.5, textColor=GRIS1, leading=13)
    mt = Table([[Paragraph('•  '+m, met_s)] for m in metodos_pago], colWidths=[W])
    mt.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),GRIS_F),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),14),('INNERGRID',(0,0),(-1,-1),0.3,BLANCO),('BOX',(0,0),(-1,-1),0.5,GRIS_L),
    ]))
    st.append(mt)

    if notas_x:
        st.append(Spacer(1, 3*mm))
        nt = Table([[Paragraph(notas_x, E['nota'])]], colWidths=[W])
        nt.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1),GRIS_F),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
            ('LEFTPADDING',(0,0),(-1,-1),12),('BOX',(0,0),(-1,-1),0.5,GRIS_L),
        ]))
        st.append(nt)

    st.append(Spacer(1, 5*mm))
    st.append(HRFlowable(width=W, thickness=0.5, color=GRIS_L))
    st.append(Spacer(1, 2*mm))
    st.append(Paragraph(f"Propuesta emitida el {fmt(date.today())} por {quien}  ·  TEB NYC  ·  Importes en dolares estadounidenses (USD)  ·  Validez: 15 dias.", E['pie']))
    st.append(Spacer(1, 2*mm))
    st.append(Paragraph(INFO_LEGAL, E['legal']))

    doc.build(st)
    return buf.getvalue()


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body   = self.rfile.read(length)
            datos  = json.loads(body)
            pdf_bytes = generar_pdf(datos)
            nombre  = datos.get('nombre',  'alumno').replace(' ', '_')
            edicion = datos.get('edicion', '').replace(' ', '_')
            filename = f"TEB_{nombre}_{edicion}.pdf"
            self.send_response(200)
            self.send_header('Content-Type',        'application/pdf')
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(pdf_bytes)
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
