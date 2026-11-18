import re


def mask_sensitive_data(text: str) -> tuple[str, dict]:
    """
    Temporarily masks sensitive identifiers to protect contract privacy.
    Returns: (masked_text, mapping_dict)
    """
    mapping = {}
    counter = 1

    # Detect email addresses and replace them with placeholders
    emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    for email in emails:
        placeholder = f"[EMAIL_{counter}]"
        mapping[placeholder] = email
        text = text.replace(email, placeholder)
        counter += 1

    return text, mapping


def unmask_report_text(text: str, mapping: dict) -> str:
    """Restores original sensitive values in the final AI output."""
    for placeholder, original in mapping.items():
        text = text.replace(placeholder, original)
    return text
    
