"""Structural, transactional editor. No game installation is required."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from datetime import datetime

from dsss import Reader, parse_class
from i18n import tr

BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
SLOTS = 'top[0]:DBE3F199/f1:FEEA1F9B'
COSMETICS = 'top[0]:DBE3F199/f0:AA0642D6/f0:695A3627/f0:2180405A/f15:0630456E'
SHARED_REMATCH = tuple('top[0]:DBE3F199/f0:AA0642D6/f0:695A3627/f0:2180405A/'+s for s in ('f18:AA0E1B11','f19:B19E59CC','f20:AE0BD931'))
SYSTEM = '/f28:87FA23FF'
BOSS = '/f33:CAD768A6'
# app.RematchBoss.ID: EM504_00_01 = 11 (late Benkei), EM514_00_00 = 17.
FINAL_REMATCH_MASK = (1 << 11) | (1 << 17)
PRE_FINAL_REMATCH_MASK = ((1 << 18) - 1) & ~FINAL_REMATCH_MASK
SOUL = '/f2:45C5772D/f2:D9E97C41'
NODES = '/f11:EDF49C15/f16:5F3AB015'
ITEMS = '/f4:2A5A76C7'
COSMETIC_IDS = (28716, 30419, 31281, 13810, 18329, 16477, 413)
COSMETIC_NAMES = ('藏笼手羽织2', '条纹羽织2', '天鹅绒羽织2', '朝雾羽织2', '鬼羽织2', '火消羽织2', '轻装和服2')
STONES = ((1080394368, '力石', 53), (-111058624, '鬼石', 55))
STAGES = {100:'60405B88',200:'7807C8B5',201:'E7DF3144',202:'B59E087E',203:'4652A245',204:'3C7483DE',206:'C2E96B13',209:'CDB5FE75',210:'1DEA1F79',211:'00817BE3',212:'FC1F62E2',213:'2558FB07',214:'48FD1554',215:'CE4077D1',218:'2DC4B845',700:'21FA65F3',900:'5278258B'}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def outer(slot):
    return f'{SLOTS}[{slot}]'

def root(slot):
    return outer(slot)+'/f0:695A3627'

def mandrake(raw):
    if len(raw) != 16:
        raise ValueError(tr('不支持的保护数值长度'))
    value, multiplier = struct.unpack('<qq', raw)
    if multiplier <= 0 or value % multiplier:
        raise ValueError(tr('存档保护数值无效'))
    return value // multiplier

class Save:
    def __init__(self, data):
        if not 100_000 <= len(data) <= 20_000_000:
            raise ValueError(tr('存档长度异常或解密失败'))
        self.data = bytes(data)
        reader, records, index = Reader(self.data), [], 0
        while reader.pos < len(data):
            h = reader.u32()
            parse_class(reader, f'top[{index}]:{h:08X}', records)
            index += 1
        if reader.pos != len(data):
            raise ValueError(tr('存档未完整解析'))
        self.records = {r['path']:r for r in records}
        if len(self.records) != len(records):
            raise ValueError(tr('存档存在重复字段'))
        if self.records.get(SLOTS, {}).get('length') != 21:
            raise ValueError(tr('此版本的存档栏位结构尚不支持'))
        for slot in range(21):
            if self.records.get(root(slot), {}).get('field_count') != 78:
                raise ValueError(tr('存档结构与已验证版本不符'))

    def rec(self, path, typ=None, size=None):
        r = self.records.get(path)
        if r is None or (typ and r['type'] != typ) or (size and r.get('size') != size):
            raise ValueError(tr('不支持的字段结构：')+path)
        return r

    def raw(self, path):
        r = self.rec(path)
        return self.data[r['offset']:r['offset']+r['size']]

    def number(self, path):
        return mandrake(self.raw(path))

    def region(self, path, next_path):
        return self.rec(path)['field_header_offset'], self.rec(next_path)['field_header_offset']

    def info(self, slot):
        title = self.rec(outer(slot)+'/f2:65EFD138')['value']
        detail = self.rec(outer(slot)+'/f3:BC922B61')['value']
        return dict(slot=slot, occupied=bool(title), title=title.replace('\t',' · '),
                    detail=re.sub('<[^>]+>','',detail).replace('\t',' · '),
                    packed=self.number(root(slot)+SYSTEM+'/f1:8E5C6227'),
                    clears=self.number(root(slot)+SYSTEM+'/f0:660F397B'))

    def item_path(self, slot, item_id):
        base = root(slot)+ITEMS
        n = self.rec(base, 'ArrayMeta')['length']
        matches = [f'{base}[{i}]/f1:E55B3687' for i in range(n)
                   if self.rec(f'{base}[{i}]/f0:183A65D3')['value'] == item_id]
        if len(matches) != 1:
            raise ValueError(tr('道具 {v0} 未找到或出现重复；停止修改',v0=item_id))
        return matches[0]

    def chests(self, slot, include_repeat=False):
        if not self.info(slot)['occupied']:
            raise ValueError(tr('来源栏位为空'))
        catalog = json.loads((BASE/'chests.json').read_text(encoding='utf-8'))
        result = []
        for c in catalog:
            if c['repeat'] and not include_repeat:
                continue
            stage, flag = c['stage'], c['save_slot']
            idx = list(STAGES).index(stage)
            path = root(slot)+f'/f9:8478B9CB/f{idx}:{STAGES[stage]}/f0:861AB707[{flag//8}]'
            word = self.rec(path,'U32',4)['value']
            state = (word >> ((flag%8)*4)) & 15
            status = {0:tr('未开启'),15:tr('已开启')}.get(state, tr('未识别状态 {v0}',v0=state))
            if c['repeat']:
                status += '（'+c['repeat_reason']+'）'
            result.append(dict(c,state=state,status=status))
        return result

    def plan(self, source, target, mode, finale_confirmed=False):
        if source == target or source not in range(10) or target not in range(10):
            raise ValueError(tr('请选择不同的来源和目标手动栏位'))
        if mode not in ('growth','finale'):
            raise ValueError(tr('未知修改模式'))
        si, ti = self.info(source), self.info(target)
        if not si['occupied'] or not ti['occupied']:
            raise ValueError(tr('来源和目标都必须是游戏内已保存的栏位'))
        if ti['packed'] != 2 or ti['clears'] < 1:
            raise ValueError(tr('目标必须是游戏内正常创建的鬼杀 NG+；当前状态不在已验证范围'))
        if si['clears'] < 1:
            raise ValueError(tr('来源必须是已通关存档'))
        if mode == 'finale' and (not finale_confirmed or si['packed'] not in (8,9,10)):
            raise ValueError(tr('请确认来源已通关并回到最终两段主线之前；当前来源须带通关标记'))
        out = bytearray(self.data)
        allowed, changes = [], []

        def write(offset, raw):
            if offset < 0 or offset+len(raw)>len(out):
                raise ValueError(tr('字段越界'))
            out[offset:offset+len(raw)] = raw
            allowed.append((offset,offset+len(raw)))

        def copy_value(a,b):
            ra, rb = self.rec(a), self.rec(b)
            if ra['type'] != rb['type'] or ra.get('size') != rb.get('size'):
                raise ValueError(tr('来源与目标字段不兼容'))
            write(rb['offset'],self.raw(a))

        if mode == 'growth':
            a,b = root(source)+NODES,root(target)+NODES
            na,nb = self.rec(a,'ArrayMeta'),self.rec(b,'ArrayMeta')
            if na['length'] != 192 or nb['length'] != 192:
                raise ValueError(tr('技能树布局尚未验证'))
            count=0
            for i in range(192):
                pa,pb=f'{a}[{i}]',f'{b}[{i}]'
                self.rec(pa,'Struct',16);self.rec(pb,'Struct',16)
                count += self.raw(pa)!=self.raw(pb)
                copy_value(pa,pb)
            copy_value(root(source)+SOUL,root(target)+SOUL)
            changes += [tr('复制数值强化：{v0} 项强化记录发生变化',v0=count),
                        tr('红魂：{v0} → {v1}',v0=self.number(root(target) + SOUL),v1=self.number(root(source) + SOUL))]
        else:
            sa,se=self.region(root(source),outer(source)+'/f1:EBCC6B98')
            ta,te=self.region(root(target),outer(target)+'/f1:EBCC6B98')
            # Raw block copying is supported only when every relative field layout matches.
            def layout(slot,start):
                p=root(slot)
                return [(k[len(p):],r['type'],r['offset']-start,r.get('size'),r.get('length'),r.get('class_hash'))
                        for k,r in self.records.items() if k==p or k.startswith(p+'/')]
            if se-sa != te-ta or layout(source,sa)!=layout(target,ta):
                raise ValueError(tr('两栏位序列化布局不同，无法安全同步此存档'))
            write(ta,self.data[sa:se])
            for first,last in ((SYSTEM,'/f29:299A4B78'),(BOSS,'/f34:DEF45888')):
                x,y=self.region(root(target)+first,root(target)+last)
                write(x,self.data[x:y])
            changes.append(tr('以来源重建目标剧情、任务、地图、养成、背包与收集状态；保留目标周目身份与再战成绩'))
            for item_id,name,amount in STONES:
                sp=self.item_path(source,item_id)
                # Target inventory now has source layout, including its item-array index.
                tp=sp.replace(root(source),root(target),1)
                r=self.rec(tp,'U32',4)
                before=self.rec(sp,'U32',4)['value']
                if before+amount>999:
                    raise ValueError(tr('{v0}补偿后超过999，停止修改',v0=tr(name)))
                write(r['offset'],struct.pack('<I',before+amount))
                changes.append(tr('{v0}：来源 {v1} + 补偿 {v2} = {v3}',v0=tr(name),v1=before,v2=amount,v3=before + amount))
            shop=root(target)+'/f34:DEF45888/f0:A8426CC0'
            for i in range(self.rec(shop,'ArrayMeta')['length']):
                r=self.rec(f'{shop}[{i}]','U32',4)
                write(r['offset'],struct.pack('<I',0))
            changes.append(tr('已解锁商店兑换库存补满'))
            mask=root(target)+BOSS+'/f1:89ACE6F9/f0:861AB707[0]'
            r=self.rec(mask,'U32',4)
            write(r['offset'],struct.pack('<I',r['value']|PRE_FINAL_REMATCH_MASK))
            changes.append(tr('补齐最终连战前16项鬼杀再战资格；弁庆（武器解放）与最终源义经不提前解锁，已有资格不撤销'))
            entries=[f'{COSMETICS}[{i}]' for i in range(self.rec(COSMETICS,'ArrayMeta')['length'])]
            ids=[self.number(p) for p in entries]
            empty=[p for p,v in zip(entries,ids) if v==46]
            missing=[(i,n) for i,n in zip(COSMETIC_IDS,COSMETIC_NAMES) if i not in ids]
            if len(empty)<len(missing):
                raise ValueError(tr('共享外观列表空位不足'))
            for p,(item_id,name) in zip(empty,missing):
                self.rec(p,'Struct',16)
                _,m=struct.unpack('<qq',self.raw(p))
                write(self.rec(p)['offset'],struct.pack('<qq',item_id*m,m))
            changes.append(tr('共享外观补齐（所有栏位可见）：')+(', '.join(tr(n) for _,n in missing) or tr('均已拥有')))
            changes.append(tr('选档界面的旧时间/任务摘要保留，进入游戏并重新保存后刷新'))
        # Prove that every changed byte belongs to the explicitly authorized regions.
        permitted=bytearray(len(out))
        for a,b in allowed:
            permitted[a:b]=b'\1'*(b-a)
        if any(a!=b and not permitted[i] for i,(a,b) in enumerate(zip(self.data,out))):
            raise AssertionError(tr('修改越过允许范围'))
        candidate=Save(out)
        for prefix in SHARED_REMATCH:
            n=self.rec(prefix,'ArrayMeta')['length']
            if candidate.rec(prefix,'ArrayMeta')['length']!=n or any(self.raw(f'{prefix}[{i}]')!=candidate.raw(f'{prefix}[{i}]') for i in range(n)):
                raise AssertionError(tr('再战成绩发生变化'))
        for slot in range(21):
            if slot==target:
                continue
            a,b=self.region(root(slot),outer(slot)+'/f1:EBCC6B98')
            if candidate.data[a:b]!=self.data[a:b]:
                raise AssertionError(tr('未选栏位发生变化'))
        # Per-slot eligibility: only the Carnage availability mask may differ.
        a,b=self.region(root(target)+BOSS,root(target)+'/f34:DEF45888')
        boss=bytearray(candidate.data[a:b])
        if mode=='finale':
            r=self.rec(root(target)+BOSS+'/f1:89ACE6F9/f0:861AB707[0]')
            boss[r['offset']-a:r['offset']-a+4]=self.data[r['offset']:r['offset']+4]
        if bytes(boss)!=self.data[a:b]:
            raise AssertionError(tr('再战成绩发生变化'))
        return bytes(out),dict(mode=mode,source_slot=source+1,target_slot=target+1,
                              changes=changes,input_sha256=sha(self.data),output_sha256=sha(out))

def steam_id(path):
    parts=Path(path).parts
    for i,part in enumerate(parts):
        if part.lower()=='userdata' and i+1<len(parts) and parts[i+1].isdigit():
            return str(76561197960265728+int(parts[i+1]))
    return ''

def discover():
    paths=set()
    bases=[]
    if os.name=='nt':
        import winreg
        for hive,key in ((winreg.HKEY_CURRENT_USER,r'Software\Valve\Steam'),(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\WOW6432Node\Valve\Steam')):
            try:
                with winreg.OpenKey(hive,key) as k:
                    for field in ('SteamPath','InstallPath'):
                        try: bases.append(Path(winreg.QueryValueEx(k,field)[0]))
                        except OSError: pass
            except OSError: pass
    for env in ('ProgramFiles(x86)','ProgramFiles'):
        if os.environ.get(env): bases.append(Path(os.environ[env])/'Steam')
    for b in bases:
        paths.update(b.glob('userdata/*/2638890/remote/win64_save/data001Slot.bin'))
    return sorted(paths,key=str)

def ensure_closed():
    if os.name=='nt':
        result=subprocess.run(['tasklist','/FI','IMAGENAME eq OnimushaWotS.exe','/FO','CSV','/NH'],
                              capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=15)
        if result.returncode or b'OnimushaWotS.exe' in result.stdout:
            raise ValueError(tr('请先保存并完全退出游戏，再执行此操作'))

def crypto(data, sid, mode):
    if not re.fullmatch(r'7656119\d{10}',str(sid)):
        raise ValueError(tr('请输入有效的17位 SteamID64；手动选择备份时需填写原账号ID'))
    engine=BASE/'vendor'/'mandarin-juice-cli.exe'
    profile=BASE/'vendor'/'Onimusha Way of the Sword v1.bin'
    if not engine.is_file() or not profile.is_file():
        raise ValueError(tr('加密组件缺失，请完整解压发布包'))
    with tempfile.TemporaryDirectory(prefix='onimusha-editor-') as td:
        td=Path(td)
        local=td/engine.name
        shutil.copy2(engine,local)
        inp=td/'input';inp.mkdir()
        (inp/'data001Slot.bin').write_bytes(data)
        env=os.environ.copy()
        env['DOTNET_ROOT']=str(BASE/'vendor'/'dotnet')
        env['DOTNET_ROOT_X64']=env['DOTNET_ROOT']
        result=subprocess.run([str(local),'-m',mode,'-g',str(profile),'-p',str(inp),'-u',str(sid),'-q'],
                              cwd=td,env=env,capture_output=True,timeout=90,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        files=list((td/'_OUTPUT').rglob('data001Slot.bin'))
        if result.returncode or len(files)!=1:
            raise ValueError(tr('加密/解密失败，请检查SteamID、文件版本和完整运行库。')+
                             result.stderr.decode('utf-8',errors='replace')[-600:])
        return files[0].read_bytes()

def write_transaction(path, encrypted, expected, report):
    """Backup before replacement. A stale destination always aborts."""
    ensure_closed()
    path=Path(path)
    current=path.read_bytes() if path.exists() else None
    if current!=expected:
        raise ValueError(tr('文件在读取后已变化；请重新读取并预览'))
    backup_dir=path.parent/'OnimushaEditor_Backups'
    backup_dir.mkdir(exist_ok=True)
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup=backup_dir/f'{stamp}-{path.name}'
    if current is not None:
        with backup.open('xb') as f:
            f.write(current);f.flush();os.fsync(f.fileno())
    manifest=backup_dir/f'{stamp}-report.json'
    manifest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    fd,tmp=tempfile.mkstemp(prefix='.onimusha-',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(encrypted);f.flush();os.fsync(f.fileno())
        ensure_closed()
        if (path.read_bytes() if path.exists() else None)!=expected:
            raise ValueError(tr('写回前检测到存档变化，已取消'))
        os.replace(tmp,path)
        if path.read_bytes()!=encrypted:
            raise IOError(tr('写回校验失败；原文件已备份'))
    finally:
        if Path(tmp).exists(): Path(tmp).unlink()
    return backup if current is not None else manifest
