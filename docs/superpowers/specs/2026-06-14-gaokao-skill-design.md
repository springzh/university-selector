# 高考志愿顾问 Skill 重构设计文档

**日期**: 2026-06-14
**状态**: 设计中
**版本**: v1

## 1. 目标

将当前 Windows 专用的 Python CLI 程序（`agent.py`）重构为可在 Claude Code 中安装执行的 Skill，实现跨平台、零外部 LLM 依赖、安装即用。

## 2. 架构决策

### 2.1 核心原则

**方案 A：纯指令 Skill + 轻量 MCP 数据层**

- Claude 自身承担全部推理（意图识别、槽位提取、分档推荐、对话生成）
- MCP Server 只做结构化数据查询
- 不保留 Python 脚本参与对话流程
- 软逻辑（槽位提取、分档判断）不硬编码

### 2.2 各层职责

| 层 | 载体 | 职责 |
|----|------|------|
| 指令层 | SKILL.md (~1200行) | 人设、流程、槽位规则、分档逻辑、表达约束、知识库 |
| 数据层 | MCP Server (~150行) | SQLite 查询：`query_admission` + `list_provinces` |
| 状态层 | slot_state.json (运行时) | 7个槽位的当前采集状态 |
| 搜索层 | Claude Code WebSearch 工具 | 替代百度爬虫，获取最新政策/分数线 |
| 推理层 | Claude 自身 | 意图判断、槽位提取、冲稳保分档、对话生成 |

## 3. 文件变更

### 3.1 新增文件

| 文件 | 行数 | 说明 |
|------|------|------|
| `SKILL.md` | ~1200 | 完整 Skill 指令。合并 system_prompt.md + knowledge_base.md + agent.py 逻辑 |
| `mcp-server/server.py` | ~150 | Python MCP Server，2个工具 |
| `mcp-server/requirements.txt` | ~3 | `mcp` 依赖声明 |
| `docs/superpowers/specs/2026-06-14-gaokao-skill-design.md` | — | 本文档 |

### 3.2 退役文件（删除或标记废弃）

| 文件 | 替代方案 |
|------|----------|
| `agent.py` | SKILL.md 指令 + Claude 推理 |
| `gaokao_data.py` | WebSearch 工具 |
| `real_data.py` | MCP Server |
| `.env.example` | MCP 配置（settings.json） |
| `启动.bat` | Skill 安装即用 |

### 3.3 保留文件

| 文件 | 用途 |
|------|------|
| `admission_clean.db.gz` | MCP Server 数据源 |
| `knowledge_base.md` | 参考源文件（内容已内联到 SKILL.md） |
| `system_prompt.md` | 参考源文件（逻辑已融入 SKILL.md） |
| `scripts/build_*.py` | 数据库构建/清洗/验证流水线 |
| `scripts/clean_data.py` | 同上 |
| `scripts/verify_provinces.py` | 同上 |
| `README.md` | 更新安装说明 |

## 4. MCP Server 设计

### 4.1 技术选型

- **语言**: Python 3.10+
- **框架**: `mcp` (Python MCP SDK)
- **数据库**: SQLite3（内置，零依赖）
- **启动**: stdio 模式，Claude Code 自动管理生命周期

### 4.2 工具定义

#### `query_admission`

灵活的组合查询，所有参数可选，但至少需要 `province` 或 `school` 之一。

```
参数:
  province   string?  省份名（LIKE 模糊匹配）
  school     string?  学校关键词（LIKE 模糊匹配）
  major      string?  专业关键词（LIKE 模糊匹配）
  max_rank   integer? 位次上限
  min_rank   integer? 位次下限
  year       integer? 年份，默认 2024
  limit      integer? 返回条数，默认 20，最大 50

返回: JSON 数组
  [{school, major, score, rank, province, year}, ...]
  按 year DESC, rank ASC 排序
```

