import re


def mask_sensitive_data(text: str, custom_terms: list[str] | None = None) -> tuple[str, dict]:
    """
    Temporarily masks sensitive identifiers locally before sending text to the LLM.
    Returns: (masked_text, mapping_dict)
    """
    mapping: dict[str, str] = {}
    counter = 1

    # 1. Emails
    email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    for match in email_pattern.findall(text):
        if match not in mapping.values():
            placeholder = f"[EMAIL_{counter}]"
            mapping[placeholder] = match
            counter += 1

    # 2. Phone numbers (international or local sequences with optional + / dashes / spaces)
    phone_pattern = re.compile(r"(?<!\w)(?:\+?\d[\d\s\-().]{7,}\d)(?!\w)")
    for match in phone_pattern.findall(text):
        cleaned = match.strip()
        digits_only = re.sub(r"\D", "", cleaned)
        if 8 <= len(digits_only) <= 15 and cleaned not in mapping.values():
            placeholder = f"[PHONE_{counter}]"
            mapping[placeholder] = cleaned
            counter += 1

    # 3. IBAN / Account / Long numeric reference IDs (12+ digits/alphanumerics)
    account_pattern = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b|\b\d{12,24}\b")
    for match in account_pattern.findall(text):
        if match not in mapping.values():
            placeholder = f"[REF_ID_{counter}]"
            mapping[placeholder] = match
            counter += 1

    # 4. User-specified sensitive terms/names (optional)
    if custom_terms:
        for term in sorted({t.strip() for t in custom_terms if t and t.strip()}, key=len, reverse=True):
            if term not in mapping.values():
                placeholder = f"[REDACTED_{counter}]"
                mapping[placeholder] = term
                counter += 1

    # Sort longest originals first so substrings don't partially collide
    sorted_pairs = sorted(mapping.items(), key=lambda item: len(item[1]), reverse=True)
    masked_text = text
    for placeholder, original in sorted_pairs:
        masked_text = masked_text.replace(original, placeholder)

    return masked_text, mapping


def unmask_report_text(text: str | None, mapping: dict[str, str]) -> str:
    """Restores original sensitive values in AI output text."""
    if not text:
        return ""
    unmasked = text
    for placeholder, original in mapping.items():
        unmasked = unmasked.replace(placeholder, original)
    return unmasked
                                    
