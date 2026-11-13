import time
import fitz  # PyMuPDF
from google import genai
from google.genai import types
from schemas import ContractAuditReport

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

def audit_contract(pdf_bytes: bytes, api_key: str, custom_rules: str = "", jurisdiction: str = "General International Commercial Law") -> ContractAuditReport:
    """Audits extracted contract text using Gemini with strict Pydantic structured output and auto-retry for 503 errors."""
    contract_text = extract_text_with_pages(pdf_bytes)
    
    if not contract_text:
        raise ValueError("No readable text found in the uploaded PDF. It might be a scanned image.")

    client = genai.Client(api_key=api_key)
    
    system_instruction = (
        f"You are an elite Senior Corporate Lawyer and RFP Compliance Auditor operating under the jurisdiction of: {jurisdiction}. "
        "Analyze the provided contract or RFP document carefully. Identify hidden financial traps, "
        "unfair penalty clauses, liability imbalances, auto-renewal traps, and compliance gaps. "
        "You MUST cite the exact [PAGE X] number where each issue is located, provide an exact quote, "
        "and crucially, provide a professional, ready-to-use alternative safe clause text (alternative_wording) that the user can directly negotiate with."
    )
    
    user_prompt = f"Audit the following document:\n\n{contract_text}"
    if custom_rules.strip():
        user_prompt += f"\n\nAdditional Company Compliance Rules to enforce:\n{custom_rules}"

    max_retries = 3
    delay = 2  # ثواني الانتظار بين المحاولات
    
    for attempt in range(max_retries):
        try:
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
            return ContractAuditReport.model_validate_json(response.text)
            
        except Exception as e:
            error_str = str(e)
            # إذا كان الخطأ بسبب الضغط 503 ولم نصل للمحاولة الأخيرة، انتظر وأعد المحاولة
            if ("503" in error_str or "UNAVAILABLE" in error_str) and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2  # مضاعفة وقت الانتظار تصاعدياً
                continue
            else:
                raise e
                
