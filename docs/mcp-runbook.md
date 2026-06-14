# MCP Runbook — 高考志愿顾问 (Gaokao Admission)

> **最后更新**: 2026-06-14
> **兼容版本**: MCP Python SDK >= 1.0.0, Claude Code (桌面版/CLI), VS Code Copilot, Cursor, Codex

---

## 目录

1. [项目 MCP Server 概览](#1-项目-mcp-server-概览)
2. [本地启动 MCP Server](#2-本地启动-mcp-server)
3. [安装到 Claude Code](#3-安装到-claude-code)
4. [安装到其他 AI Agent/IDE](#4-安装到其他-ai-agentide)
5. [远程部署 MCP Server](#5-远程部署-mcp-server)
6. [推荐远程 MCP 托管平台](#6-推荐远程-mcp-托管平台)
7. [故障排查](#7-故障排查)
8. [附录](#8-附录)

---

## 1. 项目 MCP Server 概览

### 架构

```
┌─────────────────────────────────────────────────┐
│ Claude Code / VS Code Copilot / Cursor           │
│   (MCP Client — stdio 子进程或 HTTP 远程调用)      │
└──────────────┬──────────────────────────────────┘
               │ stdio / streamable HTTP
┌──────────────▼──────────────────────────────────┐
│ mcp-server/server.py  (FastMCP, Python 3.10+)    │
│                                                   │
│  Tools:                                           │
│  ├─ query_admission() → 查询录取数据              │
│  └─ list_provinces()  → 列出可用省份             │
│                                                   │
│  Transport: stdio (本地) / streamable HTTP (远程) │
└──────────────┬──────────────────────────────────┘
               │ SQLite (只读, immutable)
┌──────────────▼──────────────────────────────────┐
│ admission_clean.db  (132 MB, 29省, 114万条记录)   │
│  schema: province, school, major, score, rank,    │
│          year                                     │
└─────────────────────────────────────────────────┘
```

### 可用 Tool 清单

| Tool | 说明 | 关键参数 |
|------|------|---------|
| `query_admission` | 模糊搜索录取记录，返回 JSON 数组 | `province`, `school`, `major`, `max_rank`, `min_rank`, `year`, `limit` |
| `list_provinces` | 列出所有省份及其记录数和年份范围 | 无 |

### 文件位置

```
university-selector/
├── mcp-server/
│   ├── server.py           # MCP Server 主程序
│   └── requirements.txt    # Python 依赖 (mcp >= 1.0.0)
├── .mcp.json               # Claude Code 项目级 MCP 配置
├── admission_clean.db.gz   # 压缩数据库 (20MB, 首次运行自动解压)
└── admission_clean.db      # 解压后数据库 (132MB, 自动生成)
```

---

## 2. 本地启动 MCP Server

### 2.1 环境要求

- **Python 3.10+**（推荐 3.13+）
- **操作系统**: macOS / Linux / Windows（WSL 或原生）
- **磁盘空间**: ~150 MB（数据库 132MB + 压缩包 20MB）

### 2.2 安装依赖

```bash
cd /path/to/university-selector
pip install -r mcp-server/requirements.txt
```

或直接：

```bash
pip install "mcp>=1.0.0"
```

### 2.3 验证安装

```bash
# 测试数据库是否能正常解压和查询
python3 -c "
from mcp_server.server import ensure_db
conn = ensure_db()
cur = conn.execute('SELECT COUNT(*) FROM admission')
print(f'总记录数: {cur.fetchone()[0]:,}')
print('MCP Server 就绪 ✓')
"
```

预期输出：
```
总记录数: 1,140,000+
MCP Server 就绪 ✓
```

### 2.4 本地测试 MCP Server（使用 MCP Inspector）

```bash
# 安装 MCP Inspector（Node.js 工具）
npx @modelcontextprotocol/inspector python3 mcp-server/server.py
```

浏览器自动打开 `http://localhost:5173`，你可以在 Inspector 界面中：
- 查看所有 Tool 列表
- 手动传入参数调用 `query_admission` / `list_provinces`
- 查看返回的 JSON 结果

### 2.5 直接命令行测试

```bash
# 用 stdin 发送 JSON-RPC 请求测试（stdio 模式）
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 mcp-server/server.py
```

---

## 3. 安装到 Claude Code

### 方式一：项目级配置（推荐，随仓库分发）

本项目已包含 `.mcp.json`，Claude Code 在项目根目录启动时自动加载：

```json
{
  "mcpServers": {
    "gaokao-admission": {
      "type": "stdio",
      "command": "python3",
      "args": ["mcp-server/server.py"],
      "cwd": "/Users/spring/Dev/ai_coding/university-selector"
    }
  }
}
```

**安装步骤**：

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/university-selector.git
cd university-selector

# 2. 安装 MCP 依赖
pip install "mcp>=1.0.0"

# 3. 修改 .mcp.json 中的 cwd 为你的实际路径
#    或者直接删除 cwd 字段，Claude Code 会自动使用当前目录

# 4. 在 Claude Code 中启用项目级 MCP
#    设置 → enableAllProjectMcpServers: true
```

```bash
# 一键设置（macOS/Linux）
sed -i '' "s|/Users/spring/Dev/ai_coding/university-selector|$(pwd)|g" .mcp.json

# 或直接运行 Claude Code，它会在项目根目录自动识别 .mcp.json
claude
```

### 方式二：用户级全局配置

编辑 `~/.claude/settings.json`（或 `~/.claude.json`）：

```json
{
  "mcpServers": {
    "gaokao-admission": {
      "type": "stdio",
      "command": "python3",
      "args": ["/absolute/path/to/university-selector/mcp-server/server.py"]
    }
  }
}
```

注意：
- `~/.claude/settings.json` 中的 `mcpServers` 会全局生效，所有项目都可以使用
- **不要同时**在全局和项目级配置中重复注册同一个 MCP Server
- 如果使用 `cwd` 字段，路径必须是**绝对路径**

### 方式三：Claude Desktop 配置

打开 Claude Desktop → Settings → Developer → MCP Servers → Edit Config，添加：

```json
{
  "mcpServers": {
    "gaokao-admission": {
      "command": "python3",
      "args": ["/absolute/path/to/university-selector/mcp-server/server.py"]
    }
  }
}
```

### 验证安装

在 Claude Code 中运行：

```
/mcp
```

应该能看到 `gaokao-admission` 出现在可用 MCP Server 列表中，并有 2 个 tools。

或者在对话中直接测试：

```
帮我查一下湖北武汉理工大学的录取数据
```

如果 Claude 调用了 `query_admission` tool 并返回结果，说明 MCP 集成成功。

---

## 4. 安装到其他 AI Agent/IDE

### 4.1 VS Code / Cursor（Copilot 模式）

自 2025 年起，VS Code Copilot 和 Cursor 支持 MCP 配置。编辑 VS Code 的 `settings.json`：

```json
{
  "mcp": {
    "inputs": [],
    "servers": {
      "gaokao-admission": {
        "command": "python3",
        "args": ["/absolute/path/to/university-selector/mcp-server/server.py"]
      }
    }
  }
}
```

路径替换为你的实际绝对路径。

### 4.2 Codex（OpenAI）

Codex CLI 通过 `.codex/config.toml` 或 `~/.codex/config.toml` 配置 MCP：

```toml
[mcp_servers.gaokao-admission]
command = "python3"
args = ["/absolute/path/to/university-selector/mcp-server/server.py"]
```

### 4.3 Gemini CLI

Gemini CLI 使用 `~/.gemini/settings.json`：

```json
{
  "mcpServers": {
    "gaokao-admission": {
      "command": "python3",
      "args": ["/absolute/path/to/university-selector/mcp-server/server.py"]
    }
  }
}
```

### 4.4 Windsurf / Continue.dev / Cody

大部分支持 MCP 的 AI IDE 都遵循类似格式：

```json
{
  "mcpServers": {
    "gaokao-admission": {
      "transport": "stdio",
      "command": "python3",
      "args": ["/absolute/path/to/university-selector/mcp-server/server.py"]
    }
  }
}
```

具体配置文件位置：
- **Windsurf**: `~/.codeium/windsurf/mcp.json`
- **Continue.dev**: `~/.continue/config.json` 中的 `"experimental.mcpServers"` 字段
- **Cody (Sourcegraph)**: `~/.cody/mcp.json`

### 4.5 配置原则总结

| Agent / IDE | 配置文件 | 配置字段 |
|-------------|---------|---------|
| Claude Code (CLI/Desktop) | `.mcp.json` 或 `~/.claude/settings.json` | `mcpServers` |
| VS Code / Cursor | `.vscode/settings.json` | `mcp.servers` |
| Codex (OpenAI) | `.codex/config.toml` | `[mcp_servers.xxx]` |
| Gemini CLI | `~/.gemini/settings.json` | `mcpServers` |
| Windsurf | `~/.codeium/windsurf/mcp.json` | `mcpServers` |

> **关键提示**：所有配置中，`command` 和 `args` 必须使用**绝对路径**。`python3` 命令需要在系统的 `PATH` 中可用。

---

## 5. 远程部署 MCP Server

本地 stdio 模式适合个人使用，但如果需要团队共享或作为独立服务运行，需要部署为远程 streamable HTTP server。

### 5.1 架构变更概览

```
本地 stdio 模式                     远程 HTTP 模式
┌──────────┐                      ┌──────────┐
│  Client  │                      │  Client  │
└────┬─────┘                      └────┬─────┘
     │ stdin/stdout                    │ HTTPS + JSON-RPC
┌────▼─────┐                      ┌────▼─────────────┐
│ server.py│                      │ 反向代理 (nginx)  │
│ (子进程)  │                      │ /mcp → uvicorn    │
└──────────┘                      └────┬─────────────┘
                                       │
                                  ┌────▼─────────────┐
                                  │ server.py         │
                                  │ (streamable HTTP)  │
                                  │ uvicorn + FastMCP  │
                                  └──────────────────┘
```

### 5.2 改造 MCP Server 支持远程模式

当前的 `server.py` 只注册了 `mcp.run(transport="stdio")`。要支持远程部署，需要改造成可配置的 transport。

**关键改动点**：

```python
# ── Entry point ───────────────────────────────────────
if __name__ == "__main__":
    import sys
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    if transport == "http":
        mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
    else:
        mcp.run(transport="stdio")
```

然后可以通过命令行参数选择模式：

```bash
python3 mcp-server/server.py stdio   # 本地模式（默认）
python3 mcp-server/server.py http    # 远程 HTTP 模式（监听 8000 端口）
```

### 5.3 Docker 化部署

**Dockerfile**：

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# 安装依赖
COPY mcp-server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制 MCP server 和数据库压缩包
COPY mcp-server/server.py ./mcp-server/
COPY admission_clean.db.gz ./

# 预解压数据库（减少首次请求延迟）
RUN python3 -c "import gzip, shutil; \
    shutil.copyfileobj(gzip.open('admission_clean.db.gz', 'rb'), open('admission_clean.db', 'wb'))"

# 暴露端口
EXPOSE 8000

# 以 HTTP 模式启动
CMD ["python3", "mcp-server/server.py", "http"]
```

**构建和运行**：

```bash
# 构建镜像
docker build -t gaokao-admission-mcp .

# 本地测试
docker run -p 8000:8000 gaokao-admission-mcp

# 测试 HTTP 端点
curl http://localhost:8000/health
```

### 5.4 docker-compose 部署

```yaml
# docker-compose.yml
version: "3.9"

services:
  mcp-server:
    build: .
    ports:
      - "8000:8000"
    restart: unless-stopped
    environment:
      - PYTHONUNBUFFERED=1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    volumes:
      # 如果需要持久化修改，取消注释
      # - ./admission_clean.db:/app/admission_clean.db:ro
```

```bash
docker compose up -d
```

### 5.5 安全加固

远程部署时**必须**考虑安全性：

```python
# 简单的 API Key 认证中间件
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        expected = os.environ.get("MCP_API_KEY", "")
        if expected:
            actual = request.headers.get("X-API-Key", "")
            if actual != expected:
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)

# 在 create_app 中应用
# app.add_middleware(ApiKeyMiddleware)
```

**安全清单**：
- [ ] 数据库以**只读模式**挂载（`mode=ro&immutable=1`，代码中已实现）
- [ ] 启用 API Key / Bearer Token 认证
- [ ] 部署在反向代理（nginx/Caddy）后面，强制 HTTPS
- [ ] 设置 CORS 白名单（仅允许已知客户端来源）
- [ ] 限制请求速率（rate limiting）
- [ ] 不要暴露在生产环境的 `/health` 以外的不必要端点

### 5.6 客户端配置远程 MCP

部署到远程后，客户端需要改为 HTTP 连接：

**Claude Code (`~/.claude/settings.json`)**：

```json
{
  "mcpServers": {
    "gaokao-admission": {
      "type": "http",
      "url": "https://your-server.example.com/mcp",
      "headers": {
        "X-API-Key": "${MCP_API_KEY}"
      }
    }
  }
}
```

**VS Code / Cursor (`.vscode/settings.json`)**：

```json
{
  "mcp": {
    "servers": {
      "gaokao-admission": {
        "type": "sse",
        "url": "https://your-server.example.com/mcp/sse",
        "headers": {
          "X-API-Key": "${env:MCP_API_KEY}"
        }
      }
    }
  }
}
```

---

## 6. 推荐远程 MCP 托管平台

以下是适合部署本项目的托管平台对比：

### 6.1 平台对比

| 平台 | 免费额度 | 冷启动 | 适合场景 | 数据库方案 |
|------|---------|--------|---------|-----------|
| **[Fly.io](https://fly.io)** | 3 个免费 VM（256MB RAM） | 无（常驻） | 小型团队，全球多区域 | Volume（持久卷）或外部 SQLite |
| **[Railway](https://railway.app)** | $5/月额度 | 无（常驻） | 快速原型，个人项目 | 内置 Volume 或 PostgreSQL |
| **[Render](https://render.com)** | 免费 Web Service（512MB） | ~30s（15min 无请求后休眠） | 个人项目，低流量 | Disk 持久化（1GB 免费） |
| **[Hetzner VPS](https://hetzner.com)** | 无免费，但 €4/月起 | 无（常驻） | 预算敏感，长期运行 | 本地磁盘 |
| **[DigitalOcean App Platform](https://digitalocean.com)** | 无免费，$5/月起 | 无（常驻） | 专业团队 | 内置 |
| **[Cloudflare Workers](https://workers.cloudflare.com)** | 10 万请求/天免费 | 极低 | ⚠️ 不适合（Python 限制） | D1（SQLite 兼容） |
| **[Google Cloud Run](https://cloud.google.com/run)** | 200 万请求/月免费 | 极低 | 中大型团队，弹性伸缩 | Cloud SQL 或挂载 NFS |

> **本项目推荐**：
> - **个人/小团队** → **Fly.io** 或 **Railway**（简单、有免费额度、原生支持 Docker）
> - **预算优先** → **Hetzner VPS**（€4/月，2GB RAM，20GB SSD）
> - **企业/大流量** → **Google Cloud Run** + Cloud SQL（自动伸缩，按使用付费）

### 6.2 一键部署 — Fly.io

```bash
# 安装 flyctl
brew install flyctl    # macOS
# 或: curl -L https://fly.io/install.sh | sh   # Linux

# 登录
flyctl auth signup

# 在项目根目录创建 fly.toml
flyctl launch --name gaokao-admission-mcp --region hkg

# 部署
flyctl deploy

# 查看状态
flyctl status

# 获取 URL
flyctl open
```

**fly.toml 模板**：

```toml
app = "gaokao-admission-mcp"
primary_region = "hkg"

[build]
  dockerfile = "Dockerfile"

[env]
  PYTHONUNBUFFERED = "1"
  MCP_API_KEY = "your-secret-api-key-change-me"

[[services]]
  protocol = "tcp"
  internal_port = 8000

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

  [[services.ports]]
    port = 80
    handlers = ["http"]
```

### 6.3 一键部署 — Railway

```bash
# 安装 Railway CLI
npm i -g @railway/cli

# 登录
railway login

# 初始化项目
railway init

# 部署
railway up

# 查看域名
railway domain
```

Railway 会自动检测 `Dockerfile` 或 `requirements.txt`，无需额外配置。

### 6.4 一键部署 — Render

1. 访问 [render.com](https://render.com) 注册
2. 连接 GitHub 仓库
3. 创建 **Web Service**
4. 配置：
   - **Runtime**: Docker
   - **Port**: 8000
   - **Health Check Path**: `/health`
5. 点击 Deploy

### 6.5 Hetzner 裸机部署（最省钱，适合长期运行）

```bash
# SSH 登录 VPS 后
git clone https://github.com/your-org/university-selector.git
cd university-selector

# 安装 Python 和依赖
apt install python3 python3-pip
pip install -r mcp-server/requirements.txt

# 修改 server.py 支持 HTTP 模式并启动
# 使用 systemd 管理进程（见下方 service 文件）
```

**`/etc/systemd/system/gaokao-mcp.service`**：

```ini
[Unit]
Description=Gaokao Admission MCP Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/university-selector
ExecStart=/usr/bin/python3 mcp-server/server.py http
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
Environment=MCP_API_KEY=your-secret-key

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gaokao-mcp
sudo systemctl status gaokao-mcp
```

### 6.6 特殊方案 — MCPB (MCP Gateway / Proxy)

如果你不想自己管理服务器，可以使用 MCP 托管平台（如 [mcpb.xyz](https://mcpb.xyz) 或 [smithery.ai](https://smithery.ai)），它们提供：

- 一键部署 MCP Server（上传 Python 代码或 Dockerfile）
- 自动 HTTPS + 认证
- 内置速率限制和监控
- OAuth 集成

适合不想操作运维的快速场景。

---

## 7. 故障排查

### 问题 1：`Failed to reconnect to gaokao-admission: -32000`

**原因**：MCP Server 进程启动失败或崩溃。

**排查步骤**：

```bash
# 1. 确认 Python 环境
python3 --version  # 需要 >= 3.10

# 2. 确认依赖安装
pip list | grep mcp  # 应显示 mcp >= 1.0.0

# 3. 手动启动测试
python3 /absolute/path/to/mcp-server/server.py
# 应该等待 stdin 输入，不报错

# 4. 确认数据库存在
ls -lh /absolute/path/to/admission_clean.db.gz
# 如果 .db.gz 和 .db 都不存在，数据库文件缺失

# 5. 确认 .mcp.json 路径正确
cat /absolute/path/to/.mcp.json
# cwd 和 args 路径必须是绝对路径
```

### 问题 2：MCP Server 连接成功但返回空结果

**原因**：可能是数据库未解压或查询参数不匹配。

**排查**：

```bash
# 手动解压数据库
cd /path/to/university-selector
python3 -c "
import gzip, shutil
shutil.copyfileobj(gzip.open('admission_clean.db.gz', 'rb'), open('admission_clean.db', 'wb'))
print('数据库解压完成')
"

# 验证数据库内容
python3 -c "
import sqlite3
conn = sqlite3.connect('admission_clean.db')
cur = conn.execute('SELECT DISTINCT province FROM admission ORDER BY province')
provinces = [r[0] for r in cur.fetchall()]
print(f'可用省份 ({len(provinces)}): {provinces}')
"
```

### 问题 3：报 `mcp>=1.0.0` 依赖冲突

```bash
# 使用虚拟环境隔离
python3 -m venv .venv
source .venv/bin/activate
pip install "mcp>=1.0.0"

# 在 .mcp.json 中指向虚拟环境的 python
{
  "mcpServers": {
    "gaokao-admission": {
      "command": "/absolute/path/to/.venv/bin/python3",
      "args": ["mcp-server/server.py"],
      "cwd": "/absolute/path/to/university-selector"
    }
  }
}
```

### 问题 4：远程 HTTP 部署后 502/503 错误

**常见原因**：

1. **反向代理超时**：nginx 默认 `proxy_read_timeout 60s`，MCP 请求可能更慢。调整为 300s。
2. **数据库未预解压**：首次请求触发解压，132MB 文件需要 ~15 秒。在 Dockerfile 中预解压。
3. **内存不足**：数据库以只读模式打开，内存需求约 50-100MB。确保容器至少有 256MB RAM。

### 问题 5：macOS 上提示 `python3: command not found`

```bash
# macOS 通常用 python3，确认安装
which python3

# 如果没有，安装
brew install python@3.13

# 或使用绝对路径
which python3  # 返回如 /opt/homebrew/bin/python3
# 将这个绝对路径填入 .mcp.json 的 command 字段
```

---

## 8. 附录

### A. MCP 工具完整规格

#### `query_admission`

```
输入 schema (FastMCP 自动从类型注解生成):
  province:  string | None  — 省份名模糊匹配 (e.g. '湖北')
  school:    string | None  — 学校名模糊匹配 (e.g. '武汉理工')
  major:     string | None  — 专业名模糊匹配 (e.g. '计算机')
  max_rank:  int | None     — 位次上限 (e.g. 30000)
  min_rank:  int | None     — 位次下限 (e.g. 20000)
  year:      int | None     — 年份精确筛选 (e.g. 2024)
  limit:     int = 20       — 返回条数上限 (1-50)

输出:
  JSON array: [{school, major, score, rank, province, year}, ...]

约束:
  - 至少提供 province 或 school 之一，否则返回 error
  - limit 硬上限 50，防止上下文溢出
  - rank 条件会自动加 IS NOT NULL 检查
```

#### `list_provinces`

```
输入: 无参数

输出:
  JSON array: [{province, record_count, years}, ...]
  按 record_count 降序排列

示例:
  [{"province": "湖北", "record_count": 85000, "years": "2021-2024"}, ...]
```

### B. 快速启动脚本

保存为 `start-mcp.sh`：

```bash
#!/bin/bash
# 启动 MCP Server（本地 stdio 或远程 HTTP 模式）

set -e

cd "$(dirname "$0")/.."  # 回到项目根目录

MODE="${1:-stdio}"

# 确保依赖已安装
if ! python3 -c "import mcp" 2>/dev/null; then
    echo "安装 MCP 依赖..."
    pip install -r mcp-server/requirements.txt
fi

# 确保数据库已解压
if [ ! -f admission_clean.db ] && [ -f admission_clean.db.gz ]; then
    echo "解压数据库..."
    python3 -c "
import gzip, shutil
shutil.copyfileobj(gzip.open('admission_clean.db.gz', 'rb'), open('admission_clean.db', 'wb'))
print('数据库解压完成')
"
fi

case "$MODE" in
    http)
        echo "启动 MCP Server (HTTP 模式在 :8000)..."
        python3 mcp-server/server.py http
        ;;
    stdio)
        echo "启动 MCP Server (stdio 模式)..."
        python3 mcp-server/server.py stdio
        ;;
    *)
        echo "Usage: $0 {stdio|http}"
        exit 1
        ;;
esac
```

```bash
chmod +x start-mcp.sh
./start-mcp.sh http   # 远程模式
./start-mcp.sh stdio  # 本地模式
```

### C. 相关资源

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [MCP Python SDK 文档](https://github.com/modelcontextprotocol/python-sdk)
- [FastMCP API 参考](https://github.com/modelcontextprotocol/python-sdk?tab=readme-ov-file#fastmcp)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
- [Claude Code MCP 配置指南](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [MCPB — MCP 托管平台](https://mcpb.xyz)
- [Smithery — MCP Server 市场](https://smithery.ai)

### D. 版本历史

| 日期 | 变更 |
|------|------|
| 2026-06-14 | 初始版本 — 完整 runbook 覆盖本地/远程部署全流程 |