SQL 构建伪代码：
```sql
SELECT school, major, score, rank, province, year
FROM admission
WHERE (? IS NULL OR province LIKE '%' || ? || '%')
  AND (? IS NULL OR school LIKE '%' || ? || '%')
  AND (? IS NULL OR major LIKE '%' || ? || '%')
  AND (? IS NULL OR rank <= ?)
  AND (? IS NULL OR rank >= ?)
ORDER BY year DESC, rank ASC
LIMIT ?
```

#### `list_provinces`

返回可用省份列表及数据规模，让 Claude 了解数据覆盖范围。

```
参数: 无

返回: JSON 数组
  [{province, record_count, years}, ...]
  按 record_count DESC 排序
```

### 4.3 启动流程

```python
# server.py 启动时
1. 检查 admission_clean.db 是否存在
2. 不存在则从 admission_clean.db.gz 自动解压（gzip + shutil）
3. 以只读模式打开 SQLite 连接
4. 注册 2 个工具到 MCP Server
5. stdio 模式运行
```

### 4.4 安全约束

- 数据库以只读模式打开
- LIMIT 硬上限 50 条
- 所有查询使用参数化占位符（`?`），防 SQL 注入
- 不暴露文件系统访问
- 数据库路径固定在项目目录内

### 4.5 安装配置

用户需在 Claude Code 的 `settings.json` 中添加：

```json
{
  "mcpServers": {
    "gaokao-admission": {
      "type": "stdio",
      "command": "python3",
      "args": ["mcp-server/server.py"],
      "cwd": "/path/to/university-selector"
    }
  }
}
```

前置依赖：`pip install mcp`

## 5. SKILL.md 设计

### 5.1 总体结构

| 区域 | 标题 | 行数 | 性质 |
|------|------|------|------|
| Frontmatter | Skill 元数据 | ~10 | — |
| ① 人设 | 你是谁 | ~30 | 刚性 |
| ② 咨询流程 | 意图→采集→匹配→推荐 | ~120 | 刚性 |
| ③ 槽位系统 | 7槽位 + JSON状态管理 | ~60 | 刚性 |
| ④ 数据查询规则 | MCP + WebSearch + 3层优先级 | ~60 | 刚性 |
| ⑤ 冲稳保分档 | 位次比例框架 + 弹性因子 | ~50 | 柔性 |
| ⑥ 表达+边界 | 反Markdown + 安全红线 | ~80 | 刚性 |
| ⑦ 知识库 | 17模块志愿填报方法论 | ~800 | 参考 |

### 5.2 ③ 槽位系统设计

#### slot_state.json 格式

```json
{
  "province":    {"status": "done",    "value": "湖北"},
  "score_rank":  {"status": "done",    "value": "580分/位次28000"},
  "subject":     {"status": "done",    "value": "物理"},
  "interest":    {"status": "pending", "value": ""},
  "region":      {"status": "pending", "value": ""},
  "family":      {"status": "pending", "value": ""},
  "goal":        {"status": "pending", "value": ""}
}
```

#### 操作规则

1. 每轮对话开始时，Read `slot_state.json` 了解当前状态
2. 从用户消息中提取到新信息时，立即 Write 更新文件
3. 提取依据：SKILL.md 中定义的关键词列表和识别规则（移植自 agent.py 的正则逻辑，但由 Claude 自然语言理解执行）
4. 状态变更时在回复中自然确认（如"好的，湖北580分，了解了"）
5. **进入推荐的最低门槛**：province + score_rank + goal 三项 status=done
6. **五槽全满时**：直接输出完整推荐，禁止再追问
7. `/reset` 或用户明确要求重新开始时，将所有 slot status 重置为 pending

#### 槽位定义与识别指引

| 槽位 | 识别关键词/模式 | 追问话术（缺时） |
|------|----------------|-----------------|
| province | 省份名列表（31个），"本省""老家" | "哪个省的？这个决定了竞争池" |
| score_rank | 3位数字+分，6位数+位/名 | "考了多少分？省排名知道吗？" |
| subject | 物理/历史/物化生/史政地等 | "选科是什么？物理还是历史？" |
| interest | 专业名、行业名、"讨厌XX" | "想学什么？最讨厌什么？" |
| region | 城市名、"省内""离家近""北上广" | "想去哪？不去哪？" |
| family | "电力""电网""医生""普通家庭" | "家里做什么的？" |
| goal | "就业""考公""考研""稳定""高薪" | "最看重什么？好就业还是稳定？" |

