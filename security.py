import re

def mask_sensitive_data(text: str) -> tuple[str, dict]:
    """
    يقوم بإخفاء الأسماء والبيانات الحساسة مؤقتاً لحماية خصوصية العقود.
    Returns: (masked_text, mapping_dict)
    """
    mapping = {}
    counter = 1
    
    # نموذج اكتشاف أرقام الحسابات، الإيميلات، أو الأسماء البارزة (كمثال توضيحي)
    # يمكنك توسيع الكشف حسب الحاجة
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    for email in emails:
        placeholder = f"[EMAIL_{counter}]"
        mapping[placeholder] = email
        text = text.replace(email, placeholder)
        counter += 1
        
    return text, mapping

def unmask_report_text(text: str, mapping: dict) -> str:
    """إعادة البيانات الحساسة لتقرير الذكاء الاصطناعي النهائي"""
    for placeholder, original in mapping.items():
        text = text.replace(placeholder, original)
    return text
  
