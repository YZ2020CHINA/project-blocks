"""Refresh the tool-owned runtime template before installing."""
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parent.parent
SKILL=ROOT/'integration/plugin/skills/project-blocks'
TEMPLATE=SKILL/'assets/template'
for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
    shutil.copy2(ROOT/name,SKILL.parent.parent/name)
    shutil.copy2(ROOT/name,TEMPLATE/name)
for name in ('app/index.html','app/blocks.css','app/blocks.js','server.py'):
    target=TEMPLATE/name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/name,target)
shutil.copy2(SKILL/'scripts/project_blocks.py',TEMPLATE/'runtime.py')
shutil.copy2(ROOT/'integration/template-start.py',TEMPLATE/'start.py')
(TEMPLATE/'launch.ps1').write_text('''$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$runtimePython = Join-Path $env:USERPROFILE '.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe'
if (Test-Path -LiteralPath $runtimePython) {
    & $runtimePython (Join-Path $PSScriptRoot 'start.py')
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 (Join-Path $PSScriptRoot 'start.py')
} else {
    python (Join-Path $PSScriptRoot 'start.py')
}
''',encoding='utf-8')
(TEMPLATE/'启动.cmd').write_bytes(b'@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1"\r\nif errorlevel 1 pause\r\n')
(TEMPLATE/'.gitignore').write_text('.runtime.json\n.initialize.lock\n*.log\n__pycache__/\ndata/*.tmp\ndata/*.backup.json\n',encoding='utf-8')
print(TEMPLATE)
