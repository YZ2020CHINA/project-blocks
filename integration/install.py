"""Install a personal local plugin and global automatic project rule."""
from pathlib import Path
from datetime import datetime
import json
import shutil

SOURCE=Path(__file__).resolve().parent
home=Path.home()
plugin=home/'.codex/plugins/project-blocks'
market=home/'.agents/plugins/marketplace.json'
agents=home/'.codex/AGENTS.md'
stamp=datetime.now().strftime('%Y%m%d-%H%M%S')

def backup(path):
    if path.exists():
        shutil.copy2(path,path.with_name(path.name+'.'+stamp+'.bak'))

if plugin.exists():
    current=json.loads((plugin/'plugin.json').read_text(encoding='utf-8'))
    if current.get('name')!='project-blocks':
        raise RuntimeError('安装路径已被其他插件占用')
plugin.parent.mkdir(parents=True,exist_ok=True)
shutil.copytree(SOURCE/'plugin',plugin,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))

catalog=json.loads(market.read_text(encoding='utf-8-sig')) if market.exists() else dict(name='azhou-personal',interface=dict(displayName='Azhou 的本地工具'),plugins=[])
if not isinstance(catalog.get('plugins'),list) or not catalog.get('name'):
    raise ValueError('个人插件目录格式不兼容，未更改')
entry=dict(name='project-blocks',source=dict(source='local',path='./.codex/plugins/project-blocks'),policy=dict(installation='AVAILABLE',authentication='ON_INSTALL'),category='Productivity')
catalog['plugins']=[p for p in catalog['plugins'] if p.get('name')!='project-blocks']+[entry]
backup(market)
market.parent.mkdir(parents=True,exist_ok=True)
market.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')

old=agents.read_text(encoding='utf-8-sig') if agents.exists() else ''
start,end='<!-- project-blocks:auto-project:start -->','<!-- project-blocks:auto-project:end -->'
rule=(SOURCE/'global-rule.md').read_text(encoding='utf-8').strip().replace('__PROJECT_BLOCKS_SKILL_PATH__',(plugin/'skills/project-blocks/SKILL.md').as_posix())
if start in old:
    if end not in old:
        raise ValueError('全局规则标记不完整，未替换')
    a,b=old.index(start),old.index(end)+len(end)
    merged=old[:a]+rule+old[b:]
else:
    merged=old.rstrip()+'\n\n'+rule+'\n'
backup(agents)
agents.write_text(merged.lstrip('\n'),encoding='utf-8')
print(json.dumps(dict(plugin=str(plugin),skill=str(plugin/'skills/project-blocks/SKILL.md'),marketplace=str(market),selector='project-blocks@'+catalog['name'],globalRule=str(agents)),ensure_ascii=False,indent=2))
