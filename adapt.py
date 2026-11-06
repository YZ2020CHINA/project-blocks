from pathlib import Path
import argparse

root = Path(__file__).parent
p = root / 'app/index.html'
parser = argparse.ArgumentParser(description='Rebuild the adapted canvas from an original GalFlow 1.12 HTML file.')
parser.add_argument('source', type=Path, help='Path to galgame_script_editor 1.12.html')
source = parser.parse_args().source
s = source.read_text(encoding='utf-8-sig')
s = s.replace('galflow_', 'projectblocks_')
s = s.replace("|| 'p5r'", "|| 'classic'")
s = s.replace("const newId = 'node_' + Date.now();", "const newId = 'node_' + crypto.randomUUID();")
s = s.replace('<title>GalFlow - 视觉小说剧本与无限画布流程图整理工具</title>', '<title>项目积木工坊 · Project Blocks</title>')
# Keep the original canvas engine; adapt its visible vocabulary.
for a, b in [('GalFlow 剧本工坊', '项目积木工坊'), ('未命名视觉小说', '未命名项目'), ('章节', '工序'), ('剧情梗概', '任务目标'), ('台词正文', '执行说明'), ('剧本文档', '项目文档'), ('剧本', '项目'), ('人物设定', '资源'), ('主线/共通', '需求'), ('序章', '需求'), ('共通线', '任务'), ('关键分支', '决策'), ('个人线', '模块'), ('结局', '验收'), ('出场人物', '负责人'), ('场景地点', '文件路径'), ('配乐BGM', '交付物'), ('分支选择', '输出关系'), ('剧情推进', '前置依赖')]:
    s = s.replace(a, b)
s = s.replace('const sidebarNodeCount =', 'let sidebarNodeCount =')
s = s.replace("      sidebarNodeCount.textContent = project.nodes.length;", "      sidebarNodeCount = document.getElementById('sidebar-node-count');\n      if (sidebarNodeCount) sidebarNodeCount.textContent = project.nodes.length;")
s = s.replace('src="${imgSrc}"', 'src="${escapeHtml(imgSrc)}"')
s = s.replace('</head>', '<link rel="stylesheet" href="blocks.css?v=1.2">\n</head>')
s = s.replace('</body>', '<script src="blocks.js?v=1.1"></script>\n</body>')
p.write_text(s, encoding='utf-8')
