# Skillhub

> 本地统一技能集线器 — 装一次技能，所有 AI agent 平台都能用

**One skill to rule them all.** Skillhub 是一个本地的技能/工具中央注册表，让你在一台机器上安装一次技能，就能在所有 AI agent 平台（Claude Code、WorkBuddy、OpenAI Codex、Cherry Studio……）之间共享使用。

## ✨ 特性

- 🎯 **单一真源** — 技能的规范副本只存一份，各平台通过 symlink/junction 共享
- 🔌 **适配器架构** — 新增平台支持只需写一个 Python 类
- 🔒 **安全无侵入** — 用命名空间前缀管理 MCP 配置，绝不碰用户手动设置的内容
- 🩺 **健康检查** — `skillhub doctor` 检测断裂链接，支持自动修复
- 📊 **状态追踪** — SQLite 注册表跟踪每个技能在每个平台的同步状态
- 💻 **跨平台** — 支持 Windows（junction）、macOS、Linux（symlink）

## 🏗️ 架构

### 两层模型

| 层级 | 内容 | 同步方式 |
|---|---|---|
| **Tier 1: SKILL.md 技能** | 提示词驱动的技能 | 目录 junction/symlink |
| **Tier 2: MCP 服务器** | 可调用工具服务器 | 配置文件注入（`skillhub:` 前缀命名空间） |

### 支持的平台

| 平台 | Tier 1 (SKILL.md) | Tier 2 (MCP) |
|---|:---:|:---:|
| **Claude Code** | ✅ | 🔜 |
| **WorkBuddy** | ✅ | 🔜 |
| **OpenAI Codex** | ✅ | 🔜 |
| **Cherry Studio** | 🔜 | 🔜 |
| **Claude Desktop** | — | 🔜 |
| **LM Studio** | — | 🔜 |
| **VS Code + Copilot** | — | 🔜 |

## 🚀 快速开始

### 安装

**方式一：单文件 EXE（推荐 Windows 用户）**

直接从 [Releases](https://github.com/Justin-Ju-0413/skillhub/releases) 下载 `skillhub.exe`，放到 PATH 里即可使用，无需 Python 环境。

**方式二：pip 安装**

```bash
git clone https://github.com/Justin-Ju-0413/skillhub.git
cd skillhub
pip install -e .
```

**方式三：源码构建 EXE**

```bash
pip install pyinstaller
pyinstaller --clean skillhub.spec
# 产物在 dist/skillhub.exe
```

### 初始化

```bash
skillhub init
```

自动检测本机安装的 agent 平台，导入现有的技能到中央注册表。

### 同步到所有平台

```bash
skillhub sync
```

### 查看状态

```bash
skillhub list              # 列出所有已安装技能
skillhub platforms         # 查看平台状态
skillhub doctor            # 健康检查
skillhub doctor --fix      # 自动修复问题
```

## 📖 命令手册

| 命令 | 说明 |
|---|---|
| `skillhub init` | 初始化注册表，检测平台，导入现有技能 |
| `skillhub list` | 列出所有已安装技能 |
| `skillhub sync` | 同步技能到所有启用的平台 |
| `skillhub sync --platform <name>` | 只同步指定平台 |
| `skillhub sync --dry-run` | 试运行，不做实际修改 |
| `skillhub doctor` | 检查技能同步状态 |
| `skillhub doctor --fix` | 自动修复断裂的链接 |
| `skillhub platforms` | 列出检测到的平台 |
| `skillhub platforms enable <name>` | 启用平台 |
| `skillhub platforms disable <name>` | 禁用平台 |
| `skillhub import --from <platform>` | 从指定平台批量导入技能 |

## 🧩 架构说明

```
~/.skillhub/
├── config.json           # 全局配置
├── registry.db           # SQLite 注册表
├── skills/               # Tier 1 规范副本
│   ├── excel-xlsx/
│   │   ├── SKILL.md
│   │   └── skillhub.json
│   └── ...
├── servers/              # Tier 2 MCP 服务器定义 (v0.2)
└── logs/                 # 操作日志
```

### 添加新平台适配器

在 `src/skillhub/adapters/` 下新建一个 Python 文件，继承 `BaseAdapter`：

```python
from .base import BaseAdapter
from pathlib import Path

class MyPlatformAdapter(BaseAdapter):
    name = "myplatform"
    display_name = "My Platform"

    def __init__(self):
        self.skill_dir = Path.home() / ".myplatform" / "skills"
        self.mcp_config_path = None

    def is_installed(self) -> bool:
        return (Path.home() / ".myplatform").exists()
```

自动被发现并注册。

## 🛣️ 路线图

- **v0.1** ✅ Tier 1 SKILL.md 技能共享（3 个平台）
- **v0.2** 🔜 Tier 2 MCP 服务器统一管理
- **v0.3** 🔜 Cherry Studio 适配器 + 格式翻译
- **v0.4** 🔜 VS Code / GitHub Copilot 适配器
- **v0.5** 🔜 GUI + 自动同步

## 📄 许可证

MIT License
