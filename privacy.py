"""Presentation-only redaction; never use redacted text for file operations."""
import re

def redact(text, secrets=()):
    text=str(text)
    for secret in sorted({str(s) for s in secrets if s},key=len,reverse=True):
        text=text.replace(secret,'••••')
    text=re.sub(r'(?i)(\buserdata[\\/]+)\d+',r'\1••••',text)
    text=re.sub(r'(?i)(\bUsers[\\/]+)[^\\/\r\n\'\"]+',r'\1••••',text)
    return re.sub(r'(?<!\d)7656119\d{10}(?!\d)','••••',text)
