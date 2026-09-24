"""Regression tests against real local fixtures; never touches the live save."""
import argparse
import gc
from pathlib import Path
import struct
import tempfile
import core

def run(work,crypto_test=False):
    from unittest.mock import patch, Mock
    from types import SimpleNamespace
    import app
    class Var:
        def __init__(self,value=''):self.value=value
        def get(self):return self.value
        def set(self,value):self.value=value
    ui=SimpleNamespace(filecombo={},path=Var(),sid=Var(),status=Var(),refresh_privacy=Mock())
    candidates=[Path('C:/Steam/userdata/123/2638890/remote/win64_save/data001Slot.bin'),Path('C:/Steam/userdata/456/2638890/remote/win64_save/data001Slot.bin')]
    with patch.object(core,'discover',return_value=candidates):app.App.find(ui)
    assert ui.path.get()=='' and ui.sid.get()==''
    with patch.object(core,'discover',return_value=candidates[:1]):app.App.find(ui)
    assert ui.path.get()==str(candidates[0]) and ui.sid.get()==str(76561197960265728+123)
    with patch.object(core,'discover',return_value=candidates[1:]):app.App.find(ui)
    assert ui.path.get()==str(candidates[0]),'discovery must not replace explicit selection'
    ui.mode=Var('growth');ui.finalcheck=Var(True)
    ui.confirm=Mock();ui.confirm_hint=Mock();ui.choice_widgets={}
    with patch.object(app.ttk,'Style'):
        app.App.update_mode(ui)
        assert not ui.finalcheck.get()
        ui.confirm.configure.assert_called_with(state='disabled')
        ui.mode.set('finale');app.App.update_mode(ui)
        ui.confirm.configure.assert_called_with(state='normal')
        assert not ui.finalcheck.get(),'enabling must not imply automatic confirmation'
        ui.finalcheck.set(True);app.App.reset_confirmation(ui)
        assert not ui.finalcheck.get()
    current=work/'data001Slot.ngplus-patched.plain.bin'
    save=core.Save(current.read_bytes())
    results=[]
    # Clean NG+ eligibility and each independently earned finale unlock.
    mask_path=core.root(1)+core.BOSS+'/f1:89ACE6F9/f0:861AB707[0]'
    for original_mask in (0,1<<11,1<<17,core.FINAL_REMATCH_MASK,0x80000000):
        data=bytearray(save.data)
        struct.pack_into('<I',data,save.rec(mask_path)['offset'],original_mask)
        fixture=core.Save(data)
        candidate,_=fixture.plan(0,1,'finale',True)
        result=core.Save(candidate)
        actual=result.rec(mask_path)['value']
        assert actual==original_mask|core.PRE_FINAL_REMATCH_MASK
        assert actual & core.FINAL_REMATCH_MASK==original_mask & core.FINAL_REMATCH_MASK
        assert core.PRE_FINAL_REMATCH_MASK.bit_count()==16
        del fixture,result;gc.collect()
    results.append('16 pre-finale unlocks; both finale bits and unrelated bits preserved')
    for mode in ('growth','finale'):
        plain,report=save.plan(0,1,mode,True)
        after=core.Save(plain)
        assert after.number(core.root(1)+core.SOUL)==save.number(core.root(0)+core.SOUL)
        if mode=='finale':
            for item_id,_,amount in core.STONES:
                assert after.rec(after.item_path(1,item_id))['value']==save.rec(save.item_path(0,item_id))['value']+amount
            # The prior wrong-ID bug must never recur.
            for item_id in (1544132352,-2003256576):
                assert after.rec(after.item_path(1,item_id))['value']==save.rec(save.item_path(0,item_id))['value']
        again,_=after.plan(0,1,mode,True)
        assert plain==again,'same-source operation must be idempotent'
        results.append(mode+': idempotent, protected slots and boss records preserved')
        del after;gc.collect()
    # Reverse source/target to detect hardcoded slot 1 -> 2 logic.
    data=bytearray(save.data)
    a,b=save.region(core.root(1),core.outer(1)+'/f1:EBCC6B98')
    c,d=save.region(core.root(0),core.outer(0)+'/f1:EBCC6B98')
    assert b-a==d-c
    data[c:d],data[a:b]=save.data[a:b],save.data[c:d]
    reversed_save=core.Save(data)
    reverse,_=reversed_save.plan(1,0,'finale',True)
    reverse_save=core.Save(reverse)
    for item_id,_,amount in core.STONES:
        assert reverse_save.rec(reverse_save.item_path(0,item_id))['value']==reversed_save.rec(reversed_save.item_path(1,item_id))['value']+amount
    del reversed_save,reverse_save;gc.collect()
    data=bytearray(save.data)
    # Shuffle source item entries: lookup must follow IDs, never array position.
    left=core.root(0)+core.ITEMS+'[43]';right=core.root(0)+core.ITEMS+'[44]'
    x,y=save.rec(left)['offset'],save.rec(right)['offset']
    span=y-x
    data[x:x+span],data[y:y+span]=save.data[y:y+span],save.data[x:x+span]
    shuffled=core.Save(data)
    shifted,_=shuffled.plan(0,1,'finale',True)
    shifted_save=core.Save(shifted)
    for item_id,_,amount in core.STONES:
        assert shifted_save.rec(shifted_save.item_path(1,item_id))['value']==shuffled.rec(shuffled.item_path(0,item_id))['value']+amount
    del shuffled,shifted_save;gc.collect()
    results.append('reversed slot selection and reordered item entries passed')
    data=bytearray(save.data)
    # Invalid same-slot / empty-slot operations reject rather than guessing.
    for args in [(0,0,'growth',False),(0,2,'growth',False),(0,1,'finale',False)]:
        try:save.plan(*args)
        except ValueError:pass
        else:raise AssertionError('invalid request accepted')
    p=save.item_path(0,1080394368);r=save.rec(p)
    struct.pack_into('<I',data,r['offset'],999)
    overflow=core.Save(data)
    try:overflow.plan(0,1,'finale',True)
    except ValueError:pass
    else:raise AssertionError('overflow accepted')
    del overflow;gc.collect()
    rows=save.chests(0)
    assert len(rows)==111 and not any(r['repeat'] for r in rows)
    assert len(save.chests(0,include_repeat=True))==114
    assert len({(r['stage'],r['save_slot']) for r in rows})==111
    assert any('Power Stone' in r['contents'] for r in rows)
    assert any('Oni Stone' not in r['contents'] for r in rows)
    for state in (0,15,7):
        c=rows[0];flag=c['save_slot'];stage=c['stage'];idx=list(core.STAGES).index(stage)
        path=core.root(0)+f'/f9:8478B9CB/f{idx}:{core.STAGES[stage]}/f0:861AB707[{flag//8}]'
        record=save.rec(path);data=bytearray(save.data);shift=(flag%8)*4
        struct.pack_into('<I',data,record['offset'],(record['value'] & ~(15<<shift)) | (state<<shift))
        changed=core.Save(data)
        assert next(r for r in changed.chests(0) if r['id']==c['id'])['state']==state
        del changed;gc.collect()
    results.append('invalid selections rejected; 111 permanent chest mappings and nibble states checked')
    # Temporary fake files only: a running game must not block this unit test.
    with patch.object(core,'ensure_closed'), tempfile.TemporaryDirectory(prefix='onimusha-editor-test-') as td:
        p=Path(td)/'data001Slot.bin';p.write_bytes(b'original')
        backup=core.write_transaction(p,b'edited',b'original',{'test':True})
        assert backup.read_bytes()==b'original' and p.read_bytes()==b'edited'
        try:core.write_transaction(p,b'bad',b'original',{})
        except ValueError:pass
        else:raise AssertionError('stale destination accepted')
        assert p.read_bytes()==b'edited'
        core.write_transaction(p,backup.read_bytes(),b'edited',{'restore':True})
        assert p.read_bytes()==b'original'
    results.append('transaction backup, restore and stale-file rejection passed')
    if crypto_test:
        # SID supplied from fixture provenance, not shipped in the application.
        import os
        sid=os.environ['ONIMUSHA_TEST_SID']
        encrypted=core.crypto(plain,sid,'e')
        assert core.crypto(encrypted,sid,'d')==plain
        results.append('real encrypted candidate roundtrip passed')
    print('\n'.join(results))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--crypto',action='store_true');a=p.parse_args()
    run(a.work.resolve(),a.crypto)
