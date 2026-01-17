# ===================== GENERADOR DE REPORTES PDF =====================
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.graphics.shapes import Drawing, Rect, String, Circle
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime

# Colores corporativos
PRIMARY_COLOR = colors.HexColor('#6366f1')
PRIMARY_DARK = colors.HexColor('#4f46e5')
SUCCESS_COLOR = colors.HexColor('#10b981')
WARNING_COLOR = colors.HexColor('#f59e0b')
DANGER_COLOR = colors.HexColor('#ef4444')
GRAY_DARK = colors.HexColor('#1f2937')
GRAY_LIGHT = colors.HexColor('#f3f4f6')
WHITE = colors.white

def create_styles():
    """Crear estilos personalizados para el PDF"""
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name='MainTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=PRIMARY_COLOR,
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='Subtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=GRAY_DARK,
        spaceAfter=30,
        alignment=TA_CENTER
    ))
    
    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=PRIMARY_DARK,
        spaceBefore=25,
        spaceAfter=15,
        fontName='Helvetica-Bold',
        borderPadding=(0, 0, 5, 0)
    ))
    
    styles.add(ParagraphStyle(
        name='SubsectionTitle',
        parent=styles['Heading3'],
        fontSize=13,
        textColor=GRAY_DARK,
        spaceBefore=15,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='BodyText',
        parent=styles['Normal'],
        fontSize=10,
        textColor=GRAY_DARK,
        spaceAfter=8
    ))
    
    styles.add(ParagraphStyle(
        name='SmallText',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#6b7280')
    ))
    
    styles.add(ParagraphStyle(
        name='MetricValue',
        parent=styles['Normal'],
        fontSize=24,
        textColor=PRIMARY_COLOR,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='MetricLabel',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#6b7280'),
        alignment=TA_CENTER
    ))
    
    return styles

def create_header(styles, title, subtitle=None):
    """Crear encabezado del reporte"""
    elements = []
    
    # Línea decorativa superior
    elements.append(HRFlowable(width="100%", thickness=3, color=PRIMARY_COLOR, spaceAfter=20))
    
    # Título principal
    elements.append(Paragraph(f"📊 {title}", styles['MainTitle']))
    
    if subtitle:
        elements.append(Paragraph(subtitle, styles['Subtitle']))
    
    # Fecha de generación
    fecha = datetime.now().strftime("%d de %B de %Y, %H:%M hrs")
    elements.append(Paragraph(f"Generado el: {fecha}", styles['SmallText']))
    elements.append(Spacer(1, 20))
    
    return elements

def create_metrics_table(metrics_data):
    """Crear tabla de métricas estilizada"""
    # Estructura: [[valor, label], [valor, label], ...]
    data = [[
        Paragraph(f"<font size='20' color='#6366f1'><b>{m['value']}</b></font>", getSampleStyleSheet()['Normal']),
    ] for m in metrics_data]
    
    labels = [[
        Paragraph(f"<font size='9' color='#6b7280'>{m['label']}</font>", getSampleStyleSheet()['Normal']),
    ] for m in metrics_data]
    
    # Crear tabla horizontal de métricas
    values_row = [Paragraph(f"<font size='22' color='#6366f1'><b>{m['value']}</b></font>", getSampleStyleSheet()['Normal']) for m in metrics_data]
    labels_row = [Paragraph(f"<font size='9' color='#6b7280'>{m['label']}</font>", getSampleStyleSheet()['Normal']) for m in metrics_data]
    
    table = Table([values_row, labels_row], colWidths=[120] * len(metrics_data))
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), GRAY_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ('TOPPADDING', (0, 0), (-1, 0), 15),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 15),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    return table

def create_effectiveness_box(scheduled, actual, effectiveness, status):
    """Crear caja de efectividad con colores"""
    status_colors = {
        'adelantado': SUCCESS_COLOR,
        'en_tiempo': WARNING_COLOR,
        'atrasado': DANGER_COLOR
    }
    status_labels = {
        'adelantado': '🚀 Adelantado',
        'en_tiempo': '✅ En Tiempo',
        'atrasado': '⚠️ Atrasado'
    }
    
    color = status_colors.get(status, GRAY_DARK)
    label = status_labels.get(status, status)
    
    data = [
        [
            Paragraph(f"<font size='11' color='#6b7280'>Programado</font>", getSampleStyleSheet()['Normal']),
            Paragraph(f"<font size='11' color='#6b7280'>Real</font>", getSampleStyleSheet()['Normal']),
            Paragraph(f"<font size='11' color='#6b7280'>Efectividad</font>", getSampleStyleSheet()['Normal']),
            Paragraph(f"<font size='11' color='#6b7280'>Estado</font>", getSampleStyleSheet()['Normal']),
        ],
        [
            Paragraph(f"<font size='18' color='#374151'><b>{scheduled}%</b></font>", getSampleStyleSheet()['Normal']),
            Paragraph(f"<font size='18' color='#10b981'><b>{actual}%</b></font>", getSampleStyleSheet()['Normal']),
            Paragraph(f"<font size='18' color='#6366f1'><b>{effectiveness}%</b></font>", getSampleStyleSheet()['Normal']),
            Paragraph(f"<font size='12'><b>{label}</b></font>", getSampleStyleSheet()['Normal']),
        ],
    ]
    
    table = Table(data, colWidths=[120, 120, 120, 140])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), GRAY_LIGHT),
        ('BOX', (0, 0), (-1, -1), 2, PRIMARY_COLOR),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#e5e7eb')),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    
    return table

