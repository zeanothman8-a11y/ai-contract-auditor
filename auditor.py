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

def audit_contract(pdf_bytes: bytes, api_key: str, custom_rules: str = "") -> ContractAuditReport:
    """Audits extracted contract text using Gemini with strict Pydantic structured output."""
    contract_text = extract_text_with_pages(pdf_bytes)
    
    if not contract_text:
        raise ValueError("No readable text found in the uploaded PDF. It might be a scanned image.")

    client = genai.Client(api_key=api_key)
    
    system_instruction = (
        "You are an elite Senior Corporate Lawyer and RFP Compliance Auditor. "
        "Analyze the provided contract or RFP document carefully. Identify hidden financial traps, "
        "unfair penalty clauses, liability imbalances, auto-renewal traps, and compliance gaps. "
        "You MUST cite the exact [PAGE X] number where each issue is located and provide an exact quote."
    )
    
    user_prompt = f"Audit the following document:\n\n{contract_text}"
    if custom_rules.strip():
        user_prompt += f"\n\nAdditional Company Compliance Rules to enforce:\n{custom_rules}"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=ContractAuditReport,
            temperature=0.1,
        ),
    )
    
    return ContractAuditReport.model_validate_json(response.text)
  
