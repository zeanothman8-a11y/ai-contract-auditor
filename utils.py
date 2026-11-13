import io
from docx import Document

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
  