def create_tasks_table(tasks, styles):
    """Crear tabla de tareas"""
    if not tasks:
        return Paragraph("<i>No hay tareas en este proyecto</i>", styles['BodyText'])
    
    status_labels = {
        'todo': 'Por Hacer',
        'in_progress': 'En Progreso',
        'review': 'En Revisión',
        'done': 'Completado'
    }
    
    priority_labels = {
        'low': '🟢 Baja',
        'medium': '🟡 Media',
        'high': '🔴 Alta'
    }
    
    # Encabezados
    headers = ['Tarea', 'Estado', 'Prioridad', 'Progreso', 'Vencimiento']
    
    data = [headers]
    
    for task in tasks:
        status = status_labels.get(task.status, task.status)
        priority = priority_labels.get(task.priority, task.priority)
        progress = f"{task.progress or 0}%"
        due_date = task.due_date.strftime("%d/%m/%Y") if task.due_date else "Sin fecha"
        
        # Truncar título si es muy largo
        title = task.title[:40] + "..." if len(task.title) > 40 else task.title
        
        data.append([title, status, priority, progress, due_date])
    
    table = Table(data, colWidths=[180, 90, 80, 60, 80])
    
    # Estilos de la tabla
    style = TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        
        # Cuerpo
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        
        # Bordes
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        
        # Alternar colores de fila
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])
    
    # Alternar colores de filas
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f9fafb'))
    
    # Colorear estado según valor
    for i, task in enumerate(tasks, 1):
        if task.status == 'done':
            style.add('TEXTCOLOR', (1, i), (1, i), SUCCESS_COLOR)
        elif task.status == 'in_progress':
            style.add('TEXTCOLOR', (1, i), (1, i), colors.HexColor('#0891b2'))
        elif task.status == 'review':
            style.add('TEXTCOLOR', (1, i), (1, i), WARNING_COLOR)
    
    table.setStyle(style)
    return table

def create_stages_table(stages, styles):
    """Crear tabla de etapas"""
    if not stages:
        return Paragraph("<i>No hay etapas definidas</i>", styles['BodyText'])
    
    headers = ['Etapa', 'Peso', 'Programado', 'Real', 'Efectividad']
    data = [headers]
    
    for stage in stages:
        effectiveness = round((stage['actual_progress'] / stage['scheduled_progress'] * 100), 1) if stage['scheduled_progress'] > 0 else 100
        data.append([
            stage['name'],
            f"{stage['percentage']}%",
            f"{stage['scheduled_progress']}%",
            f"{stage['actual_progress']}%",
            f"{effectiveness}%"
        ])
    
    table = Table(data, colWidths=[180, 60, 80, 80, 80])
    
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
    ])
    
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f9fafb'))
    
    table.setStyle(style)
    return table

