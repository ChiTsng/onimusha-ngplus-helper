"""Translation coverage, GUI construction and byte-invariance checks on a fixture."""
import ast
import gc
from pathlib import Path
from string import Formatter
from unittest.mock import patch
import app
import core
import i18n
import chest_labels
import json

HERE=Path(__file__).parent

def run():
    from collections import Counter
    assert Counter(r['kind'] for r in chest_labels.ENTRIES.values())=={'official-item':42,'official-place':27,'map-numbered-area':15,'unknown':1}
    assert chest_labels.LABELS['Earth-Shakers']==('大锤【地鸣】','大鎚【地鳴】')
    assert chest_labels.LABELS['Genma Note: Byakue']==('幻魔杂记【百秽】','幻魔雑記【百穢】')
    assert chest_labels.LABELS['Nine-story Pagoda district']==('龟顶塔','亀頂塔')
    # If local research tables are available, verify every official label against
    # the exact game MSG key, not against another hand-written translation.
    evidence=HERE.parent/'onimusha-save-work/official-name-tables.json'
    if evidence.exists():
        tables=json.loads(evidence.read_text(encoding='utf-8'))
        for text,row in chest_labels.ENTRIES.items():
            if not row['source']:continue
            records={r['key']:r for r in tables[row['source']]}
            for key in row['keys']:
                for lang in ('zh','ja'):
                    source=records[key][lang]
                    if row['kind'].startswith('official-'):assert row[lang]==source,(text,lang)
                    else:assert row[lang].startswith(source),(text,lang)
    rows=json.loads((HERE/'chests.json').read_text(encoding='utf-8'))
    for row in rows:
        assert row['area'] in chest_labels.LABELS,row['area']
        for part in row['contents'].split(' / '):
            assert part.rsplit(' × ',1)[0] in chest_labels.LABELS,part
    for name in ('app.py','core.py'):
        tree=ast.parse((HERE/name).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='tr' and node.args and isinstance(node.args[0],ast.Constant):
                assert node.args[0].value in i18n.MESSAGES,node.args[0].value
    fmt=Formatter()
    for key,translations in i18n.MESSAGES.items():
        fields={n for _,n,_,_ in fmt.parse(key) if n is not None}
        assert len(translations)==2
        for value in translations:
            assert value and {n for _,n,_,_ in fmt.parse(value) if n is not None}==fields,key
    fixture=HERE.parent/'onimusha-save-work/data001Slot.ngplus-patched.plain.bin'
    save=core.Save(fixture.read_bytes())
    reference=None
    for lang in ('zh','en','ja'):
        i18n.set_language(lang)
        for row in rows:
            translated=chest_labels.contents(row['contents'])
            assert translated.count(' × ')==row['contents'].count(' × ')
            assert [p.rsplit(' × ',1)[-1] for p in translated.split(' / ') if ' × ' in p]==[p.rsplit(' × ',1)[-1] for p in row['contents'].split(' / ') if ' × ' in p]
            if lang=='en':assert translated==row['contents']
        candidate,report=save.plan(0,1,'finale',True)
        if reference is None:reference=candidate
        assert reference==candidate,'language must never change save bytes'
        assert i18n.tr('力石') in '\n'.join(report['changes'])
        with patch.object(core,'discover',return_value=[]):
            ui=app.App(lang);ui.withdraw();ui.update_idletasks()
            assert ui.title()==i18n.tr('鬼武者 · 周目继承助手 0.9')
            assert ui.confirm.instate(['disabled'])
            ui.mode.set('finale');ui.confirm.invoke();assert ui.finalcheck.get()
            ui.source.set('1 | fixture');assert not ui.finalcheck.get()
            assert ui.slot(ui.source)==0
            ui.save=save;ui.current=lambda:None
            ui.chests();ui.update_idletasks()
            # Switching is denied while work is in progress and can be cancelled.
            other='en' if lang!='en' else 'ja'
            label=next(k for k,v in i18n.LANGUAGES.items() if v==other)
            ui.busy=True;ui.language_choice.set(label);ui.change_language()
            assert ui.next_language is None
            ui.busy=False;ui.language_choice.set(label)
            with patch.object(app.messagebox,'askyesno',return_value=False):ui.change_language()
            assert ui.next_language is None
            ui.language_choice.set(label)
            with patch.object(app.messagebox,'askyesno',return_value=True):ui.change_language()
            assert ui.next_language==other
        gc.collect()
        print(lang+': GUI, chest list, language switch and identical save bytes passed')
    i18n.set_language('zh')
    print('Translation keys and formatting placeholders passed')

if __name__=='__main__':run()
