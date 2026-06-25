from http.server import BaseHTTPRequestHandler
import json, io
from datetime import date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

V_OSC = colors.HexColor('#004225')
V_MED = colors.HexColor('#2E7D32')
V_CLA = colors.HexColor('#EAF3DE')
V_BOR = colors.HexColor('#C0DD97')
G_CLA = colors.HexColor('#F5F5F0')
G_TXT = colors.HexColor('#666666')
G_LIN = colors.HexColor('#E0E0D8')
ROJO  = colors.HexColor('#791F1F')
AZUL  = colors.HexColor('#0C447C')
AMBAR = colors.HexColor('#633806')
BCA   = colors.HexColor('#FAEEDA')
BCA_B = colors.HexColor('#FAC775')
BLANCO= colors.white

MESES = {1:'enero',2:'febrero',3:'marzo',4:'abril',5:'mayo',6:'junio',
         7:'julio',8:'agosto',9:'septiembre',10:'octubre',11:'noviembre',12:'diciembre'}

EDICIONES = {
    'Julio 2026': {'inicio': date(2026,7,10),'checkin':'10 de julio de 2026 a las 4:00 PM','checkout':'31 de julio de 2026 a las 12:00 PM','label':'TEB NYC — Julio 2026','duracion':'21 dias'},
    'Enero 2027': {'inicio': date(2027,1,27),'checkin':'27 de enero de 2027 a las 4:00 PM','checkout':'10 de febrero de 2027 a las 12:00 PM','label':'TEB NYC — Enero 2027','duracion':'14 dias'},
    'Julio 2027': {'inicio': date(2027,7,16),'checkin':'16 de julio de 2027 a las 4:00 PM','checkout':'30 de julio de 2027 a las 12:00 PM','label':'TEB NYC — Julio 2027','duracion':'14 dias'},
    'Enero 2028': {'inicio': date(2028,1,15),'checkin':'A confirmar','checkout':'A confirmar','label':'TEB NYC — Enero 2028','duracion':'A confirmar'},
}