def generate_project_report(project, tasks, effectiveness_data, stages):
    """Generar reporte PDF para un proyecto específico"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )
    
    styles = create_styles()
    elements = []
    
    # Encabezado
    elements.extend(create_header(
        styles,
        "Reporte de Proyecto",
        f"Proyecto: {project.name}"
    ))
    
    # Información del proyecto
    elements.append(Paragraph("📋 Información General", styles['SectionTitle']))
    
    info_data = [
        ['Nombre del Proyecto:', project.name],
        ['Descripción:', project.description or 'Sin descripción'],
        ['Fecha de Inicio:', project.start_date.strftime("%d/%m/%Y") if project.start_date else 'No definida'],
        ['Fecha de Fin:', project.end_date.strftime("%d/%m/%Y") if project.end_date else 'No definida'],
        ['Total de Tareas:', str(len(tasks))],
    ]
    
    info_table = Table(info_data, colWidths=[150, 350])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), GRAY_DARK),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#374151')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Métricas de efectividad
    if effectiveness_data:
        elements.append(Paragraph("📈 Métricas de Efectividad", styles['SectionTitle']))
        metrics = effectiveness_data.get('metrics', {})
        elements.append(create_effectiveness_box(
            metrics.get('scheduled_progress', 0),
            metrics.get('actual_progress', 0),
            metrics.get('effectiveness', 0),
            metrics.get('status', 'en_tiempo')
        ))
        elements.append(Spacer(1, 20))
    
    # Etapas
    if stages:
        elements.append(Paragraph("🏗️ Etapas del Proyecto", styles['SectionTitle']))
        elements.append(create_stages_table(stages, styles))
        elements.append(Spacer(1, 20))
    
    # Resumen de tareas por estado
    elements.append(Paragraph("📊 Resumen de Tareas", styles['SectionTitle']))
    
    todo_count = len([t for t in tasks if t.status == 'todo'])
    in_progress_count = len([t for t in tasks if t.status == 'in_progress'])
    review_count = len([t for t in tasks if t.status == 'review'])
    done_count = len([t for t in tasks if t.status == 'done'])
    
    summary_metrics = [
        {'value': str(todo_count), 'label': 'Por Hacer'},
        {'value': str(in_progress_count), 'label': 'En Progreso'},
        {'value': str(review_count), 'label': 'En Revisión'},
        {'value': str(done_count), 'label': 'Completadas'},
    ]
    elements.append(create_metrics_table(summary_metrics))
    elements.append(Spacer(1, 20))
    
    # Lista de tareas
    elements.append(Paragraph("📝 Detalle de Tareas", styles['SectionTitle']))
    elements.append(create_tasks_table(tasks, styles))
    
    # Pie de página
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        f"<font size='8' color='#9ca3af'>ProyectOS - Sistema de Gestión de Proyectos de Obra | Generado automáticamente</font>",
        styles['SmallText']
    ))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_general_report(projects_data):
    """Generar reporte PDF general de todos los proyectos"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )
    
    styles = create_styles()
    elements = []
    
    # Encabezado
    elements.extend(create_header(
        styles,
        "Reporte General de Proyectos",
        f"Resumen ejecutivo de {len(projects_data)} proyecto(s)"
    ))
    
    # Resumen general
    elements.append(Paragraph("📊 Resumen Ejecutivo", styles['SectionTitle']))
    
    total_tasks = sum(p['total_tasks'] for p in projects_data)
    completed_tasks = sum(p['completed_tasks'] for p in projects_data)
    avg_effectiveness = sum(p['effectiveness'] for p in projects_data) / len(projects_data) if projects_data else 0
    
    summary_metrics = [
        {'value': str(len(projects_data)), 'label': 'Proyectos'},
        {'value': str(total_tasks), 'label': 'Total Tareas'},
        {'value': str(completed_tasks), 'label': 'Completadas'},
        {'value': f"{avg_effectiveness:.1f}%", 'label': 'Efectividad Prom.'},
    ]
    elements.append(create_metrics_table(summary_metrics))
    elements.append(Spacer(1, 30))
    
    # Tabla de proyectos
    elements.append(Paragraph("🏗️ Estado de Proyectos", styles['SectionTitle']))
    
    headers = ['Proyecto', 'Tareas', 'Progreso', 'Programado', 'Efectividad', 'Estado']
    data = [headers]
    
    for p in projects_data:
        status_icons = {
            'adelantado': '🚀',
            'en_tiempo': '✅',
            'atrasado': '⚠️'
        }
        status_icon = status_icons.get(p['status'], '')
        
        name = p['name'][:25] + "..." if len(p['name']) > 25 else p['name']
        
        data.append([
            name,
            f"{p['completed_tasks']}/{p['total_tasks']}",
            f"{p['actual_progress']}%",
            f"{p['scheduled_progress']}%",
            f"{p['effectiveness']}%",
            f"{status_icon} {p['status'].replace('_', ' ').title()}"
        ])
    
    table = Table(data, colWidths=[130, 60, 70, 70, 70, 90])
    
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
    ])
    
    # Colorear según estado
    for i, p in enumerate(projects_data, 1):
        if i % 2 == 0:
            style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f9fafb'))
        
        if p['status'] == 'adelantado':
            style.add('TEXTCOLOR', (-1, i), (-1, i), SUCCESS_COLOR)
        elif p['status'] == 'atrasado':
            style.add('TEXTCOLOR', (-1, i), (-1, i), DANGER_COLOR)
        else:
            style.add('TEXTCOLOR', (-1, i), (-1, i), WARNING_COLOR)
    
    table.setStyle(style)
    elements.append(table)
    elements.append(Spacer(1, 30))
    
    # Detalle por proyecto
    elements.append(Paragraph("📋 Detalle por Proyecto", styles['SectionTitle']))
    
    for p in projects_data:
        elements.append(Paragraph(f"<b>{p['name']}</b>", styles['SubsectionTitle']))
        
        detail = f"""
        <font size='9'>
        <b>Descripción:</b> {p.get('description', 'Sin descripción') or 'Sin descripción'}<br/>
        <b>Fecha Inicio:</b> {p.get('start_date', 'No definida')}<br/>
        <b>Fecha Fin:</b> {p.get('end_date', 'No definida')}<br/>
        <b>Tareas:</b> {p['completed_tasks']} de {p['total_tasks']} completadas<br/>
        <b>Efectividad:</b> {p['effectiveness']}%
        </font>
        """
        elements.append(Paragraph(detail, styles['BodyText']))
        elements.append(Spacer(1, 15))
    
    # Pie de página
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        f"<font size='8' color='#9ca3af'>ProyectOS - Sistema de Gestión de Proyectos de Obra | Reporte Mensual para Directiva</font>",
        styles['SmallText']
    ))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer
