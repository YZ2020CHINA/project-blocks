"""Generate the bundled example. Never overwrites an existing project."""
from pathlib import Path
import json

ROOT = Path(__file__).parent
definitions = [
    ('goal', '项目目标与范围', 'prologue', '#9b8aff', 60, 80, '把项目拆成可组合的积木，让结构、执行顺序和交付结果一眼可见。', 'done', ['明确项目用户与主要使用场景', '列出本次要交付的功能范围'], ['docs/brief.md'], '你', '项目需求说明'),
    ('design', '画布与卡片模块', 'route', '#72a8f8', 500, 80, '复用 GalFlow 的无限画布，搭建卡片、端口与分组交互。', 'doing', ['可以拖拽卡片与平移缩放画布', '可以为卡片编辑目标、状态和文件'], ['app/index.html', 'app/blocks.js', 'app/blocks.css'], 'Codex', '可交互的项目画布'),
    ('schema', '工程数据与同步', 'route', '#72a8f8', 500, 480, '用 JSON 保存项目结构，支持 Codex 修改后回到画布查看。', 'todo', ['保存后重新打开不丢失卡片', '外部修改与未保存画布冲突时能选择版本'], ['data/project.json', 'server.py'], 'Codex', '工程文件与本地服务'),
    ('reference', 'GalFlow 1.12 参考', 'character', '#e6b66d', 60, 480, '原有剧本整理工具提供卡片、连线、便签、分组和撤销引擎。', 'done', ['确认原文件路径与版本'], ['galgame_script_editor 1.12.html'], '你', '画布基础工具'),
    ('task-ui', '积木编辑与任务导出', 'common', '#73d2b3', 940, 80, '填写验收标准和关联文件，将选中的积木整理为 Codex 可执行任务。', 'todo', ['六种积木类型可创建', '任务说明包含 ID、目标、前置工序和验收标准'], ['app/blocks.js'], 'Codex', 'CODEX_TASK.md'),
    ('task-sync', '文件保存与版本检查', 'common', '#73d2b3', 940, 480, '保证画布和磁盘文件之间的修改可追踪，保存时检查版本。', 'todo', ['写入前检查磁盘版本', '发现冲突时不覆盖未保存修改'], ['server.py', 'app/blocks.js'], 'Codex', '可同步的本地工程'),
    ('decision', '确认第一版使用方式', 'branch', '#f295ac', 1380, 480, '先通过项目 JSON 和任务 Markdown 与 Codex 协作，按实际使用再扩展自动化。', 'todo', ['确认本地文件协作方式满足当前需求'], ['README.md'], '你', '使用方式决策'),
    ('accept', '整体流程验收', 'ending', '#b0cb70', 1820, 80, '从创建积木到生成任务，再到更新状态，走通一次完整项目构建流程。', 'todo', ['新建、连接、编辑、撤销均可使用', '保存、刷新、外部更新后数据一致', '验收结果与任务状态一致'], ['tests/'], '你 + Codex', '验收记录')
]
nodes = []
for id, title, kind, color, x, y, summary, status, acceptance, files, owner, output in definitions:
    nodes.append(dict(id=id, title=title, routeType=kind, color=color, x=x, y=y,
                      characters=owner, location=', '.join(files), bgm=output,
                      summary=summary, script='先检查相关文件，按验收标准实施并记录实际结果。', image='', choices=[],
                      workflow=dict(status=status, priority='P1', acceptance=acceptance, files=files, blockReason='')))
edges = [('goal','design','前置依赖'), ('goal','schema','前置依赖'), ('reference','design','提供资源'), ('design','task-ui','前置依赖'), ('schema','task-sync','前置依赖'), ('task-sync','decision','前置依赖'), ('task-ui','accept','前置依赖'), ('decision','accept','前置依赖')]
for i,(a,b,type) in enumerate(edges):
    next(n for n in nodes if n['id']==a)['choices'].append(dict(id=f'rel_{i}',text=type,tag=type,target=b))
p = dict(title='我的项目 · 工序搭建示例',version='1.0',viewport=dict(x=40,y=80,scale=.55),nodes=nodes,
         groups=[dict(id='group_design',title='01 · 规划与基础',tag='项目结构',color='blue',nodeIds=['goal','design','schema','reference']),dict(id='group_build',title='02 · 实施与验证',tag='工序推进',color='green',nodeIds=['task-ui','task-sync','decision','accept'])],stickyNotes=[],customRoutes=[])
path=ROOT/'data/project.json'
if not path.exists():
    path.write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'data/example.project.json').write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf-8')
