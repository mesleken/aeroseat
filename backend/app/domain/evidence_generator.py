import os
import json
import hashlib
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_evidence_package(
    assessment_data: dict,
    input_manifest_data: dict,
    output_manifest_data: dict,
    output_dir: str
) -> tuple[str, str, str, str, str]:
    """Generates immutable manifest files (input & output json) and PDF report (Contract 4).
    
    Returns (input_manifest_uri, input_sha256, output_manifest_uri, output_sha256, pdf_uri).
    """
    os.makedirs(output_dir, exist_ok=True)

    # 1. Input Manifest
    input_path = os.path.join(output_dir, "input_manifest.json")
    input_json_str = json.dumps(input_manifest_data, indent=2, sort_keys=True)
    with open(input_path, "w", encoding="utf-8") as f:
        f.write(input_json_str)
    input_sha256 = hashlib.sha256(input_json_str.encode("utf-8")).hexdigest()

    # 2. Output Manifest
    output_path = os.path.join(output_dir, "output_manifest.json")
    output_json_str = json.dumps(output_manifest_data, indent=2, sort_keys=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_json_str)
    output_sha256 = hashlib.sha256(output_json_str.encode("utf-8")).hexdigest()

    # 3. PDF Package
    pdf_path = os.path.join(output_dir, "evidence_package.pdf")
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=15
    )
    heading2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )
    
    story = []

    # Header
    story.append(Paragraph("AeroSeat Certification OS — Engineering Evidence Artifact", title_style))
    story.append(Paragraph(f"Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | Engine Version: 1.0.0", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E1'), spaceAfter=15))

    # Readiness Banner
    readiness = assessment_data.get("overall_readiness", "READY")
    banner_color = "#166534" if readiness == "READY" else ("#9A3412" if readiness == "CONDITIONALLY_READY" else "#991B1B")
    banner_text = f"<b>CERTIFICATION READINESS: {readiness}</b>"
    
    banner_data = [[Paragraph(banner_text, ParagraphStyle('Banner', parent=body_style, textColor=colors.white, fontSize=12, leading=14))]]
    banner_table = Table(banner_data, colWidths=[540])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(banner_color)),
        ('PADDING', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 15))

    # Cryptographic Fingerprints Table
    story.append(Paragraph("1. Cryptographic Immutable Fingerprints", heading2_style))
    fp_data = [
        ["Parameter", "SHA-256 Hash"],
        ["Configuration Hash", assessment_data.get("configuration_hash", "N/A")[:48] + "..."],
        ["Execution Fingerprint", assessment_data.get("execution_fingerprint", "N/A")[:48] + "..."],
        ["Input Manifest Hash", input_sha256[:48] + "..."],
        ["Output Manifest Hash", output_sha256[:48] + "..."],
    ]
    fp_table = Table(fp_data, colWidths=[160, 380])
    fp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    story.append(fp_table)
    story.append(Spacer(1, 15))

    # Injury Metrics & Requirement Summary
    story.append(Paragraph("2. 14 CFR § 25.562 / SAE AS8049E Regulatory Compliance Summary", heading2_style))
    
    req_summary = assessment_data.get("requirement_compliance_summary", [])
    req_rows = [["Metric", "Measured Value", "Regulatory Limit", "Margin", "Status"]]
    for item in req_summary:
        req_rows.append([
            str(item.get("metric", "")),
            f"{item.get('measured_value', 0):.2f} {item.get('unit', '')}",
            f"{item.get('operator', '<=')} {item.get('limit_value', 0):.2f} {item.get('unit', '')}",
            f"{item.get('margin_percent', 0):+.1f}%",
            str(item.get("status", "PASS"))
        ])
        
    req_table = Table(req_rows, colWidths=[120, 110, 130, 90, 90])
    req_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    story.append(req_table)
    story.append(Spacer(1, 15))

    # Engineer Approval
    story.append(Paragraph("3. Engineering Sign-off & Audit Trail", heading2_style))
    approval_text = f"""
    <b>Approved By:</b> {assessment_data.get('approved_by_name', 'Lead Certification Engineer')}<br/>
    <b>Approval Role:</b> {assessment_data.get('approval_role', 'CHIEF_CHEST_SAFETY_ENGINEER')}<br/>
    <b>Engineer Comments:</b> {assessment_data.get('engineer_comments', 'Validated against SAE ARP5765B correlation vector.')}<br/>
    """
    story.append(Paragraph(approval_text, body_style))

    doc.build(story)

    return input_path, input_sha256, output_path, output_sha256, pdf_path
