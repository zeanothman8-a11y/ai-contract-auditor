import time
import fitz  # PyMuPDF
from google import genai
from google.genai import types
from schemas import ContractAuditReport, ContractComparisonReport
from security import mask_sensitive_data, unmask_report_text

def extract_text_with_pages(pdf_bytes: bytes) -> str:
    """Extracts text from PDF bytes while tagging each page number accurately."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()
        if text:
            full_text.append(f"--- [PAGE {page_num + 1}] ---\n{text}")
    doc.close()
    return "\n\n".join(full_text)

def audit_contract(pdf_bytes: bytes, api_key: str, custom_rules: str = "", jurisdiction: str = "General International Commercial Law", company_playbook: str = "", enable_pii_masking: bool = True) -> ContractAuditReport:
    """Audits extracted contract or scanned PDF using Gemini with strict Pydantic structured output, PII masking, and Playbook enforcement."""
    client = genai.Client(api_key=api_key)
    
    contract_text = extract_text_with_pages(pdf_bytes)
    
    # تطبيق إخفاء البيانات الحساسة إذا كان الخيار مفعلاً
    pii_mapping = {}
    if enable_pii_masking and contract_text.strip():
        contract_text, pii_mapping = mask_sensitive_data(contract_text)
    
    system_instruction = (
        f"You are an elite Senior Corporate Lawyer and RFP Compliance Auditor operating under the jurisdiction of: {jurisdiction}. "
        "Analyze the provided contract or RFP document carefully. Identify hidden financial traps, "
        "unfair penalty clauses, liability imbalances, auto-renewal traps, and compliance gaps. "
        "You MUST cite the exact [PAGE X] number where each issue is located, provide an exact quote, "
        "estimate financial exposure if applicable, check against the provided Company Playbook, "
        "and crucially, provide a professional, ready-to-use alternative safe clause text (alternative_wording)."
    )
    
    max_retries = 3
    delay = 2
    
    for attempt in range(max_retries):
        try:
            if not contract_text.strip():
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        types.Part.from_bytes(
                            data=pdf_bytes,
                            mime_type="application/pdf",
                        ),
                        "Audit this scanned or image-based document thoroughly following the instructions."
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=ContractAuditReport,
                        temperature=0.1,
                    ),
                )
            else:
                user_prompt = f"Audit the following document:\n\n{contract_text}"
                if company_playbook.strip():
                    user_prompt += f"\n\nCompany Internal Legal Playbook (Strict Rules to enforce):\n{company_playbook}"
                if custom_rules.strip():
                    user_prompt += f"\n\nAdditional Custom Compliance Rules:\n{custom_rules}"
                
                response = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=ContractAuditReport,
                        temperature=0.1,
                    ),
                )
                
            report = ContractAuditReport.model_validate_json(response.text)
            
            # إعادة البيانات الحساسة الأصلية لتقرير النتائج إن وجدت
            if pii_mapping:
                report.contract_summary = unmask_report_text(report.contract_summary, pii_mapping)
                if report.negotiation_email_draft:
                    report.negotiation_email_draft = unmask_report_text(report.negotiation_email_draft, pii_mapping)
                for risk in report.detected_risks:
                    risk.exact_quote = unmask_report_text(risk.exact_quote, pii_mapping)
                    risk.explanation = unmask_report_text(risk.explanation, pii_mapping)
                    risk.alternative_wording = unmask_report_text(risk.alternative_wording, pii_mapping)
                    
            return report
            
        except Exception as e:
            error_str = str(e)
            if ("503" in error_str or "UNAVAILABLE" in error_str) and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            else:
                raise e

def compare_contracts(original_bytes: bytes, revised_bytes: bytes, api_key: str, jurisdiction: str = "General International Commercial Law") -> ContractComparisonReport:
    client = genai.Client(api_key=api_key)
    
    orig_text = extract_text_with_pages(original_bytes)
    rev_text = extract_text_with_pages(revised_bytes)
    
    system_instruction = (
        f"You are an elite Senior Corporate Lawyer under {jurisdiction}. "
        "Compare the ORIGINAL contract against the REVISED contract carefully. "
        "Identify every material modification, check if previous risk imbalances were fixed, "
        "and aggressively catch any NEW hidden financial or legal traps slipped into the revised draft."
    )
    
    contents = []
    if orig_text.strip() and rev_text.strip():
        contents.append(f"=== ORIGINAL CONTRACT ===\n{orig_text}\n\n=== REVISED CONTRACT ===\n{rev_text}")
    else:
        contents.append("Compare the first document (ORIGINAL) with the second document (REVISED):")
        contents.append(types.Part.from_bytes(data=original_bytes, mime_type="application/pdf"))
        contents.append(types.Part.from_bytes(data=revised_bytes, mime_type="application/pdf"))

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=ContractComparisonReport,
            temperature=0.1,
        ),
    )
    return ContractComparisonReport.model_validate_json(response.text)
                
