import os
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from auditor import (
    analyze_negotiation_timeline,
    ask_contract_question,
    audit_contract,
    compare_contracts,
    extract_document_data,
)
from schemas import OutputLanguage

app = FastAPI(
    title="Verilogix AI — Contract & RFP Intelligence API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _resolve_api_key(provided_key: Optional[str]) -> str:
    key = (provided_key or "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=400,
            detail="Missing Gemini API key. Provide api_key in request or set GEMINI_API_KEY on the server.",
        )
    return key


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "verilogix-ai-api"}


@app.post("/audit")
async def audit_endpoint(
    file: UploadFile = File(...),
    jurisdiction: str = Form("General International Commercial Law"),
    output_language: OutputLanguage = Form("English"),
    deal_breakers: str = Form(""),
    company_playbook: str = Form(""),
    custom_rules: str = Form(""),
    enable_pii_masking: bool = Form(True),
    custom_pii_terms_raw: str = Form(""),
    api_key: Optional[str] = Form(None),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a valid PDF file.")

    resolved_key = _resolve_api_key(api_key)
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        doc_meta = extract_document_data(pdf_bytes)
        custom_pii_terms = [t.strip() for t in custom_pii_terms_raw.split(",") if t.strip()]

        report = audit_contract(
            pdf_bytes=pdf_bytes,
            api_key=resolved_key,
            custom_rules=custom_rules,
            jurisdiction=jurisdiction,
            company_playbook=company_playbook,
            deal_breakers=deal_breakers,
            enable_pii_masking=enable_pii_masking,
            output_language=output_language,
            custom_pii_terms=custom_pii_terms,
            pre_extracted_text=doc_meta["extracted_text"],
        )

        payload = report.model_dump()
        payload["filename"] = file.filename
        payload["page_count"] = doc_meta["page_count"]
        payload["is_scanned"] = doc_meta["is_scanned"]
        return payload
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(exc)}") from exc


@app.post("/ask")
async def ask_endpoint(
    file: UploadFile = File(...),
    question: str = Form(...),
    jurisdiction: str = Form("General International Commercial Law"),
    output_language: OutputLanguage = Form("English"),
    api_key: Optional[str] = Form(None),
) -> dict:
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    resolved_key = _resolve_api_key(api_key)
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        doc_meta = extract_document_data(pdf_bytes)
        answer = ask_contract_question(
            pdf_bytes=pdf_bytes,
            api_key=resolved_key,
            question=question.strip(),
            jurisdiction=jurisdiction,
            output_language=output_language,
            pre_extracted_text=doc_meta["extracted_text"],
        )
        return {"filename": file.filename, "question": question.strip(), "answer": answer}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Question answering failed: {str(exc)}") from exc


@app.post("/compare")
async def compare_endpoint(
    original_file: UploadFile = File(...),
    revised_file: UploadFile = File(...),
    jurisdiction: str = Form("General International Commercial Law"),
    output_language: OutputLanguage = Form("English"),
    use_quick_diff: bool = Form(True),
    api_key: Optional[str] = Form(None),
) -> dict:
    resolved_key = _resolve_api_key(api_key)
    orig_bytes = await original_file.read()
    rev_bytes = await revised_file.read()
    if not orig_bytes or not rev_bytes:
        raise HTTPException(status_code=400, detail="Both original and revised PDFs are required.")

    try:
        orig_meta = extract_document_data(orig_bytes)
        rev_meta = extract_document_data(rev_bytes)
        comp_report = compare_contracts(
            original_bytes=orig_bytes,
            revised_bytes=rev_bytes,
            api_key=resolved_key,
            jurisdiction=jurisdiction,
            output_language=output_language,
            pre_orig_text=orig_meta["extracted_text"],
            pre_rev_text=rev_meta["extracted_text"],
            use_quick_diff=use_quick_diff,
        )
        return comp_report.model_dump()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(exc)}") from exc


@app.post("/timeline")
async def timeline_endpoint(
    files: list[UploadFile] = File(...),
    jurisdiction: str = Form("General International Commercial Law"),
    output_language: OutputLanguage = Form("English"),
    api_key: Optional[str] = Form(None),
) -> dict:
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Upload at least two contract versions.")

    resolved_key = _resolve_api_key(api_key)
    versions_payload: list[tuple[str, bytes]] = []
    for f in files:
        content = await f.read()
        if content:
            versions_payload.append((f.filename or "version.pdf", content))

    if len(versions_payload) < 2:
        raise HTTPException(status_code=400, detail="At least two non-empty PDFs are required.")

    try:
        tl_report = analyze_negotiation_timeline(
            versions=versions_payload,
            api_key=resolved_key,
            jurisdiction=jurisdiction,
            output_language=output_language,
        )
        return tl_report.model_dump()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Timeline analysis failed: {str(exc)}") from exc
  
