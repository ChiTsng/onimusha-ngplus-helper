"""Game-localized short names; external map numbering remains clearly identified."""
import json
from pathlib import Path
import sys
import i18n

BASE=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
CATALOG=json.loads((BASE/'official_labels.json').read_text(encoding='utf-8'))
ENTRIES=CATALOG['labels']
LABELS={key:(row['zh'],row['ja']) for key,row in ENTRIES.items()}

def label(text):
    if i18n.language=='en':return text
    row=ENTRIES.get(text)
    return row[i18n.language] if row else text

def contents(text):
    result=[]
    for part in text.split(' / '):
        if ' × ' in part:
            name,amount=part.rsplit(' × ',1)
            result.append(label(name)+' × '+amount)
        else:result.append(label(part))
    return ' / '.join(result)