PLANES = {
    'Economy':       {'color': G_CLA, 'color_txt': colors.HexColor('#444444'), 'icono': '●'},
    'Comfort':       {'color': colors.HexColor('#E6F1FB'), 'color_txt': AZUL, 'icono': '◆'},
    'Comfort Stay+': {'color': colors.HexColor('#EEEDFE'), 'color_txt': colors.HexColor('#3C3489'), 'icono': '★'},
    'Sin hotel':     {'color': colors.HexColor('#F1EFE8'), 'color_txt': G_TXT, 'icono': '○'},
}
PLAN_DESC = {
    'Economy':       'Habitacion compartida en hotel seleccionado por TEB NYC.',
    'Comfort':       'Habitacion doble o triple en hotel de categoria superior.',
    'Comfort Stay+': 'Habitacion individual o suite. Maxima comodidad y privacidad.',
    'Sin hotel':     'El alumno gestiona su propio alojamiento. No incluye hospedaje.',
}

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
        'tit':   ParagraphStyle('tit', fontName='Helvetica-Bold', fontSize=22, textColor=BLANCO, alignment=TA_CENTER),
        'sub':   ParagraphStyle('sub', fontName='Helvetica', fontSize=11, textColor=colors.HexColor('#C8E6C9'), alignment=TA_CENTER),
        'edi':   ParagraphStyle('edi', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#A5D6A7'), alignment=TA_CENTER),
        'sec':   ParagraphStyle('sec', fontName='Helvetica-Bold', fontSize=9, textColor=V_OSC, spaceAfter=5),
        'lbl':   ParagraphStyle('lbl', fontName='Helvetica', fontSize=8, textColor=G_TXT),
        'val':   ParagraphStyle('val', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#1A1A1A')),
        'nor':   ParagraphStyle('nor', fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#333333'), leading=14),
        'cn':    ParagraphStyle('cn', fontName='Helvetica-Bold', fontSize=9, textColor=BLANCO, alignment=TA_CENTER),
        'ct':    ParagraphStyle('ct', fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#1A1A1A')),
        'cm':    ParagraphStyle('cm', fontName='Helvetica-Bold', fontSize=10, textColor=V_OSC, alignment=TA_RIGHT),
        'imp':   ParagraphStyle('imp', fontName='Helvetica-Bold', fontSize=8, textColor=ROJO),
        'pie':   ParagraphStyle('pie', fontName='Helvetica', fontSize=7, textColor=G_TXT, alignment=TA_CENTER, leading=10),
        'nota':  ParagraphStyle('nota', fontName='Helvetica-Oblique', fontSize=8, textColor=G_TXT, leading=11),
    }

def generar_pdf(datos):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=14*mm, bottomMargin=14*mm)
    W = A4[0] - 36*mm
    E = estilos()
    st = []

    nombre   = datos['nombre']
    programa = datos['programa']
    ed_key   = datos.get('edicion', '')
    plan_key = datos.get('plan', 'Economy')
    valor    = float(datos.get('valor_programa', 0))
    desc     = float(datos.get('descuento', 0))
    upgrade  = float(datos.get('upgrade', 0))
    reprog   = float(datos.get('reprogramacion', 0))
    n_cuotas = int(datos['cuotas'])
    quien    = datos.get('quien_recibe', 'TEB NYC')
    notas_x  = datos.get('notas', '')
    total    = valor - desc + upgrade + reprog

    ed = EDICIONES.get(ed_key, {})
    fv = ed.get('inicio', date.today() + timedelta(days=180))
    cuotas, fecha_lim = calcular_cuotas(fv, total, n_cuotas)
    plan_info = PLANES.get(plan_key, PLANES['Economy'])

    h_data = [[Paragraph('TEB NYC', E['tit'])],[Paragraph('Broadway New York City', E['sub'])]]
    if ed_key in EDICIONES:
        h_data.append([Paragraph(EDICIONES[ed_key]['label'], E['edi'])])
    ht = Table(h_data, colWidths=[W])
    ht.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),V_OSC),('TOPPADDING',(0,0),(-1,0),18),
        ('BOTTOMPADDING',(0,-1),(-1,-1),14),('TOPPADDING',(0,1),(-1,-1),3),
        ('LEFTPADDING',(0,0),(-1,-1),20),('RIGHTPADDING',(0,0),(-1,-1),20),
    ]))
    st.append(ht)
    barra = Table([[Paragraph('Propuesta de plan de pagos personalizado', E['sub'])]], colWidths=[W])
    barra.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),V_MED),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    st.append(barra)
    st.append(Spacer(1, 5*mm))

    st.append(Paragraph('Datos del alumno', E['sec']))
    at = Table([
        [Paragraph('Nombre', E['lbl']), Paragraph('Programa', E['lbl']), Paragraph('Edicion', E['lbl'])],
        [Paragraph(nombre, E['val']), Paragraph(programa, E['val']), Paragraph(ed_key or '—', E['val'])],
    ], colWidths=[W*0.38, W*0.28, W*0.34])
    at.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),G_CLA),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('LEFTPADDING',(0,0),(-1,-1),12),('LINEBELOW',(0,0),(-1,0),0.5,G_LIN),('BOX',(0,0),(-1,-1),0.5,G_LIN),
    ]))
    st.append(at)
    st.append(Spacer(1, 4*mm))

    if ed_key in EDICIONES:
        st.append(Paragraph('Fechas del viaje', E['sec']))
        ed_data = EDICIONES[ed_key]
        ft = Table([
            [Paragraph('Check-in', E['lbl']), Paragraph('Check-out', E['lbl']), Paragraph('Duracion', E['lbl'])],
            [Paragraph(ed_data['checkin'], E['nor']), Paragraph(ed_data['checkout'], E['nor']), Paragraph(ed_data['duracion'], E['val'])],
        ], colWidths=[W*0.42, W*0.42, W*0.16])
        ft.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#E6F1FB')),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#B5D4F4')),
            ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('LEFTPADDING',(0,0),(-1,-1),12),
            ('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#B5D4F4')),('INNERGRID',(0,0),(-1,-1),0.3,colors.HexColor('#B5D4F4')),
        ]))
        st.append(ft)
        st.append(Spacer(1, 4*mm))

    st.append(Paragraph('Plan de hospedaje contratado', E['sec']))
    p_bg, p_txt, p_icono = plan_info['color'], plan_info['color_txt'], plan_info['icono']
    plan_label = ParagraphStyle('pl', fontName='Helvetica-Bold', fontSize=13, textColor=p_txt)
    plan_desc_s = ParagraphStyle('pd', fontName='Helvetica', fontSize=9, textColor=G_TXT, leading=12)
    pt = Table([[Paragraph(f"{p_icono}  {plan_key}", plan_label), Paragraph(PLAN_DESC.get(plan_key, ''), plan_desc_s)]], colWidths=[W*0.28, W*0.72])
    pt.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),p_bg),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),
        ('LEFTPADDING',(0,0),(-1,-1),14),('RIGHTPADDING',(0,0),(-1,-1),14),('BOX',(0,0),(-1,-1),1,p_txt),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
    ]))
    st.append(pt)
    st.append(Spacer(1, 4*mm))

    st.append(Paragraph('Detalle economico', E['sec']))
    eco = [[Paragraph('Concepto', E['lbl']), Paragraph('', E['lbl']), Paragraph('Importe', E['lbl'])],
           [Paragraph('Valor del programa', E['nor']), Paragraph('', E['nor']), Paragraph(f'USD {valor:,.0f}', E['nor'])]]
    if desc > 0:
        eco.append([Paragraph('Beca / descuento aplicado', E['nor']), Paragraph('', E['nor']), Paragraph(f'- USD {desc:,.0f}', ParagraphStyle('d',fontName='Helvetica',fontSize=10,textColor=V_MED))])
    if upgrade > 0:
        eco.append([Paragraph('Upgrade de plan', E['nor']), Paragraph('', E['nor']), Paragraph(f'+ USD {upgrade:,.0f}', ParagraphStyle('u',fontName='Helvetica',fontSize=10,textColor=AZUL))])
    if reprog > 0:
        eco.append([Paragraph('Costo de reprogramacion', E['nor']), Paragraph('', E['nor']), Paragraph(f'+ USD {reprog:,.0f}', ParagraphStyle('r',fontName='Helvetica',fontSize=10,textColor=ROJO))])
    eco.append(['', '', ''])
    eco.append([Paragraph('TOTAL A ABONAR', ParagraphStyle('tl',fontName='Helvetica-Bold',fontSize=11,textColor=V_OSC)), Paragraph('', E['nor']),
                Paragraph(f'USD {total:,.0f}', ParagraphStyle('tv',fontName='Helvetica-Bold',fontSize=15,textColor=V_OSC,alignment=TA_RIGHT))])
    nf = len(eco)
    et = Table(eco, colWidths=[W*0.55, W*0.05, W*0.40])
    et.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),BLANCO),('LINEBELOW',(0,0),(-1,0),0.5,G_LIN),
        ('LINEABOVE',(0,nf-1),(-1,nf-1),1,V_BOR),('BACKGROUND',(0,nf-1),(-1,nf-1),V_CLA),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LEFTPADDING',(0,0),(-1,-1),12),
        ('ALIGN',(2,0),(2,-1),'RIGHT'),('RIGHTPADDING',(2,0),(2,-1),12),('BOX',(0,0),(-1,-1),0.5,G_LIN),
    ]))
    st.append(et)
    st.append(Spacer(1, 4*mm))

    st.append(Paragraph('Plan de pagos', E['sec']))
    resumen = f"{n_cuotas} cuota{'s' if n_cuotas>1 else ''} de USD {cuotas[0]['monto']:,.0f}  ({fmt_mes(cuotas[0]['fecha'])} a {fmt_mes(cuotas[-1]['fecha'])})  ·  Pagos del 1 al 15 de cada mes"
    st.append(Paragraph(resumen, E['nor']))
    st.append(Spacer(1, 3*mm))

    ch = [Paragraph('#', E['cn']), Paragraph('Periodo', E['cn']), Paragraph('Vencimiento', E['cn']), Paragraph('Importe', E['cn']), Paragraph('Estado', E['cn'])]
    cr = [ch]
    for c in cuotas:
        estado_txt = 'Ultimo pago' if c['ultima'] else 'Pendiente'
        estado_col = AMBAR if c['ultima'] else G_TXT
        cr.append([
            Paragraph(str(c['n']), ParagraphStyle('x',fontName='Helvetica-Bold',fontSize=9,alignment=TA_CENTER,textColor=V_OSC)),
            Paragraph(fmt_mes(c['fecha']), E['ct']),
            Paragraph(f"Del 1 al 15 de {MESES[c['fecha'].month]}", E['ct']),
            Paragraph(f"USD {c['monto']:,.0f}", E['cm']),
            Paragraph(estado_txt, ParagraphStyle('est',fontName='Helvetica'+('-Bold' if c['ultima'] else ''),fontSize=8,textColor=estado_col,alignment=TA_CENTER)),
        ])
    ct = Table(cr, colWidths=[W*0.07, W*0.21, W*0.31, W*0.20, W*0.21], repeatRows=1)
    n_tabla = len(cuotas)
    ct.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),V_OSC),('TOPPADDING',(0,0),(-1,0),8),('BOTTOMPADDING',(0,0),(-1,0),8),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[BLANCO,G_CLA]),('TOPPADDING',(0,1),(-1,-1),7),('BOTTOMPADDING',(0,1),(-1,-1),7),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('ALIGN',(0,0),(0,-1),'CENTER'),
        ('ALIGN',(3,0),(3,-1),'RIGHT'),('ALIGN',(4,0),(4,-1),'CENTER'),('BOX',(0,0),(-1,-1),0.5,G_LIN),
        ('INNERGRID',(0,1),(-1,-1),0.3,G_LIN),('BACKGROUND',(0,n_tabla),(-1,n_tabla),BCA),('LINEABOVE',(0,n_tabla),(-1,n_tabla),1,BCA_B),
    ]))
    st.append(ct)
    st.append(Spacer(1, 3*mm))

    alerta_txt = f"IMPORTANTE: El ultimo pago debe acreditarse antes del {fmt(fecha_lim)}. El viaje inicia el {fmt(fv)} — se requieren 45 dias de anticipacion."
    alt = Table([[Paragraph(alerta_txt, E['imp'])]], colWidths=[W])
    alt.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#FCEBEB')),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#F7C1C1')),
    ]))
    st.append(alt)
    st.append(Spacer(1, 4*mm))

    st.append(Paragraph('Medios de pago aceptados', E['sec']))
    mt = Table([[Paragraph('Stripe (tarjeta)', E['nor']), Paragraph('Transferencia bancaria', E['nor']), Paragraph('MercadoPago', E['nor']), Paragraph('BOFA / Wire transfer', E['nor'])]], colWidths=[W/4]*4)
    mt.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),G_CLA),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('LEFTPADDING',(0,0),(-1,-1),10),('INNERGRID',(0,0),(-1,-1),0.3,G_LIN),('BOX',(0,0),(-1,-1),0.5,G_LIN),('ALIGN',(0,0),(-1,-1),'CENTER'),
    ]))
    st.append(mt)

    if notas_x:
        st.append(Spacer(1, 3*mm))
        nt = Table([[Paragraph(notas_x, E['nota'])]], colWidths=[W])
        nt.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#E6F1FB')),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
            ('LEFTPADDING',(0,0),(-1,-1),12),('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#B5D4F4')),
        ]))
        st.append(nt)

    st.append(Spacer(1, 4*mm))
    st.append(HRFlowable(width=W, thickness=0.5, color=G_LIN))
    st.append(Spacer(1, 2*mm))
    st.append(Paragraph(f"Propuesta emitida el {fmt(date.today())} por {quien}  ·  TEB NYC  ·  Importes en dolares estadounidenses (USD)  ·  Validez: 15 dias.", E['pie']))

    doc.build(st)
    return buf.getvalue()


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            datos = json.loads(body)
            pdf_bytes = generar_pdf(datos)
            nombre = datos.get('nombre', 'alumno').replace(' ', '_')
            edicion = datos.get('edicion', '').replace(' ', '_')
            filename = f"TEB_{nombre}_{edicion}.pdf"

            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
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
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
