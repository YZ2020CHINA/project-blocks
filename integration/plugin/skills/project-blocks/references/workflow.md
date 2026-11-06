# 工程格式与协作

工程路径固定为 `<实际项目根目录>/project-blocks/data/project.json`。原 GalFlow 引擎保留的字段名：`characters`=负责人，`location`=文件摘要，`bgm`=交付物，`script`=执行说明。`workflow.files` 是权威文件列表。

类型：`prologue` 需求、`route` 模块、`common` 任务、`character` 资源、`branch` 决策、`ending` 验收。
状态：`todo` 待开始、`doing` 进行中、`blocked` 受阻、`review` 待验收、`done` 已完成。

`ensure --plan file.json` 接收以下计划；仅新建工程时读取，不会替换已有工程：

```json
{
  "title": "素材管理工具",
  "nodes": [
    {"id":"import", "title":"素材导入", "type":"route", "summary":"导入并展示文件", "files":["src/import.ts"], "acceptance":["可读取用户选择的文件"]},
    {"id":"check", "title":"导入验收", "type":"ending", "acceptance":["导入、保存、重新打开结果一致"]}
  ],
  "edges": [{"from":"import", "to":"check", "type":"前置依赖"}]
}
```

完整节点：

```json
{
  "id":"task_storage", "title":"项目存取", "routeType":"common", "color":"#73d2b3",
  "x":100,"y":100,"characters":"Codex","location":"src/storage.ts","bgm":"可重载的工程文件",
  "summary":"实现项目保存与重开", "script":"先阅读现有 schema。",
  "choices":[{"id":"rel_storage_check","text":"前置依赖","tag":"前置依赖","target":"check"}],
  "workflow":{"status":"todo","priority":"P1","files":["src/storage.ts"],"acceptance":["重载数据一致"],"blockReason":"","evidence":[]}
}
```

验收证据可保存在 `workflow.evidence` 字符串数组，包含实际执行的检查及结果；不要在未执行时写“通过”。工程顶层保留 `title`、`version`、`viewport`、`nodes`、`groups`、`stickyNotes`、`customRoutes`。

程序保存使用当前文件 hash 检测冲突并备份上一版。Agent 外部写入应先读取当前工程，保留未知字段并原子替换，例如 Python 中写到同目录临时文件后 `os.replace`。如果用户当前浏览器有未保存修改，先让用户保存或使用 UI 保存后再编辑磁盘。

启动器：`project-blocks/启动.cmd` 或 `python project-blocks/start.py`；自动选择空闲回环端口。`.runtime.json`、日志和备份文件是本机状态，项目下自带 `.gitignore` 忽略它们，项目 JSON 可以版本管理。
