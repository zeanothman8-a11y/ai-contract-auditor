import hashlib
import pandas as pd
import streamlit as st
from auditor import (
    analyze_negotiation_timeline,
    ask_contract_question,
    audit_contract,
    compare_contracts,
    compute_quick_redline_diff,
    extract_document_data,
)
from utils import (
    generate_counter_proposal_docx,
    generate_excel_report,
    generate_word_report,
)

st.set_page_config(
    page_title="Verilogix AI — Contract & RFP Intelligence",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom UI Styling for a cleaner, executive SaaS look
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2.5rem;
            max-width: 1280px;
        }
        .hero-box {
            background: linear-gradient(135deg, #111827 0%, #1e293b 60%, #0f172a 100%);
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 16px;
            padding: 1.4rem 1.6rem;
            margin-bottom: 1.2rem;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.28);
        }
        .hero-badge {
            display: inline-block;
            background: rgba(56, 189, 248, 0.14);
            color: #7dd3fc;
            border: 1px solid rgba(56, 189, 248, 0.35);
            font-size: 0.78rem;
            font-weight: 600;
            padding: 0.2rem 0.65rem;
            border-radius: 999px;
            margin-bottom: 0.55rem;
            letter-spacing: 0.02em;
        }
        .hero-title {
            font-size: 1.75rem;
            font-weight: 700;
            color: #f8fafc;
            margin: 0 0 0.35rem 0;
            line-height: 1.25;
        }
        .hero-sub {
            font-size: 0.98rem;
            color: #cbd5e1;
            margin: 0;
            line-height: 1.5;
        }
        div[data-testid="stMetric"] {
            background: rgba(30, 41, 59, 0.55);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 12px;
            padding: 0.85rem 1rem;
        }
        div[data-testid="stMetric"] label {
            color: #94a3b8 !important;
            font-size: 0.8rem !important;
        }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
            color: #f8fafc !important;
            font-weight: 700 !important;
        }
        .stButton > button[kind="primary"] {
            border-radius: 10px;
            font-weight: 600;
            padding: 0.55rem 1.1rem;
        }
        .stDownloadButton > button {
            border-radius: 10px;
            font-weight: 600;
        }
        div[data-testid="stDataFrame"] {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid rgba(148, 163, 184, 0.18);
        }
    </style>
    <div class="hero-box">
        <div class="hero-badge">VERILOGIX AI • RISK & COMPLIANCE ENGINE</div>
        <div class="hero-title">⚖️ Contract &amp; RFP Risk Intelligence</div>
        <p class="hero-sub">
            Spot high-risk clauses, deal-breakers, and financial exposure in seconds — with redline comparison, negotiation drafts, and instant exportable reports.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def _cached_word_report(report_json: str, filename: str) -> bytes:
    from schemas import ContractAuditReport

    parsed = ContractAuditReport.model_validate_json(report_json)
    return generate_word_report(parsed, filename).getvalue()


@st.cache_data(show_spinner=False)
def _cached_counter_proposal_docx(report_json: str, filename: str) -> bytes:
    from schemas import ContractAuditReport

    parsed = ContractAuditReport.model_validate_json(report_json)
    return generate_counter_proposal_docx(parsed, filename).getvalue()


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
    st.subheader("🚨 Deal-Breakers (Non-Negotiables)")
    deal_breakers = st.text_area(
        "Red-Line Rules (Auto-Escalates Risk)",
        placeholder="e.g., No unlimited liability. No IP ownership transfer. Delay penalties must not exceed 5% of contract value.",
        height=110,
        help="Any violation triggers an immediate Deal-Breaker alert and escalates the risk score.",
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
        height=110,
    )
    custom_rules = st.text_area(
        "Custom Compliance Rules (Optional)",
        placeholder="e.g., Payment terms must not exceed 30 days or special project constraints.",
        height=100,
    )

if "audit_reports" not in st.session_state:
    st.session_state.audit_reports = {}
if "pdf_bytes_store" not in st.session_state:
    st.session_state.pdf_bytes_store = {}
if "doc_meta_store" not in st.session_state:
    # Stores {filename: {"extracted_text": str, "page_count": int, "is_scanned": bool}}
    st.session_state.doc_meta_store = {}
if "comparison_report" not in st.session_state:
    st.session_state.comparison_report = None
