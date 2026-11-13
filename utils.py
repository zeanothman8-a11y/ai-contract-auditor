import io
from docx import Document
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

def generate_word_report(report, filename):
    doc = Document()
    doc.add_heading("⚖️ Legal & Compliance Audit Report", 0)
    
    doc.add_heading("Executive Summary", level=1)
    doc.add_paragraph(report.contract_summary)
    
    doc.add_heading(f"Overall Risk Score: {report.overall_risk_score} / 100", level=1)
    
    doc.add_heading("Detected Risks & Alternative Wording", level=1)
    for idx, r in enumerate(report.detected_risks, 1):
        doc.add_heading(f"{idx}. {r.clause_title} (Risk: {r.risk_level} - Page {r.page_number})", level=2)
        doc.add_paragraph(f"Exact Quote: {r.exact_quote}")
        doc.add_paragraph(f"Explanation: {r.explanation}")
        doc.add_paragraph(f"Recommended Action: {r.recommended_action}")
        p = doc.add_paragraph()
        p.add_run("Alternative Wording to Propose: ").bold = True
        p.add_run(r.alternative_wording)
        doc.add_paragraph("-" * 40)
        
    if report.missing_protections:
        doc.add_heading("Missing Protective Clauses", level=1)
        for item in report.missing_protections:
            doc.add_paragraph(f"• {item}", style='List Bullet')
            
    if report.rfp_compliance_matrix:
        doc.add_heading("RFP Compliance Matrix", level=1)
        table = doc.add_table(rows=1, cols=4)
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Req #'
        hdr_cells[1].text = 'Client Requirement'
        hdr_cells[2].text = 'Status'
        hdr_cells[3].text = 'Bidder Response / Solution'
        
        for row in report.rfp_compliance_matrix:
            row_cells = table.add_row().cells
            row_cells[0].text = str(row.requirement_number)
            row_cells[1].text = str(row.client_requirement)
            row_cells[2].text = str(row.compliance_status)
            row_cells[3].text = str(row.bidder_response)
            
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def generate_excel_report(report):
    """Generates a styled multi-tab Excel workbook for RFP matrix and Detected Risks."""
    wb = Workbook()
    
    # تنسيقات موحدة احترافية
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=11)
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    wrap_alignment = Alignment(wrap_text=True, vertical="top")

    # 1. ورقة المخاطر المكتشفة (Detected Risks)
    ws_risks = wb.active
    ws_risks.title = "Detected Risks"
    
    risk_headers = ["Risk Level", "Page", "Clause Title", "Exact Quote", "Analysis", "Recommended Action", "Alternative Wording"]
    ws_risks.append(risk_headers)
    
    for cell in ws_risks[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for r in report.detected_risks:
        row_data = [
            r.risk_level,
            r.page_number,
            r.clause_title,
            r.exact_quote,
            r.explanation,
            r.recommended_action,
            r.alternative_wording
        ]
        ws_risks.append(row_data)
        
        # تلوين مستوى الخطورة
        curr_row = ws_risks.max_row
        risk_cell = ws_risks.cell(row=curr_row, column=1)
        if r.risk_level == "High":
            risk_cell.fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
            risk_cell.font = Font(color="9C0006", bold=True)
        elif r.risk_level == "Medium":
            risk_cell.fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
            risk_cell.font = Font(color="9C6500", bold=True)
        else:
            risk_cell.fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
            risk_cell.font = Font(color="006100", bold=True)

        for col_idx in range(1, 8):
            c = ws_risks.cell(row=curr_row, column=col_idx)
            c.border = thin_border
            c.alignment = wrap_alignment

    # ضبط عرض الأعمدة
    risk_widths = [14, 8, 25, 35, 40, 35, 45]
    for idx, width in enumerate(risk_widths, 1):
        ws_risks.column_dimensions[chr(64 + idx)].width = width

    # 2. ورقة مصفوفة مطابقة الشروط (RFP Compliance Matrix) إن وجدت
    if report.rfp_compliance_matrix:
        ws_rfp = wb.create_sheet(title="RFP Compliance Matrix")
        rfp_headers = ["Req #", "Client Requirement", "Compliance Status", "Proposed Bidder Response"]
        ws_rfp.append(rfp_headers)
        
        for cell in ws_rfp[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            
        for m in report.rfp_compliance_matrix:
            ws_rfp.append([
                m.requirement_number,
                m.client_requirement,
                m.compliance_status,
                m.bidder_response
            ])
            curr_row = ws_rfp.max_row
            status_cell = ws_rfp.cell(row=curr_row, column=3)
            if m.compliance_status == "Compliant":
                status_cell.fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
                status_cell.font = Font(color="006100", bold=True)
            elif m.compliance_status == "Non-Compliant":
                status_cell.fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
                status_cell.font = Font(color="9C0006", bold=True)
            else:
                status_cell.fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
                status_cell.font = Font(color="9C6500", bold=True)
                
            for col_idx in range(1, 5):
                c = ws_rfp.cell(row=curr_row, column=col_idx)
                c.border = thin_border
                c.alignment = wrap_alignment

        rfp_widths = [12, 45, 22, 55]
        for idx, width in enumerate(rfp_widths, 1):
            ws_rfp.column_dimensions[chr(64 + idx)].width = width

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
    
