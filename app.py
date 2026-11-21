import hashlib
import pandas as pd
import streamlit as st
from auditor import (
    analyze_negotiation_timeline,
    ask_contract_question,
    audit_contract,
    compare_contracts,
    extract_text_with_pages,
)
from utils import generate_excel_report, generate_word_report

st.set_page_config(
    page_title="Verilogix AI - Contract & RFP Auditor",
    page_icon="⚖️",
    layout="wide",
)

st.title("⚖️ Verilogix AI — Legal & RFP Compliance Engine")
st.markdown(
    "Automated risk extraction, **RFP compliance matrices, negotiation drafting & redline version comparison**."
)


@st.cache_data(show_spinner=False)
def _cached_word_report(report_json: str, filename: str) -> bytes:
    from schemas import ContractAuditReport

    parsed = ContractAuditReport.model_validate_json(report_json)
    return generate_word_report(parsed, filename).getvalue()


@st.cache_data(show_spinner=False)
def _cached_excel_report(report_json: str) -> bytes:
    from schemas import ContractAuditReport

    parsed = ContractAuditReport.model_validate_json(report_json)
    return generate_excel_report(parsed).getvalue()


with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input(
        "Enter Gemini API Key",
        type="password",
        help="Get an API key from Google AI Studio",
    )

    jurisdiction = st.selectbox(
        "Governing Law / Jurisdiction",
        [
            "General International Commercial Law",
            "Saudi Arabian Law (KSA)",
            "UAE Law",
            "Egyptian Law",
            "Syrian Commercial Law",
            "Common Law / UK / US",
        ],
    )

    output_language = st.selectbox(
        "Output Language",
        ["English", "Arabic", "Match Document Language"],
    )

    st.divider()
    st.subheader("🛡️ Enterprise Security & Playbook")
    enable_pii_masking = st.checkbox(
        "Enable PII Anonymization",
        value=True,
        help="Masks emails, phone numbers, reference IDs, and custom terms locally before text analysis",
    )
    custom_pii_raw = st.text_input(
        "Additional Terms / Names to Mask (comma-separated)",
        placeholder="e.g., Acme Corp, John Doe",
    )

    company_playbook = st.text_area(
        "Company Legal Playbook Rules",
        placeholder="e.g., Liability capped at contract value. Payment terms must be >= 45 days. No unilateral termination without 60 days notice.",
        height=120,
    )
    custom_rules = st.text_area(
        "Custom Compliance Rules (Optional)",
        placeholder="e.g., Payment terms must not exceed 30 days or special project constraints.",
        height=140,
    )

if "audit_reports" not in st.session_state:
    st.session_state.audit_reports = {}
if "pdf_bytes_store" not in st.session_state:
    st.session_state.pdf_bytes_store = {}
if "extracted_text_store" not in st.session_state:
    st.session_state.extracted_text_store = {}
if "comparison_report" not in st.session_state:
    st.session_state.comparison_report = None
if "last_compare_pair" not in st.session_state:
    st.session_state.last_compare_pair = None
if "timeline_report" not in st.session_state:
    st.session_state.timeline_report = None
if "last_timeline_sig" not in st.session_state:
    st.session_state.last_timeline_sig = None

custom_pii_terms = [t.strip() for t in custom_pii_raw.split(",") if t.strip()]

tab1, tab2 = st.tabs(["🔍 Single & Batch Contract Audit", "⚖️ Version Comparison (Redlining)"])

