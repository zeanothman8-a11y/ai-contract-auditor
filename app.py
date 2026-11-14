import streamlit as st
import pandas as pd
from auditor import audit_contract, compare_contracts
from utils import generate_word_report, generate_excel_report

st.set_page_config(page_title="Verilogix AI - Contract & RFP Auditor", page_icon="⚖️", layout="wide")

st.title("⚖️ Verilogix AI — Legal & RFP Compliance Engine")
st.markdown("Automated risk extraction, **RFP compliance matrices, negotiation drafting & redline version comparison**.")

with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Enter Gemini API Key", type="password", help="Get a free API key from Google AI Studio")
    
    jurisdiction = st.selectbox(
        "Governing Law / Jurisdiction",
        [
            "General International Commercial Law",
            "Saudi Arabian Law (KSA)",
            "UAE Law",
            "Egyptian Law",
            "Syrian Commercial Law",
            "Common Law / UK / US"
        ]
    )
    
    st.divider()
    st.subheader("🛡️ Enterprise Security & Playbook")
    enable_pii_masking = st.checkbox("Enable PII Anonymization", value=True, help="Masks sensitive names and emails locally before analysis")
    
    company_playbook = st.text_area(
        "Company Legal Playbook Rules",
        placeholder="e.g., Liability capped at contract value. Payment terms must be >= 45 days. No unilateral termination without 60 days notice.",
        height=120
    )
    
    custom_rules = st.text_area(
        "Custom Compliance Rules (Optional)",
        placeholder="e.g., Special project constraints.",
        height=100
    )
    
    custom_rules = st.text_area(
        "Custom Compliance Rules (Optional)",
        placeholder="e.g., Payment terms must not exceed 30 days.",
        height=150
    )

if "audit_reports" not in st.session_state:
    st.session_state.audit_reports = {}
if "comparison_report" not in st.session_state:
    st.session_state.comparison_report = None

# تقسيم التطبيق إلى تبويبين رئيسيين
tab1, tab2 = st.tabs(["🔍 Single & Batch Contract Audit", "⚖️ Version Comparison (Redlining)"])

# ==========================================
# التبويب الأول: التدقيق الفردي والجماعي + لوحة المخاطر
# ==========================================
with tab1:
    uploaded_files = st.file_uploader("Upload Contract or RFP Documents (PDF)", type=["pdf"], accept_multiple_files=True)

    if uploaded_files and st.button("🚀 Run Compliance Audit", type="primary"):
        if not api_key:
            st.error("Please enter your API key in the sidebar first.")
        else:
            for uploaded_file in uploaded_files:
                with st.spinner(f"جاري تحليل المستند وتوليد مصفوفة الامتثال لـ {uploaded_file.name}..."):
                    try:
                        pdf_bytes = uploaded_file.read()
                        report = audit_contract(pdf_bytes, api_key, custom_rules, jurisdiction, company_playbook, enable_pii_masking)
                        st.session_state.audit_reports[uploaded_file.name] = report
                    except Exception as e:
                        st.error(f"Audit failed for {uploaded_file.name}: {str(e)}")

    # لوحة تحكم سريعة عند وجود أكثر من مستند (Portfolio Overview)
    if len(st.session_state.audit_reports) > 1:
        st.subheader("📊 Portfolio Risk Overview (ملخص العقود المرفوعة)")
        summary_rows = []
        for fname, rep in st.session_state.audit_reports.items():
            summary_rows.append({
                "Document Name": fname,
                "Type": rep.document_type,
                "Risk Score (/100)": rep.overall_risk_score,
                "Total Risks": len(rep.detected_risks),
                "High Risks": sum(1 for r in rep.detected_risks if r.risk_level == "High")
            })
        summary_df = pd.DataFrame(summary_rows).sort_values(by="Risk Score (/100)", ascending=False)
        st.dataframe(summary_df, use_container_width=True)

    # عرض تفاصيل كل تقرير
    if st.session_state.audit_reports:
        for file_name, report in st.session_state.audit_reports.items():
            st.markdown(f"--- \n### 📄 تقرير فحص المستند: `{file_name}`")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Overall Risk Score", f"{report.overall_risk_score} / 100")
            col2.metric("Detected Risks", len(report.detected_risks))
            col3.metric("Document Type", report.document_type)
            
            st.subheader("📋 Executive Summary")
            st.info(report.contract_summary)
            
            # أزرار تحميل التقارير (Word و Excel)
            dl_col1, dl_col2 = st.columns(2)
            with dl_col1:
                docx_buffer = generate_word_report(report, file_name)
                st.download_button(
                    label="📥 Download Word Report (.docx)",
                    data=docx_buffer,
                    file_name=f"audit_report_{file_name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"docx_{file_name}",
                    use_container_width=True
                )
            with dl_col2:
                excel_buffer = generate_excel_report(report)
                st.download_button(
                    label="📊 Download Excel Matrix (.xlsx)",
                    data=excel_buffer,
                    file_name=f"compliance_matrix_{file_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"xlsx_{file_name}",
                    use_container_width=True
                )
            
            st.subheader("🚨 Detected Risk & Compliance Clauses")
            if report.detected_risks:
                risks_data = [{
                    "Risk Level": r.risk_level,
                    "Page": r.page_number,
                    "Clause": r.clause_title,
                    "Exact Quote": r.exact_quote,
                    "Analysis": r.explanation,
                    "Recommended Action": r.recommended_action,
                    "Alternative Wording": r.alternative_wording
                } for r in report.detected_risks]
                st.dataframe(pd.DataFrame(risks_data), use_container_width=True)
            else:
                st.success("No major risk clauses detected!")

            if report.rfp_compliance_matrix:
                st.subheader("📊 RFP Compliance Matrix (جدول مطابقة الشروط)")
                matrix_data = [{
                    "Req #": m.requirement_number,
                    "Client Requirement": m.client_requirement,
                    "Status": m.compliance_status,
                    "Bidder Response": m.bidder_response
                } for m in report.rfp_compliance_matrix]
                st.dataframe(pd.DataFrame(matrix_data), use_container_width=True)

            if report.missing_protections:
                st.subheader("🛡️ Missing Protective Clauses")
                for item in report.missing_protections:
                    st.warning(f"• {item}")

            if report.negotiation_email_draft:
                st.subheader("✉️ Negotiation Email Draft (مسودة إيميل التفاوض)")
                st.code(report.negotiation_email_draft, language="markdown")

