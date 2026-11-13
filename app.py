import streamlit as st
import pandas as pd
from auditor import audit_contract
from utils import generate_word_report

st.set_page_config(page_title="Verilogix AI - Contract & RFP Auditor", page_icon="⚖️", layout="wide")

st.title("⚖️ AI Contract & RFP Compliance Auditor")
st.markdown("Automated legal & compliance risk extraction engine with **page citations, alternative clauses & RFP matrix**.")

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
    
    custom_rules = st.text_area(
        "Custom Compliance Rules (Optional)",
        placeholder="e.g., Payment terms must not exceed 30 days.",
        height=150
    )

uploaded_files = st.file_uploader("Upload Contract or RFP Documents (PDF)", type=["pdf"], accept_multiple_files=True)

# استخدام session_state لحفظ التقارير حتى لا تضيع عند إعادة تحميل الصفحة
if "audit_reports" not in st.session_state:
    st.session_state.audit_reports = {}

if uploaded_files and st.button("🚀 Run Compliance Audit", type="primary"):
    if not api_key:
        st.error("Please enter your API key in the sidebar first.")
    else:
        for uploaded_file in uploaded_files:
            with st.spinner(f"جاري تحليل المستند وتوليد مصفوفة الامتثال لـ {uploaded_file.name}..."):
                try:
                    pdf_bytes = uploaded_file.read()
                    report = audit_contract(pdf_bytes, api_key, custom_rules, jurisdiction)
                    
                    # حفظ التقرير في الذاكرة المؤقتة للجلسة
                    st.session_state.audit_reports[uploaded_file.name] = report
                            
                except Exception as e:
                    st.error(f"Audit failed for {uploaded_file.name}: {str(e)}")

# عرض التقارير المحفوظة في الذاكرة (تظهر مباشرة دون أن تختفي عند الضغط على الأزرار)
if st.session_state.audit_reports:
    for file_name, report in st.session_state.audit_reports.items():
        st.markdown(f"--- \n### 📄 تقرير فحص المستند: `{file_name}`")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Overall Risk Score", f"{report.overall_risk_score} / 100")
        col2.metric("Detected Risks", len(report.detected_risks))
        col3.metric("Document Type", report.document_type)
        
        st.subheader("📋 Executive Summary")
        st.info(report.contract_summary)
        
        # زر تحميل تقرير Word الاحترافي (الآن يعمل بسلاسة بفضل الـ session_state)
        docx_buffer = generate_word_report(report, file_name)
        st.download_button(
            label=f"📥 Download Full Professional Report (Word .docx) - {file_name}",
            data=docx_buffer,
            file_name=f"audit_report_{file_name}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key=f"docx_{file_name}"
        )
        
        st.subheader("🚨 Detected Risk & Compliance Clauses")
        if report.detected_risks:
            risks_data = []
            for r in report.detected_risks:
                risks_data.append({
                    "Risk Level": r.risk_level,
                    "Page": r.page_number,
                    "Clause": r.clause_title,
                    "Exact Quote": r.exact_quote,
                    "Analysis": r.explanation,
                    "Recommended Action": r.recommended_action,
                    "Alternative Wording": r.alternative_wording
                })
            df = pd.DataFrame(risks_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.success("No major risk clauses detected!")

        if report.rfp_compliance_matrix:
            st.subheader("📊 RFP Compliance Matrix (جدول مطابقة الشروط)")
            matrix_data = []
            for m in report.rfp_compliance_matrix:
                matrix_data.append({
                    "Req #": m.requirement_number,
                    "Client Requirement": m.client_requirement,
                    "Status": m.compliance_status,
                    "Bidder Response": m.bidder_response
                })
            matrix_df = pd.DataFrame(matrix_data)
            st.dataframe(matrix_df, use_container_width=True)

        if report.missing_protections:
            st.subheader("🛡️ Missing Protective Clauses")
            for item in report.missing_protections:
                st.warning(f"• {item}")
                                  