# ==========================================
# Tab 1: Single & Batch Audit + Risk Dashboard
# ==========================================
with tab1:
    uploaded_files = st.file_uploader(
        "Upload Contract or RFP Documents (PDF)",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if uploaded_files and st.button("🚀 Run Compliance Audit", type="primary"):
        if not api_key:
            st.error("Please enter your API key in the sidebar first.")
        else:
            for uploaded_file in uploaded_files:
                with st.spinner(
                    f"Analyzing document and generating compliance matrix for {uploaded_file.name}..."
                ):
                    try:
                        pdf_bytes = uploaded_file.getvalue()
                        st.session_state.pdf_bytes_store[uploaded_file.name] = pdf_bytes
                        extracted_txt = extract_text_with_pages(pdf_bytes)
                        st.session_state.extracted_text_store[uploaded_file.name] = extracted_txt

                        if enable_pii_masking and not extracted_txt.strip():
                            st.warning(
                                f"`{uploaded_file.name}` appears to be a scanned/image PDF with no extractable text layer; it will be sent directly to Gemini Vision without local text redaction."
                            )

                        report = audit_contract(
                            pdf_bytes=pdf_bytes,
                            api_key=api_key,
                            custom_rules=custom_rules,
                            jurisdiction=jurisdiction,
                            company_playbook=company_playbook,
                            enable_pii_masking=enable_pii_masking,
                            output_language=output_language,
                            custom_pii_terms=custom_pii_terms,
                            pre_extracted_text=extracted_txt,
                        )
                        st.session_state.audit_reports[uploaded_file.name] = report
                    except Exception as e:
                        st.error(f"Audit failed for {uploaded_file.name}: {str(e)}")

    if len(st.session_state.audit_reports) > 1:
        st.subheader("📊 Portfolio Risk Overview")
        summary_rows = []
        for fname, rep in st.session_state.audit_reports.items():
            summary_rows.append(
                {
                    "Document Name": fname,
                    "Type": rep.document_type,
                    "Risk Score (/100)": rep.overall_risk_score,
                    "Total Risks": len(rep.detected_risks),
                    "High Risks": sum(1 for r in rep.detected_risks if r.risk_level == "High"),
                }
            )
        summary_df = pd.DataFrame(summary_rows).sort_values(
            by="Risk Score (/100)", ascending=False
        )
        st.dataframe(summary_df, width="stretch")

    if st.session_state.audit_reports:
        for file_name, report in st.session_state.audit_reports.items():
            st.markdown(f"---\n### 📄 Document Audit Report: `{file_name}`")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Overall Risk Score", f"{report.overall_risk_score} / 100")
            col2.metric("Detected Risks", len(report.detected_risks))
            col3.metric("Document Type", report.document_type)
            col4.metric(
                "Est. Financial Exposure",
                report.estimated_financial_exposure or "N/A",
            )

            st.subheader("📋 Executive Summary")
            st.info(report.contract_summary)

            report_json = report.model_dump_json()
            dl_col1, dl_col2 = st.columns(2)
            with dl_col1:
                docx_bytes = _cached_word_report(report_json, file_name)
                st.download_button(
                    label="📥 Download Word Report (.docx)",
                    data=docx_bytes,
                    file_name=f"audit_report_{file_name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"docx_{file_name}",
                    width="stretch",
                )
            with dl_col2:
                excel_bytes = _cached_excel_report(report_json)
                st.download_button(
                    label="📊 Download Excel Matrix (.xlsx)",
                    data=excel_bytes,
                    file_name=f"compliance_matrix_{file_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"xlsx_{file_name}",
                    width="stretch",
                )

            st.subheader("🚨 Detected Risk & Compliance Clauses")
            if report.detected_risks:
                risks_data = [
                    {
                        "Risk Level": r.risk_level,
                        "Page": r.page_number,
                        "Clause": r.clause_title,
                        "Exact Quote": r.exact_quote,
                        "Analysis": r.explanation,
                        "Financial Exposure": r.financial_exposure_estimate or "-",
                        "Playbook Violation": r.playbook_violation or "-",
                        "Recommended Action": r.recommended_action,
                        "Alternative Wording": r.alternative_wording,
                    }
                    for r in report.detected_risks
                ]
                st.dataframe(pd.DataFrame(risks_data), width="stretch")
            else:
                st.success("No major risk clauses detected!")

            if report.rfp_compliance_matrix:
                st.subheader("📊 RFP Compliance Matrix")
                matrix_data = [
                    {
                        "Req #": m.requirement_number,
                        "Client Requirement": m.client_requirement,
                        "Status": m.compliance_status,
                        "Bidder Response": m.bidder_response,
                    }
                    for m in report.rfp_compliance_matrix
                ]
                st.dataframe(pd.DataFrame(matrix_data), width="stretch")

            if report.missing_protections:
                st.subheader("🛡️ Missing Protective Clauses")
                for item in report.missing_protections:
                    st.warning(f"• {item}")

            if report.negotiation_email_draft:
                st.subheader("✉️ Negotiation Email Draft")
                st.code(report.negotiation_email_draft, language="markdown")

            st.markdown("---")
            st.subheader(f"💬 Chat with `{file_name}` (Interactive Legal Assistant)")
            st.markdown(
                "Ask any specific question about this contract and AI will answer with extracted page numbers:"
            )

            user_question = st.text_input(
                "Example: What are the conditions for contract termination?",
                key=f"q_input_{file_name}",
                placeholder="Type your question here...",
            )

            if user_question:
                if not api_key:
                    st.error("Please enter your API key first.")
                else:
                    with st.spinner("Searching contract clauses and analyzing the answer..."):
                        try:
                            file_bytes = st.session_state.pdf_bytes_store.get(file_name)
                            cached_txt = st.session_state.extracted_text_store.get(file_name)
                            answer = ask_contract_question(
                                pdf_bytes=file_bytes,
                                api_key=api_key,
                                question=user_question,
                                jurisdiction=jurisdiction,
                                output_language=output_language,
                                pre_extracted_text=cached_txt,
                            )
                            st.success("Legal Answer:")
                            st.markdown(answer)
                        except Exception as e:
                            st.error(f"Failed to answer question: {str(e)}")


# ==========================================
# Tab 2: Version Comparison (Original vs Revised)
# ==========================================
with tab2:
    st.subheader("🔄 Version Comparison & Multi-Round Negotiation Timeline")
    compare_mode = st.radio(
        "Select Comparison Mode:",
        [
            "Quick 2-Version Compare (Original vs. Revised)",
            "Multi-Round Negotiation Timeline (V1 → V2 → V3...)",
        ],
        horizontal=True,
    )

    if compare_mode == "Quick 2-Version Compare (Original vs. Revised)":
        st.markdown(
            "Upload the original contract version and the revised version after negotiation to verify adherence to edits and detect any hidden new clauses."
        )

        c_col1, c_col2 = st.columns(2)
        with c_col1:
            orig_file = st.file_uploader("1️⃣ Original Contract (PDF)", type=["pdf"], key="orig_pdf")
        with c_col2:
            rev_file = st.file_uploader("2️⃣ Revised Contract (PDF)", type=["pdf"], key="rev_pdf")

        current_pair = (
            (orig_file.name, orig_file.size, rev_file.name, rev_file.size)
            if (orig_file and rev_file)
            else None
        )
        if current_pair != st.session_state.last_compare_pair:
            st.session_state.comparison_report = None
            st.session_state.last_compare_pair = current_pair

        if orig_file and rev_file and st.button("⚖️ Compare Versions", type="primary"):
            if not api_key:
                st.error("Please enter your API key in the sidebar first.")
            else:
                with st.spinner(
                    "Comparing both versions and analyzing legal and financial differences..."
                ):
                    try:
                        orig_bytes = orig_file.getvalue()
                        rev_bytes = rev_file.getvalue()
                        comp_report = compare_contracts(
                            original_bytes=orig_bytes,
                            revised_bytes=rev_bytes,
                            api_key=api_key,
                            jurisdiction=jurisdiction,
                            output_language=output_language,
                            pre_orig_text=extract_text_with_pages(orig_bytes),
                            pre_rev_text=extract_text_with_pages(rev_bytes),
                        )
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
            changes_data = [
                {
                    "Clause Topic": ch.clause_topic,
                    "Status": ch.change_status,
                    "Original Version": ch.original_text_summary,
                    "Revised Version": ch.revised_text_summary,
                    "Risk Impact": ch.risk_impact,
                }
                for ch in comp.changes_breakdown
            ]
            st.dataframe(pd.DataFrame(changes_data), width="stretch")

    else:
        st.markdown(
            "Upload contract versions in chronological order of negotiation rounds (from oldest to newest) to track risk progression and open clauses."
        )
        timeline_files = st.file_uploader(
            "Upload Contract Versions in Chronological Order (V1, V2, V3...)",
            type=["pdf"],
            accept_multiple_files=True,
            key="timeline_pdfs",
        )

        if timeline_files:
            sig = hashlib.md5(
                "|".join(f"{f.name}:{f.size}" for f in timeline_files).encode()
            ).hexdigest()
            if sig != st.session_state.last_timeline_sig:
                st.session_state.timeline_report = None
                st.session_state.last_timeline_sig = sig

            file_names = [f.name for f in timeline_files]
            ordered_names = st.multiselect(
                "Verify or Adjust Chronological Round Order (First = Round 1):",
                options=file_names,
                default=file_names,
            )
            file_map = {f.name: f for f in timeline_files}
            ordered_files = [file_map[n] for n in ordered_names if n in file_map]

            for i, f in enumerate(ordered_files, start=1):
                st.write(f"**Round {i}:** `{f.name}`")

            if len(ordered_files) >= 2 and st.button(
                "📈 Build Negotiation Timeline", type="primary"
            ):
                if not api_key:
                    st.error("Please enter your API key in the sidebar first.")
                else:
                    with st.spinner("Analyzing negotiation path across all versions..."):
                        try:
                            versions_payload = [(f.name, f.getvalue()) for f in ordered_files]
                            st.session_state.timeline_report = analyze_negotiation_timeline(
                                versions=versions_payload,
                                api_key=api_key,
                                jurisdiction=jurisdiction,
                                output_language=output_language,
                            )
                        except Exception as e:
                            st.error(f"Timeline analysis failed: {str(e)}")
            elif len(ordered_files) < 2:
                st.warning("Please select or upload at least two versions to build a timeline.")

        if st.session_state.timeline_report:
            tl = st.session_state.timeline_report
            st.markdown("---")
            st.info(tl.timeline_summary)
            st.success(f"**Current Legal Verdict:** {tl.overall_negotiation_verdict}")

            score_df = pd.DataFrame(
                [
                    {
                        "Round": f"Round {r.round_number}",
                        "Version": r.version_label,
                        "Risk Score (/100)": r.round_risk_score,
                    }
                    for r in tl.rounds
                ]
            )
            st.subheader("📉 Risk Progression Across Rounds")
            st.dataframe(score_df, width="stretch")

            for r in tl.rounds:
                with st.expander(
                    f"Round {r.round_number}: {r.version_label} — Risk Score: {r.round_risk_score}/100",
                    expanded=(r.round_number == len(tl.rounds)),
                ):
                    st.write(f"**Key Changes:** {r.key_changes_summary}")
                    if r.resolved_issues:
                        st.markdown("**Resolved / Improved:**")
                        for item in r.resolved_issues:
                            st.markdown(f"- ✅ {item}")
                    if r.unresolved_or_new_risks:
                        st.markdown("**Unresolved or New Risks:**")
                        for item in r.unresolved_or_new_risks:
                            st.markdown(f"- ⚠️ {item}")

            if tl.next_round_leverage_tips:
                st.subheader("🎯 Leverage Tips for Next Negotiation Round")
                for tip in tl.next_round_leverage_tips:
                    st.warning(f"• {tip}")