# ==========================================
# التبويب الثاني: مقارنة النسخ (Original vs Revised)
# ==========================================
with tab2:
    st.subheader("🔄 Compare Original Draft vs. Revised Draft")
    st.markdown("ارفع النسخة الأولى من العقد والنسخة المعدلة بعد التفاوض للتحقق من التزام الطرف الآخر بالتعديلات واكتشاف أي بنود مخفية جديدة.")
    
    c_col1, c_col2 = st.columns(2)
    with c_col1:
        orig_file = st.file_uploader("1️⃣ Original Contract (PDF)", type=["pdf"], key="orig_pdf")
    with c_col2:
        rev_file = st.file_uploader("2️⃣ Revised Contract (PDF)", type=["pdf"], key="rev_pdf")
        
    if orig_file and rev_file and st.button("⚖️ Compare Versions", type="primary"):
        if not api_key:
            st.error("Please enter your API key in the sidebar first.")
        else:
            with st.spinner("جاري مقارنة النسختين وتحليل الفروقات القانونية والمالية..."):
                try:
                    comp_report = compare_contracts(orig_file.read(), rev_file.read(), api_key, jurisdiction)
                    st.session_state.comparison_report = comp_report
                except Exception as e:
                    st.error(f"Comparison failed: {str(e)}")

    if st.session_state.comparison_report:
        comp = st.session_state.comparison_report
        st.markdown("---")
        m1, m2 = st.columns(2)
        m1.metric("Safety Improvement Score", f"{comp.overall_improvement_score} / 100")
        m2.metric("Final Legal Verdict", comp.final_recommendation)
        
        st.info(comp.executive_comparison_summary)
        
        st.subheader("📝 Detailed Redline Changes Breakdown")
        changes_data = [{
            "Clause Topic": ch.clause_topic,
            "Status": ch.change_status,
            "Original Version": ch.original_text_summary,
            "Revised Version": ch.revised_text_summary,
            "Risk Impact": ch.risk_impact
        } for ch in comp.changes_breakdown]
        st.dataframe(pd.DataFrame(changes_data), use_container_width=True)
        
