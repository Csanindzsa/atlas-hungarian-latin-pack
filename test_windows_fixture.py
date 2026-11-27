"""Exercise installer against explicit synthetic files on a Windows SSH host, never the installed Atlas.

Env: ATLAS_TEST_HOST (ssh alias of the Windows test machine), ATLAS_TEST_USERPROFILE (e.g. C:\\Users\\me).

Covers: offline staging, source immutability, install (variant A), idempotence, switch to variant B,
restore (twice), corrupt-patch rejection, unknown-file rejection.
"""
from pathlib import Path
import base64, json, os, shutil, subprocess, uuid
from pack_builder import ROOT, hashfile, make_delta

HOST = os.environ.get('ATLAS_TEST_HOST') or SystemExit('Set ATLAS_TEST_HOST (ssh alias of a Windows test machine)')
PROFILE = os.environ.get('ATLAS_TEST_USERPROFILE') or SystemExit('Set ATLAS_TEST_USERPROFILE (e.g. C:\\Users\\me)')
if isinstance(HOST, SystemExit): raise HOST
if isinstance(PROFILE, SystemExit): raise PROFILE
suffix = uuid.uuid4().hex[:12]
local = ROOT/'build'/('windows-fixture-'+suffix)
local.mkdir(parents=True)
shutil.copy2(ROOT/'Install-Pack.ps1', local/'Install-Pack.ps1')
paths = ['Human Anatomy Atlas_Data/resources.assets', 'Human Anatomy Atlas_Data/Managed/Assembly-UnityScript.dll']
variants = {}
for v in ('magyar', 'latinos', 'latinkviz'):
    entries = []
    for i, path in enumerate(paths):
        old = local/'source'/path; old.parent.mkdir(parents=True, exist_ok=True)
        if not old.exists():
            old.write_bytes(('SYNTHETIC ORIGINAL '+str(i)+'|').encode()*100)
        new = local/('expected-'+v+'-'+str(i))
        new.write_bytes(('SYNTHETIC PATCH ŐŰ '+v+' '+str(i)+'|').encode()*120)
        ops, data = make_delta(old, new, [])
        literal = local/('file-'+v+'-'+str(i)+'.literals'); literal.write_bytes(data)
        entries.append({'path': path, 'source_sha256': hashfile(old), 'target_sha256': hashfile(new), 'source_size': old.stat().st_size,
                        'target_size': new.stat().st_size, 'operations': ops, 'literal_file': literal.name, 'literal_sha256': hashfile(literal)})
    variants[v] = {'files': entries}
(local/'manifest.json').write_text(json.dumps({'schema': 2, 'variants': variants}))
remote_rel = 'AgentShare/artifacts/'+local.name
remote_root = PROFILE.rstrip('\\')+'\\'+remote_rel.replace('/', '\\')
subprocess.run(['scp', '-q', '-r', '-o', 'BatchMode=yes', str(local), HOST+':AgentShare/artifacts/'], check=True)
script = r'''$ErrorActionPreference='Stop'; $r='REMOTE'; $code=[ScriptBlock]::Create([IO.File]::ReadAllText($r+'\Install-Pack.ps1')); $source=$r+'\source'; $m=Get-Content ($r+'\manifest.json') -Raw | ConvertFrom-Json
function Assert-State($kind) { foreach($f in $m.variants.magyar.files) { $h=(Get-FileHash (Join-Path $source $f.path)).Hash.ToLowerInvariant(); if($kind -eq 'source'){$e=$f.source_sha256}else{$e=(@($m.variants.$kind.files | Where-Object {$_.path -eq $f.path})[0]).target_sha256}; if($h -ne $e){throw ('State mismatch: '+$kind)} } }
& $code -PackDirectory $r -AtlasDirectory $source -Variant latinos -OutputDirectory ($r+'\staged'); Assert-State 'source'
foreach($f in $m.variants.latinos.files){ if((Get-FileHash (Join-Path ($r+'\staged') $f.path)).Hash.ToLowerInvariant() -ne $f.target_sha256){throw 'Offline output mismatch'} }
& $code -PackDirectory $r -AtlasDirectory $source -Variant magyar; Assert-State 'magyar'
& $code -PackDirectory $r -AtlasDirectory $source -Variant magyar; Assert-State 'magyar'
& $code -PackDirectory $r -AtlasDirectory $source -Variant latinos; Assert-State 'latinos'
& $code -PackDirectory $r -AtlasDirectory $source -Variant latinkviz; Assert-State 'latinkviz'
& $code -PackDirectory $r -AtlasDirectory $source -Restore; Assert-State 'source'
& $code -PackDirectory $r -AtlasDirectory $source -Restore; Assert-State 'source'
[IO.File]::WriteAllText(($r+'\file-magyar-0.literals'),'corrupted synthetic test data'); $rejected=$false; try{& $code -PackDirectory $r -AtlasDirectory $source -Variant magyar}catch{$rejected=$true}; if(!$rejected){throw 'Corrupt patch was accepted'}; Assert-State 'source'
$f0=Join-Path $source $m.variants.magyar.files[0].path; [IO.File]::AppendAllText($f0,'x'); $rejected=$false; try{& $code -PackDirectory $r -AtlasDirectory $source -Variant latinos}catch{$rejected=$true}; if(!$rejected){throw 'Unknown source was accepted'}
Write-Output 'WINDOWS_FIXTURE_PASS: offline staging, source immutability, install, idempotence, variant switch, restore (x2), corrupt-patch rejection, unknown-file rejection'; Remove-Item -LiteralPath $r -Recurse -Force
'''.replace('REMOTE', remote_root)
encoded = base64.b64encode(script.encode('utf-16le')).decode()
r = subprocess.run(['ssh', '-o', 'BatchMode=yes', HOST, 'powershell -NoProfile -EncodedCommand '+encoded], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
text = r.stdout.decode('utf-8', errors='replace'); print(text)
shutil.rmtree(local, ignore_errors=True)
if r.returncode or 'WINDOWS_FIXTURE_PASS' not in text: raise SystemExit('Windows fixture verification failed')
