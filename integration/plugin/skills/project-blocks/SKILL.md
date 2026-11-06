---
name: project-blocks
description: 为新建或正在构建的本地 Codex 软件项目建立并维护积木流程画布，保存项目内的模块、工序、依赖、状态和验收标准，并在 Codex 面板打开。用于实际项目构建、项目拆解、积木流程管理；普通问答、仅查看代码和用户明确不需要画布时不触发。
---

# 项目积木工坊

在实际项目文件夹下维护 `project-blocks/data/project.json`，用已安装的 GalFlow 改造版作为结构和进度画布。首次开始构建新项目时初始化，已有工程复用，不能用示例数据覆盖用户的卡片。

## 开始项目

1. 确定本次实际创建/开发的项目根目录。若聊天工作目录是容纳多个项目的父目录，先建立用户所需的项目子目录，画布放在子目录内。不要把用户主目录、磁盘根目录或插件目录当作业务项目。
2. 运行此 skill 的 `scripts/project_blocks.py`：

   `python "<skill-dir>/scripts/project_blocks.py" ensure --project-root "<absolute-project-root>" --title "<project-title>" --start`

   使用当前环境可用的 Python 3.10+。Windows 可调用 bundled runtime 的 Python；helper 启动后台服务时隐藏窗口。无需网络、pip、模型 API 或密钥。
3. helper 返回 JSON 中的 `url` 和 `dataFile`。用当前聊天可用的 `open_in_codex` 工具将该 URL 作为 browser target 打开到右侧；这一步由 agent 执行，不使用外部浏览器替代。若没有该工具，返回可点击的本地 URL。`--start` 不会自动打开系统浏览器。
4. 按真实需求填充或细化卡片，再继续实现项目。默认种子是“需求、实现、验收”待开始占位，不能视为已完成的工作。项目有明确计划时，可在初始化时传 `--plan <absolute-json-file>`，格式见 [工程格式](references/workflow.md)。

## 协作与更新

- 工作阶段有实质变化时，更新对应卡片的状态、文件、交付物、验收标准及实际验证证据。完成与否依据代码和检查结果，不依据计划。简短答疑不需要写卡片。
- ID、坐标、分组、便签、用户文字与非本次范围的卡片保持原样；新增关系箭头由前置指向后续。
- 修改工程前读取当前文件；写入使用临时文件原子替换。避免覆盖浏览器未保存的编辑，提醒其先保存；界面发现磁盘变化且有本地编辑会提示版本冲突。
- 再次打开同一项目重新运行 `ensure ... --start`；helper 检查服务确实对应同一工程才复用端口，不会把其他项目的画布当作当前工程。
- 每个项目包含自己的 UI、服务与数据，可独立复制或启动。修改应用主体时不要把 `project-blocks` 当作业务源代码扫描或构建目标。
- 不使用生命周期 hooks、目录监控或计划任务；触发由本 skill 的隐式选择和用户的全局项目规则完成。仅在用户创建了空项目但未开始对话时不会执行命令。

需要检查 schema、导入现有计划或记录验证证据时，读取 [references/workflow.md](references/workflow.md)。