if "quick_diff_preview" not in st.session_state:
    st.session_state.quick_diff_preview = None
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
                        doc_meta = extract_document_data(pdf_bytes)
                        st.session_state.doc_meta_store[uploaded_file.name] = doc_meta

                        if enable_pii_masking and doc_meta["is_scanned"]:
                            st.warning(
                                f"`{uploaded_file.name}` ({doc_meta['page_count']} pages) appears to be a scanned/image PDF with no extractable text layer; it will be sent directly to Gemini Vision without local text redaction."
                            )

                        report = audit_contract(
                            pdf_bytes=pdf_bytes,
                            api_key=api_key,
                            custom_rules=custom_rules,
                            jurisdiction=jurisdiction,
                            company_playbook=company_playbook,
                            deal_breakers=deal_breakers,
                            enable_pii_masking=enable_pii_masking,
                            output_language=output_language,
                            custom_pii_terms=custom_pii_terms,
                            pre_extracted_text=doc_meta["extracted_text"],
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
                    "Deal-Breakers": getattr(rep, "deal_breakers_triggered", 0),
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
            doc_meta = st.session_state.doc_meta_store.get(file_name, {})
            pages_label = f" ({doc_meta['page_count']} pages)" if doc_meta.get("page_count") else ""
            st.markdown(f"---\n### 📄 Document Audit Report: `{file_name}`{pages_label}")

            db_count = getattr(report, "deal_breakers_triggered", 0)
            if db_count > 0:
                st.error(
                    f"🛑 **DEAL-BREAKER ALERT:** {db_count} non-negotiable red-line rule(s) violated in this document! Do not sign without removing these clauses."
                )

            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Overall Risk Score", f"{report.overall_risk_score} / 100")
            col2.metric("Deal-Breakers", db_count)
            col3.metric("Detected Risks", len(report.detected_risks))
            col4.metric("Document Type", report.document_type)
            col5.metric(
                "Est. Financial Exposure",
                report.estimated_financial_exposure or "N/A",
            )

            st.subheader("📋 Executive Summary")
            st.info(report.contract_summary)

            report_json = report.model_dump_json()
            dl_col1, dl_col2, dl_col3 = st.columns(3)
            with dl_col1:
                docx_bytes = _cached_word_report(report_json, file_name)
                st.download_button(
                    label="📥 Full Audit Report (.docx)",
                    data=docx_bytes,
                    file_name=f"audit_report_{file_name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"docx_{file_name}",
                    width="stretch",
                )
            with dl_col2:
                counter_bytes = _cached_counter_proposal_docx(report_json, file_name)
                st.download_button(
                    label="✉️ Formal Counter-Proposal (.docx)",
                    data=counter_bytes,
                    file_name=f"counter_proposal_{file_name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"counter_{file_name}",
                    width="stretch",
                )
            with dl_col3:
                excel_bytes = _cached_excel_report(report_json)
                st.download_button(
                    label="📊 Excel Risk Matrix (.xlsx)",
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
                        "Deal-Breaker": "🛑 YES" if getattr(r, "is_deal_breaker", False) else "No",
                        "Risk Level": r.risk_level,
                        "Page": r.page_number,
                        "Clause": r.clause_title,
                        "Deal-Breaker Reason": getattr(r, "deal_breaker_reason", None) or "-",
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
                with st.expander("🛡️ Missing Protective Clauses", expanded=False):
                    for item in report.missing_protections:
                        st.warning(f"• {item}")

            if report.negotiation_email_draft:
                with st.expander("✉️ Negotiation Email Draft", expanded=False):
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
                            cached_txt = doc_meta.get("extracted_text")
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

        use_quick_diff = st.checkbox(
            "⚡ Enable Local Quick Redline Diff Pre-Scan (difflib — saves tokens & highlights exact line edits)",
            value=True,
        )

        current_pair = (
            (orig_file.name, orig_file.size, rev_file.name, rev_file.size)
            if (orig_file and rev_file)
            else None
        )
        if current_pair != st.session_state.last_compare_pair:
            st.session_state.comparison_report = None
            st.session_state.quick_diff_preview = None
            st.session_state.last_compare_pair = current_pair

        if orig_file and rev_file:
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                if st.button("⚡ Instant Local Diff Preview (No API Cost)", width="stretch"):
                    orig_meta = extract_document_data(orig_file.getvalue())
                    rev_meta = extract_document_data(rev_file.getvalue())
                    if orig_meta["is_scanned"] or rev_meta["is_scanned"]:
                        st.warning("One or both PDFs are scanned images; local text diff requires text-based PDFs.")
                    else:
                        st.session_state.quick_diff_preview = compute_quick_redline_diff(
                            orig_meta["extracted_text"], rev_meta["extracted_text"]
                        )
            with b_col2:
                run_ai_compare = st.button("⚖️ Deep AI Legal Comparison", type="primary", width="stretch")

            if st.session_state.quick_diff_preview:
                qd = st.session_state.quick_diff_preview
                with st.expander(
                    f"⚡ Local Text Diff — Similarity: {qd['similarity_pct']}% (+{qd['added_lines']} added / -{qd['removed_lines']} removed lines)",
                    expanded=True,
                ):
                    if qd["has_changes"]:
                        st.code(qd["unified_diff"], language="diff")
                    else:
                        st.success("Both documents have identical extracted text.")

            if run_ai_compare:
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