### 5.4 ⑤ 冲稳保分档规则

#### 基础框架

以用户位次为基准 R，对数据库返回的每条记录 rank 做分档：

| 档次 | 位次关系 | 含义 |
|------|---------|------|
| **冲** | rank < R × 0.7 | 往年录取位次远高于你，需要运气 |
| **稳** | R × 0.7 ≤ rank ≤ R × 1.3 | 位次接近，正常发挥大概率能进 |
| **保** | rank > R × 1.3 | 位次远低于你，稳进 |

如用户无精确位次只有分数，则用分数类比。

#### 弹性调整因子（Claude 自主判断）

- **学校层次**：985/211 的冲可放宽到 rank < R × 0.6（名校值得一搏）
- **家庭资源**：有行业内部资源的，稳档学校可升至冲档（如电网家庭报电气）
- **专业热度**：计算机/临床等热门专业，实际录取位次比学校投档线高，稳的学校可能需要降为冲
- **冷门专业**：可用保底学校的位次报更好学校的冷门专业
- **地域偏好**：用户指定城市时，该城市学校竞争更激烈，冲稳保比例适当收紧

#### MCP 查询策略

1. 首次查询：`max_rank=R×1.5, min_rank=R×0.3`（宽范围，确保覆盖所有可能）
2. 根据结果做分档
3. 若某档结果过多/过少，调整参数二次查询
4. 每档推荐 2-4 所学校，附简要理由

### 5.5 ④ 数据查询铁律

每轮用户提到具体学校/专业/分数时，必须按以下顺序处理：

```
第1层: MCP query_admission()
  ├─ 有数据 → 引用。标注省份和年份
  ├─ 本省无跨省有 → 引用 + 明确标注"XX省暂无该学校数据，以下为YY省参考"
  └─ 完全无结果 → 进入第2层

第2层: WebSearch
  ├─ 搜索"{学校} {省份} 录取分数线 位次 2025"
  ├─ 优先教育考试院、学校官网、中国教育在线
  ├─ 多条信息交叉验证
  ├─ 有结果 → 引用 + 标注"网上信息仅供参考"
  └─ 无结果 → 进入第3层

第3层: 承认不知道
  ├─ 明确说"数据库和网上均未找到"
  ├─ 建议查省教育考试院官网
  └─ 🚫 禁止编造任何数字。此条为死线
```

## 6. 实现范围

### 6.1 Phase 1：核心 Skill（本次）

- [ ] `SKILL.md` 完整编写（7个区域）
- [ ] `mcp-server/server.py` MCP Server 实现
- [ ] `slot_state.json` 初始模板
- [ ] 退役 agent.py 等文件（标记废弃/移动至 legacy/）
- [ ] 更新 README.md（Skill 安装说明）
- [ ] 验证：用示例对话测试完整流程

### 6.2 不在本次范围

- [ ] MCP Server 性能优化（缓存、连接池）
- [ ] 数据库增量更新机制
- [ ] 多省份数据并行查询
- [ ] 知识库模块化按需加载（当前全量内联足够）
- [ ] Web 界面 / Gradio / Streamlit

## 7. 风险与缓解

| 风险 | 缓解 |
|------|------|
| SKILL.md 过长（~1200行），token消耗大 | 1200行约40KB，Claude 1M上下文可轻松承载。若后续增大可考虑知识库模块化 |
| Claude 偶尔漏写 slot_state.json | SKILL.md 指令中反复强调；遗漏时槽位状态不变，用户可 `/slots` 查看 |
| MCP 查询结果过多支撑上下文 | LIMIT 50 + 建议Claude对结果做摘要而非全量输出 |
| 冲稳保分档过于依赖Claude判断 | 位次比例框架提供刚性基线；弹性调整是feature而非bug |
| Python MCP SDK 兼容性 | 固定 `mcp>=1.0.0` 版本，MCP Server 代码极简，升级成本低 |
