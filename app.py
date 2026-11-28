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

# Full-page executive SaaS theme & custom typography
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }

        /* Hide Streamlit top toolbar, decoration & menu when possible */
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        #MainMenu {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
        }

        /* Full app background override */
        [data-testid="stAppViewContainer"] {
            background: radial-gradient(circle at 15% 10%, #132238 0%, #090e1a 48%, #060911 100%) !important;
            color: #f1f5f9 !important;
        }

        [data-testid="stHeader"] {
            background: transparent !important;
            height: 2.2rem !important;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0d1526 0%, #090e1a 100%) !important;
            border-right: 1px solid rgba(56, 189, 248, 0.16) !important;
        }

        .block-container {
            padding-top: 2.6rem !important;
            padding-bottom: 3rem !important;
            max-width: 1280px !important;
        }

        /* Hero Banner */
        .hero-box {
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.92) 0%, rgba(30, 41, 59, 0.78) 55%, rgba(14, 116, 144, 0.25) 100%);
            border: 1px solid rgba(56, 189, 248, 0.28);
            border-radius: 18px;
            padding: 1.5rem 1.75rem;
            margin-bottom: 1.35rem;
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.42), inset 0 1px 0 rgba(255, 255, 255, 0.08);
        }
        .hero-badge {
            display: inline-block;
            background: rgba(56, 189, 248, 0.14);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.38);
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.24rem 0.75rem;
            border-radius: 999px;
            margin-bottom: 0.65rem;
            letter-spacing: 0.06em;
        }
        .hero-title {
            font-size: 1.85rem;
            font-weight: 800;
            background: linear-gradient(90deg, #ffffff 0%, #bae6fd 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0 0 0.4rem 0;
            line-height: 1.25;
            letter-spacing: -0.02em;
        }
        .hero-sub {
            font-size: 0.98rem;
            color: #cbd5e1;
            margin: 0;
            line-height: 1.55;
            max-width: 820px;
        }
        .hero-pills {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.95rem;
        }
        .hero-pill {
            background: rgba(15, 23, 42, 0.75);
            border: 1px solid rgba(148, 163, 184, 0.22);
            color: #e2e8f0;
            font-size: 0.78rem;
            font-weight: 600;
            padding: 0.28rem 0.7rem;
            border-radius: 8px;
        }

        /* Headings & Text */
        h1, h2, h3, h4 {
            color: #f8fafc !important;
            font-weight: 700 !important;
            letter-spacing: -0.01em;
        }
        p, label, .stMarkdown {
            color: #e2e8f0;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
            background: rgba(15, 23, 42, 0.65);
            padding: 0.35rem;
            border-radius: 12px;
            border: 1px solid rgba(148, 163, 184, 0.16);
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 9px;
            padding: 0.5rem 1rem;
            font-weight: 600;
            color: #94a3b8;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%) !important;
            color: #ffffff !important;
        }

        /* File Uploader */
        [data-testid="stFileUploader"] section {
            background: rgba(15, 23, 42, 0.68) !important;
            border: 1.5px dashed rgba(56, 189, 248, 0.42) !important;
            border-radius: 14px !important;
            padding: 1.1rem !important;
            transition: border-color 0.2s ease, background 0.2s ease;
        }
        [data-testid="stFileUploader"] section:hover {
            border-color: #38bdf8 !important;
            background: rgba(15, 23, 42, 0.88) !important;
        }

        /* Metric Cards */
        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(30, 41, 59, 0.68) 0%, rgba(15, 23, 42, 0.85) 100%) !important;
            border: 1px solid rgba(56, 189, 248, 0.22) !important;
            border-radius: 14px !important;
            padding: 0.9rem 1.05rem !important;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25);
        }
        div[data-testid="stMetric"] label {
            color: #94a3b8 !important;
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
            color: #f8fafc !important;
            font-weight: 800 !important;
            font-size: 1.45rem !important;
        }

        /* Primary & Secondary Buttons */
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 11px !important;
            font-weight: 700 !important;
            padding: 0.6rem 1.25rem !important;
            box-shadow: 0 8px 22px rgba(14, 165, 233, 0.32) !important;
            transition: transform 0.15s ease, box-shadow 0.15s ease !important;
        }
        .stButton > button[kind="primary"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 12px 26px rgba(14, 165, 233, 0.45) !important;
        }
        .stDownloadButton > button, .stButton > button[kind="secondary"] {
            background: rgba(30, 41, 59, 0.78) !important;
            color: #e2e8f0 !important;
            border: 1px solid rgba(56, 189, 248, 0.28) !important;
            border-radius: 11px !important;
            font-weight: 600 !important;
        }
        .stDownloadButton > button:hover {
            border-color: #38bdf8 !important;
            background: rgba(30, 41, 59, 0.98) !important;
        }

        /* Expanders, Alerts & Inputs */
        div[data-testid="stExpander"] {
            background: rgba(15, 23, 42, 0.65) !important;
            border: 1px solid rgba(148, 163, 184, 0.2) !important;
            border-radius: 12px !important;
        }
        div[data-testid="stAlert"] {
            border-radius: 12px !important;
        }
        div[data-testid="stDataFrame"] {
            border-radius: 14px !important;
            overflow: hidden !important;
            border: 1px solid rgba(56, 189, 248, 0.22) !important;
        }
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
            background-color: rgba(15, 23, 42, 0.85) !important;
            border: 1px solid rgba(148, 163, 184, 0.25) !important;
            border-radius: 10px !important;
            color: #f8fafc !important;
        }
    </style>

    <div class="hero-box">
        <div class="hero-badge">VERILOGIX AI • ENTERPRISE RISK ENGINE</div>
        <div class="hero-title">⚖️ Contract &amp; RFP Risk Intelligence</div>
        <p class="hero-sub">
            Detect hidden liability traps, deal-breakers, and financial exposure in seconds — complete with redline comparisons, counter-proposals, and board-ready reports.
        </p>
        <div class="hero-pills">
            <span class="hero-pill">⚡ Instant Risk Scoring</span>
            <span class="hero-pill">🛑 Deal-Breaker Alerts</span>
            <span class="hero-pill">🔄 Redline Diff &amp; Timeline</span>
            <span class="hero-pill">🔒 Local PII Privacy</span>
        </div>
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
                    with st.spinner(
                        "Comparing both versions and analyzing legal and financial differences..."
                    ):
                        try:
                            orig_meta = extract_document_data(orig_file.getvalue())
                            rev_meta = extract_document_data(rev_file.getvalue())
                            if not orig_meta["is_scanned"] and not rev_meta["is_scanned"]:
                                st.session_state.quick_diff_preview = compute_quick_redline_diff(
                                    orig_meta["extracted_text"], rev_meta["extracted_text"]
                                )
                            comp_report = compare_contracts(
                                original_bytes=orig_file.getvalue(),
                                revised_bytes=rev_file.getvalue(),
                                api_key=api_key,
                                jurisdiction=jurisdiction,
                                output_language=output_language,
                                pre_orig_text=orig_meta["extracted_text"],
                                pre_rev_text=rev_meta["extracted_text"],
                                use_quick_diff=use_quick_diff,
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
