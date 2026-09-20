"""Build from the audited research workspace; explicit distribution allowlist."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

HERE=Path(__file__).resolve().parent

def prepare(work):
    shutil.copy2(work/'parse_dsss_payload.py',HERE/'dsss.py')
    # Harden parser size/alignment limits before accepting arbitrary user files.
    p=HERE/'dsss.py'
    src=p.read_text(encoding='utf-8')
    src=src.replace('if self.pos + count > len(self.data):','if count < 0 or self.pos + count > len(self.data):')
    src=src.replace('if size > 1:\n', 'if size not in (1, 2, 4, 8, 16, 32):\n            raise ValueError("unsupported alignment")\n        if size > 1:\n')
    src=src.replace('length > 10_000_000','length > 100_000')
    src=src.replace('field_count > 1_000_000','field_count > 10_000')
    p.write_text(src,encoding='utf-8')
    # Use the reviewed complete catalog; never regenerate the obsolete Oni-only subset.
    catalog=json.loads((HERE/'chests.json').read_text(encoding='utf-8'))
    assert len(catalog)==114 and sum(not r['repeat'] for r in catalog)==111
    vendor=HERE/'vendor';vendor.mkdir(exist_ok=True)
    shutil.copy2(work/'MandarinJuice-release/win-x64/MandarinJuice/mandarin-juice-cli.exe',vendor)
    shutil.copy2(work/'MandarinJuice-release/_profiles/_profiles/Onimusha Way of the Sword v1.bin',vendor)
    shutil.copy2(work/'MandarinJuice/LICENSE',vendor/'MandarinJuice-LICENSE.txt')
    shutil.copytree(work/'dotnet10',vendor/'dotnet',dirs_exist_ok=True)
    notices=HERE/'notices';notices.mkdir(exist_ok=True)
    py=Path(sys.base_prefix)
    for p in (py/'LICENSE.txt',py/'tcl/tcl8.6/license.terms',py/'tcl/tk8.6/license.terms'):
        if p.exists():shutil.copy2(p,notices/(p.parent.name+'-'+p.name))
    import PyInstaller
    for p in Path(PyInstaller.__file__).parent.parent.glob('pyinstaller-*.dist-info/licenses/*'):
        if p.is_file():shutil.copy2(p,notices/('PyInstaller-'+p.name))

def build():
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir',
                    '--name','OnimushaNGPlus','--add-data','chests.json;.',
                    '--add-data','official_labels.json;.',
                    '--add-data','vendor;vendor','--add-data','notices;notices','app.py'],cwd=HERE,check=True)
    dist=HERE/'dist/OnimushaNGPlus'
    for name in ('README.md','THIRD_PARTY.md','LICENSE'):
        shutil.copy2(HERE/name,dist/name)
    with zipfile.ZipFile(HERE/'dist/OnimushaNGPlus-0.9-win64.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in dist.rglob('*'):
            if p.is_file():z.write(p,Path('OnimushaNGPlus')/p.relative_to(dist))
    with zipfile.ZipFile(HERE/'dist/OnimushaNGPlus-0.9-source.zip','w',zipfile.ZIP_DEFLATED) as z:
        for name in ('app.py','core.py','i18n.py','chest_labels.py','official_labels.json','dsss.py','chests.json','build.py','tests.py','tests_i18n.py','README.md','THIRD_PARTY.md','LICENSE','REQUIREMENTS.md'):
            z.write(HERE/name,name)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,default=HERE.parent/'onimusha-save-work');p.add_argument('--prepare-only',action='store_true')
    a=p.parse_args()
    if a.work.is_dir():
        prepare(a.work.resolve())
    elif not all((HERE/n).exists() for n in ('dsss.py','chests.json','official_labels.json','vendor','notices')):
        raise SystemExit('Copy vendor and notices from the binary package _internal directory next to this script before building.')
    if not a.prepare_only:build()
