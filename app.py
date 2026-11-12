import streamlit as st
import pandas as pd
from auditor import audit_contract

st.set_page_config(page_title="Verilogix AI - Contract & RFP Auditor", page_icon="⚖️", layout="wide")

st.title("⚖️ AI Contract & RFP Compliance Auditor")
st.markdown("Automated legal & compliance risk extraction engine with **page-level citations**.")

with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Enter Gemini API Key", type="password", help="Get a free API key from Google AI Studio")
    st.markdown("---")
    custom_rules = st.text_area(
        "Custom Compliance Rules (Optional)",
        placeholder="e.g., Payment terms must not exceed 30 days. Liability cap must not exceed contract value.",
        height=150
    )

uploaded_file = st.file_uploader("Upload Contract or RFP Document (PDF)", type=["pdf"])

if uploaded_file and st.button("🚀 Run Compliance Audit", type="primary"):
    if not api_key:
        st.error("Please enter your API key in the sidebar first.")
    else:
        with st.spinner("Analyzing pages, checking compliance rules, and validating clauses..."):
            try:
                pdf_bytes = uploaded_file.read()
                report = audit_contract(pdf_bytes, api_key, custom_rules)
                
                # Top Metrics
                col1, col2, col3 = st.columns(3)
                col1.metric("Overall Risk Score", f"{report.overall_risk_score} / 100")
                col2.metric("Detected Risks", len(report.detected_risks))
                col3.metric("Missing Protections", len(report.missing_protections))
                
                st.subheader("📋 Executive Summary")
                st.info(report.contract_summary)
                
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
                            "Recommended Action": r.recommended_action
                        })
                    df = pd.DataFrame(risks_data)
                    st.dataframe(df, use_container_width=True)
                    
                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="📥 Download Full Audit Report (CSV)",
                        data=csv,
                        file_name="contract_audit_report.csv",
                        mime="text/csv"
                    )
                else:
                    st.success("No major risk clauses detected!")

                if report.missing_protections:
                    st.subheader("🛡️ Missing Protective Clauses")
                    for item in report.missing_protections:
                        st.warning(f"• {item}")
                        
            except Exception as e:
                st.error(f"Audit failed: {str(e)}")
              
