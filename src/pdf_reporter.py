def generate_finops_report(self, audit_results: dict, client_name: str = "Cliente"):
    """Genera reporte PDF mostrando solo servicios en uso"""
    filename = f"Auditoria_FinOps_{client_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Header
    title = Paragraph(f"AUDITORÍA FINOPS LATAM - {client_name}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Sección de servicios EN USO (siempre visible)
    service_discovery = audit_results['service_discovery']
    self.add_services_in_use_section(story, service_discovery['services_in_use'], styles)
    
    # Sección de servicios NO DETECTADOS (solo si existen, en anexos)
    if service_discovery['services_not_detected']['total_services'] > 0:
        self.add_undetected_services_annex(story, service_discovery['services_not_detected'], styles)
    
    # Resto del reporte (análisis de costos, recomendaciones, etc.)
    self.add_cost_analysis_section(story, audit_results['cost_analysis'], styles)
    self.add_recommendations_section(story, audit_results, styles)
    
    doc.build(story)
    return filename

def add_services_in_use_section(self, story, services_in_use: Dict, styles):
    """Agrega sección de servicios EN USO al PDF"""
    story.append(Paragraph("🏗️ INFRAESTRUCTURA DETECTADA", styles['Heading2']))
    
    # Resumen
    summary_data = [
        ['Servicios en Uso', 'Total Recursos', 'Cobertura'],
        [
            str(services_in_use['total_services']),
            str(services_in_use['total_resources']),
            f"{services_in_use['coverage_percentage']}%"
        ]
    ]
    
    summary_table = Table(summary_data)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27AE60')),  # Verde para "en uso"
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#D5F5E3')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 12))
    
    # Tabla detallada de servicios EN USO
    if services_in_use['breakdown']:
        story.append(Paragraph("Servicios con Recursos Activos:", styles['Heading3']))
        
        services_data = [['Servicio AWS', 'Cantidad de Recursos', 'Ejemplos']]
        for service, details in services_in_use['breakdown'].items():
            if details['resource_count'] > 0:  # Solo servicios con recursos
                examples = ', '.join([r.get('id', r.get('name', 'N/A')) for r in details['resources'][:2]])
                services_data.append([
                    service.upper(),
                    str(details['resource_count']),
                    examples[:40] + '...' if len(examples) > 40 else examples
                ])
        
        services_table = Table(services_data, colWidths=[120, 80, 200])
        services_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F7F7F7')),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        story.append(services_table)
    else:
        story.append(Paragraph("No se detectaron servicios con recursos activos.", styles['Normal']))
    
    story.append(Spacer(1, 12))

def add_undetected_services_annex(self, story, undetected_services: Dict, styles):
    """Agrega anexo con servicios NO DETECTADOS"""
    story.append(PageBreak())
    story.append(Paragraph("📋 ANEXO: SERVICIOS NO DETECTADOS", styles['Heading2']))
    story.append(Paragraph(undetected_services['note'], styles['Italic']))
    story.append(Spacer(1, 12))
    
    # Lista de servicios no detectados (agrupados)
    services_list = undetected_services['services']
    chunks = [services_list[i:i + 4] for i in range(0, len(services_list), 4)]
    
    for chunk in chunks:
        services_data = [['Servicios AWS Sin Recursos Detectados']]
        for service in chunk:
            services_data.append([service.upper()])
        
        services_table = Table(services_data)
        services_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E74C3C')),  # Rojo para "no detectados"
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FDEDEC')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)
        ]))
        story.append(services_table)
        story.append(Spacer(1, 6))