---
triggers:
  - 安装技能
  - 卸载技能
  - 技能列表
  - 技能管理
  - install skill
  - skill
max_tokens: 400
---

# 技能管理

## 触发条件

用户请求安装、卸载、查看技能列表。

## 指令

你可以使用 `skill` 工具管理技能：

- `skill(action="list")` — 列出所有已安装和内置技能
- `skill(action="install", source="user/repo/path")` — 从 GitHub 安装技能
- `skill(action="install", source="/local/path")` — 从本地路径安装
- `skill(action="uninstall", source="skill_id")` — 卸载已安装的技能
- `skill(action="search", query="关键词")` — 搜索可用技能

安装后技能会自动生效，无需重启。

## 工具

- skill
