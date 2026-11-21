import time
from typing import Any, TypeVar
import fitz  # PyMuPDF
from google import genai
from google.genai import types
from pydantic import BaseModel
from schemas import (
    ContractAuditReport,
    ContractComparisonReport,
    MultiRoundTimelineReport,
    OutputLanguage,
)
from security import mask_sensitive_data, unmask_report_text

SchemaT = TypeVar("SchemaT", bound=BaseModel)


def _language_rule(output_language: OutputLanguage = "English") -> str:
    if output_language == "Arabic":
        return (
            " Write every output field, explanation, summary, draft, and answer clearly in professional "
            "Arabic (keeping legal clause references or exact contract quotes accurate)."
        )
    if output_language == "Match Document Language":
        return (
            " Detect the primary language of the provided document/question and write all explanations, "
            "summaries, drafts, and answers in that same language."
        )
    return (
        " Always write every output field, explanation, summary, draft, and answer strictly in English "
        "regardless of the input document or question language."
    )


def extract_text_with_pages(pdf_bytes: bytes) -> str:
    """Extracts text from PDF bytes while tagging each page number accurately."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text: list[str] = []
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()
            if text:
                full_text.append(f"--- [PAGE {page_num + 1}] ---\n{text}")
    finally:
        doc.close()
    return "\n\n".join(full_text)


def _generate_with_retry(
    client: genai.Client,
    model: str,
    contents: Any,
    system_instruction: str,
    temperature: float = 0.1,
    response_schema: type[SchemaT] | None = None,
    max_retries: int = 3,
    initial_delay: float = 2.0,
) -> Any:
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            config_kwargs: dict[str, Any] = {
                "system_instruction": system_instruction,
                "temperature": temperature,
            }
            if response_schema is not None:
                config_kwargs["response_mime_type"] = "application/json"
                config_kwargs["response_schema"] = response_schema

            return client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(**config_kwargs),
            )
        except Exception as exc:
            error_str = str(exc)
            is_transient = any(
                token in error_str
                for token in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "Deadline expired")
            )
            if is_transient and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise


def audit_contract(
    pdf_bytes: bytes,
    api_key: str,
    custom_rules: str = "",
    jurisdiction: str = "General International Commercial Law",
    company_playbook: str = "",
    enable_pii_masking: bool = True,
    output_language: OutputLanguage = "English",
    custom_pii_terms: list[str] | None = None,
    pre_extracted_text: str | None = None,
) -> ContractAuditReport:
    """Audits extracted contract text or scanned PDF using Gemini with structured output and PII handling."""
    client = genai.Client(api_key=api_key)

    contract_text = (
        pre_extracted_text if pre_extracted_text is not None else extract_text_with_pages(pdf_bytes)
    )

    pii_mapping: dict[str, str] = {}
    if enable_pii_masking and contract_text.strip():
        contract_text, pii_mapping = mask_sensitive_data(contract_text, custom_terms=custom_pii_terms)

    system_instruction = (
        f"You are an elite Senior Corporate Lawyer and RFP Compliance Auditor operating under the jurisdiction of: {jurisdiction}. "
        "Analyze the provided contract or RFP document carefully. Identify hidden financial traps, "
        "unfair penalty clauses, liability imbalances, auto-renewal traps, and compliance gaps. "
        "You MUST cite the exact [PAGE X] number where each issue is located, provide an exact quote, "
        "estimate financial exposure if applicable, check against the provided Company Playbook, "
        "and provide a professional, ready-to-use alternative safe clause text (alternative_wording)."
        + _language_rule(output_language)
    )

    if not contract_text.strip():
        response = _generate_with_retry(
            client=client,
            model="gemini-3.5-flash",
            contents=[
                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                "Audit this scanned or image-based document thoroughly following the instructions.",
            ],
            system_instruction=system_instruction,
            temperature=0.1,
            response_schema=ContractAuditReport,
        )
    else:
        user_prompt = f"Audit the following document:\n\n{contract_text}"
        if company_playbook.strip():
            user_prompt += f"\n\nCompany Internal Legal Playbook (Strict Rules to enforce):\n{company_playbook}"
        if custom_rules.strip():
            user_prompt += f"\n\nAdditional Custom Compliance Rules:\n{custom_rules}"

        response = _generate_with_retry(
            client=client,
            model="gemini-3.5-flash-lite",
            contents=user_prompt,
            system_instruction=system_instruction,
            temperature=0.1,
            response_schema=ContractAuditReport,
        )

    report = ContractAuditReport.model_validate_json(response.text)

    if pii_mapping:
        report.contract_summary = unmask_report_text(report.contract_summary, pii_mapping)
        if report.estimated_financial_exposure:
            report.estimated_financial_exposure = unmask_report_text(
                report.estimated_financial_exposure, pii_mapping
            )
        if report.negotiation_email_draft:
            report.negotiation_email_draft = unmask_report_text(
                report.negotiation_email_draft, pii_mapping
            )
        report.missing_protections = [
            unmask_report_text(item, pii_mapping) for item in report.missing_protections
        ]
        for risk in report.detected_risks:
            risk.clause_title = unmask_report_text(risk.clause_title, pii_mapping)
            risk.exact_quote = unmask_report_text(risk.exact_quote, pii_mapping)
            risk.explanation = unmask_report_text(risk.explanation, pii_mapping)
            risk.recommended_action = unmask_report_text(risk.recommended_action, pii_mapping)
            risk.alternative_wording = unmask_report_text(risk.alternative_wording, pii_mapping)
            if risk.financial_exposure_estimate:
                risk.financial_exposure_estimate = unmask_report_text(
                    risk.financial_exposure_estimate, pii_mapping
                )
            if risk.playbook_violation:
                risk.playbook_violation = unmask_report_text(risk.playbook_violation, pii_mapping)

    return report


def compare_contracts(
    original_bytes: bytes,
    revised_bytes: bytes,
    api_key: str,
    jurisdiction: str = "General International Commercial Law",
    output_language: OutputLanguage = "English",
    pre_orig_text: str | None = None,
    pre_rev_text: str | None = None,
) -> ContractComparisonReport:
    client = genai.Client(api_key=api_key)

    orig_text = pre_orig_text if pre_orig_text is not None else extract_text_with_pages(original_bytes)
    rev_text = pre_rev_text if pre_rev_text is not None else extract_text_with_pages(revised_bytes)

    system_instruction = (
        f"You are an elite Senior Corporate Lawyer under {jurisdiction}. "
        "Compare the ORIGINAL contract against the REVISED contract carefully. "
        "Identify every material modification, check if previous risk imbalances were fixed, "
        "and aggressively catch any NEW hidden financial or legal traps slipped into the revised draft."
        + _language_rule(output_language)
    )

    if orig_text.strip() and rev_text.strip():
        contents: Any = (
            f"=== ORIGINAL CONTRACT ===\n{orig_text}\n\n=== REVISED CONTRACT ===\n{rev_text}"
        )
        model_name = "gemini-3.5-flash-lite"
    else:
        contents = [
            "Compare the first document (ORIGINAL) with the second document (REVISED):",
            types.Part.from_bytes(data=original_bytes, mime_type="application/pdf"),
            types.Part.from_bytes(data=revised_bytes, mime_type="application/pdf"),
        ]
        model_name = "gemini-3.5-flash"

    response = _generate_with_retry(
        client=client,
        model=model_name,
        contents=contents,
        system_instruction=system_instruction,
        temperature=0.1,
        response_schema=ContractComparisonReport,
    )
    return ContractComparisonReport.model_validate_json(response.text)


def ask_contract_question(
    pdf_bytes: bytes | None,
    api_key: str,
    question: str,
    jurisdiction: str = "General International Commercial Law",
    output_language: OutputLanguage = "English",
    pre_extracted_text: str | None = None,
) -> str:
    """Answers specific user questions based on extracted contract text with page citations."""
    client = genai.Client(api_key=api_key)

    if pre_extracted_text is not None and pre_extracted_text.strip():
        contract_text = pre_extracted_text
    elif pdf_bytes:
        contract_text = extract_text_with_pages(pdf_bytes)
    else:
        raise ValueError("No contract text or PDF bytes provided.")

    system_instruction = (
        f"You are an expert Legal Assistant operating under {jurisdiction}. "
        "Answer the user's specific question about the provided contract accurately and objectively. "
        "You MUST cite the exact [PAGE X] number and provide short exact quotes supporting your answer."
        + _language_rule(output_language)
    )

    response = _generate_with_retry(
        client=client,
        model="gemini-3.5-flash-lite",
        contents=f"Contract Document Text:\n\n{contract_text}\n\nUser Question: {question}",
        system_instruction=system_instruction,
        temperature=0.2,
    )
    return response.text or ""


def analyze_negotiation_timeline(
    versions: list[tuple[str, bytes]],
    api_key: str,
    jurisdiction: str = "General International Commercial Law",
    output_language: OutputLanguage = "English",
) -> MultiRoundTimelineReport:
    """Analyzes multiple sequential contract versions (V1 -> V2 -> V3...) chronologically."""
    client = genai.Client(api_key=api_key)

    system_instruction = (
        f"You are an elite Senior Corporate Lawyer and Lead Contract Negotiator under {jurisdiction}. "
        "You are given multiple contract versions in chronological order (Version 1 is the earliest/initial draft, "
        "followed by subsequent revisions). Track how each round resolves or ignores prior issues, "
        "detect any new traps introduced in later rounds, score the risk of each version (1-100), "
        "and provide sharp negotiation leverage tips for the next round."
        + _language_rule(output_language)
    )

    contents: list[Any] = [
        f"Analyze these {len(versions)} sequential contract versions in exact chronological order:"
    ]

    all_have_text = True
    extracted_versions: list[tuple[int, str, str, bytes]] = []
    for idx, (fname, pdf_bytes) in enumerate(versions, start=1):
        text = extract_text_with_pages(pdf_bytes)
        extracted_versions.append((idx, fname, text, pdf_bytes))
        if not text.strip():
            all_have_text = False

    if all_have_text:
        combined_parts = [
            f"=== VERSION {idx}: {fname} ===\n{text}" for idx, fname, text, _ in extracted_versions
        ]
        contents.append("\n\n".join(combined_parts))
    else:
        for idx, fname, text, pdf_bytes in extracted_versions:
            contents.append(f"--- VERSION {idx}: {fname} ---")
            if text.strip():
                contents.append(text)
            else:
                contents.append(types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"))

    model_name = "gemini-3.5-flash-lite" if all_have_text else "gemini-3.5-flash"
    response = _generate_with_retry(
        client=client,
        model=model_name,
        contents=contents,
        system_instruction=system_instruction,
        temperature=0.1,
        response_schema=MultiRoundTimelineReport,
    )
    return MultiRoundTimelineReport.model_validate_json(response.text)
            
