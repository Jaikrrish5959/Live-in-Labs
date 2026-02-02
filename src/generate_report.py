#!/usr/bin/env python3
"""
Generate PDF Report for Dual-Ring LoRa Perimeter Simulation
"""

import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image, PageBreak, ListFlowable, ListItem
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
except ImportError:
    print("Installing reportlab...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image, PageBreak, ListFlowable, ListItem
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

import config


def create_report(output_path: str):
    """Generate the PDF report."""
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='Title_Custom',
        parent=styles['Title'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.HexColor('#1a365d')
    ))
    styles.add(ParagraphStyle(
        name='Heading1_Custom',
        parent=styles['Heading1'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#2c5282')
    ))
    styles.add(ParagraphStyle(
        name='Heading2_Custom',
        parent=styles['Heading2'],
        fontSize=13,
        spaceBefore=15,
        spaceAfter=8,
        textColor=colors.HexColor('#2b6cb0')
    ))
    styles.add(ParagraphStyle(
        name='Body_Custom',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        alignment=TA_JUSTIFY
    ))
    
    story = []
    
    # Title
    story.append(Paragraph("Dual-Ring LoRa Perimeter Simulation", styles['Title_Custom']))
    story.append(Paragraph("Agent-Based Networking Validation Report", styles['Heading2']))
    story.append(Spacer(1, 20))
    
    # Date
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 30))
    
    # Executive Summary
    story.append(Paragraph("Executive Summary", styles['Heading1_Custom']))
    summary_text = """
    This report presents the results of a discrete-event simulation validating a dual-ring 
    LoRa perimeter sensing network. The simulation uses an agent-based model where each 
    perimeter node operates independently with PIR and thermal sensors, AI-based confidence 
    scoring, and P2P cross-verification for uncertain detections.
    """
    story.append(Paragraph(summary_text.strip(), styles['Body_Custom']))
    story.append(Spacer(1, 15))
    
    # Key Findings Table
    story.append(Paragraph("Key Findings", styles['Heading2_Custom']))
    
    findings_data = [
        ['Metric', 'Cascaded + Verification', 'PIR-Only Baseline', 'Improvement'],
        ['Detection Rate', '98.98%', '88.47%', '+10.5%'],
        ['False Positive Rate', '9.50%', '12.91%', '-3.4%'],
        ['Mean Latency', '0.292 s', 'N/A', 'Acceptable'],
        ['P2P Messages/Event', '1.46', 'N/A', 'Minimal overhead'],
    ]
    
    findings_table = Table(findings_data, colWidths=[3.5*cm, 4*cm, 4*cm, 3*cm])
    findings_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#edf2f7')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e0')),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    story.append(findings_table)
    story.append(Spacer(1, 25))
    
    # System Architecture
    story.append(Paragraph("1. System Architecture", styles['Heading1_Custom']))
    
    arch_text = """
    The simulated system consists of 16 perimeter nodes arranged in a dual-ring topology:
    """
    story.append(Paragraph(arch_text.strip(), styles['Body_Custom']))
    
    arch_data = [
        ['Parameter', 'Outer Ring', 'Inner Ring'],
        ['Node Count', '8', '8'],
        ['Radius', f'{config.OUTER_RING_RADIUS} m', f'{config.INNER_RING_RADIUS} m'],
        ['Angular Spacing', f'{config.OUTER_RING_SPACING_DEG}°', f'{config.OUTER_RING_SPACING_DEG}°'],
        ['Angular Offset', '0°', f'{config.INNER_RING_OFFSET_DEG}°'],
    ]
    
    arch_table = Table(arch_data, colWidths=[4.5*cm, 4*cm, 4*cm])
    arch_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#a0aec0')),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(arch_table)
    story.append(Spacer(1, 20))
    
    # Decision Logic
    story.append(Paragraph("2. Agent Decision Logic", styles['Heading1_Custom']))
    
    logic_text = f"""
    Each node follows a rule-based decision policy based on AI confidence scores:
    <br/><br/>
    <b>• High Confidence (≥ {config.CONFIRM_THRESHOLD}):</b> Immediate confirmation, send LoRaWAN uplink<br/>
    <b>• Medium Confidence ({config.VERIFY_THRESHOLD} - {config.CONFIRM_THRESHOLD}):</b> Request P2P verification from neighbors<br/>
    <b>• Low Confidence (&lt; {config.VERIFY_THRESHOLD}):</b> Ignore event<br/>
    <br/>
    Cross-verification timeout: {config.P2P_VERIFICATION_TIMEOUT} seconds
    """
    story.append(Paragraph(logic_text, styles['Body_Custom']))
    story.append(Spacer(1, 20))
    
    # Simulation Parameters
    story.append(Paragraph("3. Simulation Parameters", styles['Heading1_Custom']))
    
    params_data = [
        ['Parameter', 'Value'],
        ['Random Seed', str(config.RANDOM_SEED)],
        ['Total Events', str(config.EVENT_TARGET_COUNT)],
        ['Intruder Event Probability', f'{config.INTRUDER_EVENT_PROB:.0%}'],
        ['P2P Communication Range', f'{config.P2P_RANGE} m'],
        ['Sensor Detection Range', f'{config.SENSOR_RANGE} m'],
        ['Packet Loss Probability', f'{config.PACKET_LOSS_PROB:.0%}'],
        ['Gateway Up Duration (mean)', f'{config.GATEWAY_UP_DURATION_MEAN} s'],
        ['Gateway Down Duration (mean)', f'{config.GATEWAY_DOWN_DURATION_MEAN} s'],
    ]
    
    params_table = Table(params_data, colWidths=[6*cm, 5*cm])
    params_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#a0aec0')),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(params_table)
    story.append(Spacer(1, 25))
    
    # Results
    story.append(Paragraph("4. Simulation Results", styles['Heading1_Custom']))
    
    results_text = """
    The simulation generated 1000 events (295 intruders, 705 noise) and evaluated the 
    detection performance of the cascaded verification system against a PIR-only baseline.
    """
    story.append(Paragraph(results_text.strip(), styles['Body_Custom']))
    story.append(Spacer(1, 15))
    
    # Results table
    results_data = [
        ['Metric', 'Value'],
        ['Total Events', '1000'],
        ['Intruder Events', '295'],
        ['Noise Events', '705'],
        ['Unique Detections', '359'],
        ['True Positives', '292'],
        ['False Positives', '67'],
        ['Detection Rate', '98.98%'],
        ['False Positive Rate', '9.50%'],
        ['Mean Latency', '0.292 s'],
        ['Max Latency', '3.000 s'],
        ['Detections During Outage', '29 (8.08%)'],
    ]
    
    results_table = Table(results_data, colWidths=[5*cm, 5*cm])
    results_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#276749')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#68d391')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0fff4')),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(results_table)
    story.append(PageBreak())
    
    # Plots
    story.append(Paragraph("5. Visualizations", styles['Heading1_Custom']))
    
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    
    # Latency CDF
    latency_path = os.path.join(output_dir, "latency_cdf.png")
    if os.path.exists(latency_path):
        story.append(Paragraph("5.1 Detection Latency (CDF)", styles['Heading2_Custom']))
        story.append(Image(latency_path, width=14*cm, height=9*cm))
        story.append(Paragraph(
            "The latency CDF shows detection confirmation times. Most detections complete under 0.5 seconds, "
            "with worst-case delays reaching the 3-second P2P verification timeout.",
            styles['Body_Custom']
        ))
        story.append(Spacer(1, 15))
    
    # P2P Overhead
    p2p_path = os.path.join(output_dir, "p2p_overhead.png")
    if os.path.exists(p2p_path):
        story.append(Paragraph("5.2 P2P Message Overhead", styles['Heading2_Custom']))
        story.append(Image(p2p_path, width=14*cm, height=9*cm))
        story.append(Paragraph(
            "P2P verification messages are minimal, averaging 1.46 messages per verified event. "
            "This demonstrates efficient use of the cross-verification mechanism.",
            styles['Body_Custom']
        ))
        story.append(Spacer(1, 15))
    
    # Detection Comparison
    comp_path = os.path.join(output_dir, "detection_comparison.png")
    if os.path.exists(comp_path):
        story.append(Paragraph("5.3 Detection Performance", styles['Heading2_Custom']))
        story.append(Image(comp_path, width=14*cm, height=9*cm))
        story.append(Spacer(1, 20))
    
    # Conclusions
    story.append(Paragraph("6. Conclusions", styles['Heading1_Custom']))
    
    conclusions = """
    <b>1. Cross-verification is effective:</b> Requiring neighbors to independently confirm 
    at high confidence significantly reduces false positive propagation while maintaining 
    high detection rates.<br/><br/>
    
    <b>2. Latency is acceptable:</b> Mean detection latency of 0.29 seconds is well within 
    operational requirements, with worst-case 3-second delays only for edge verification cases.<br/><br/>
    
    <b>3. Gateway outage resilience:</b> 8% of detections occurred during gateway downtime, 
    demonstrating the value of the P2P verification fallback mechanism.<br/><br/>
    
    <b>4. Minimal communication overhead:</b> Average of 1.5 P2P messages per verified event 
    indicates efficient resource utilization.<br/><br/>
    
    <b>5. Dual-ring topology validated:</b> The system achieves a 10.5% improvement in detection 
    rate and 3.4% reduction in false positives compared to PIR-only baseline.
    """
    story.append(Paragraph(conclusions, styles['Body_Custom']))
    
    # Build PDF
    doc.build(story)
    print(f"Report generated: {output_path}")


if __name__ == "__main__":
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "simulation_report.pdf")
    create_report(output_path)
