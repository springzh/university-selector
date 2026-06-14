# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A conversational AI agent for Chinese Gaokao (college entrance exam) university admissions counseling. The agent uses a slot-based information collection system, a local SQLite database (29 provinces, 1.14M admission records), web search fallback, and an OpenAI-compatible LLM backend to give personalized "reach/match/safety" school recommendations.

## Running

```bash
python agent.py                    # Interactive CLI
python agent.py --model qwen-plus  # Specific model
python agent.py --no-search        # Disable web search
```

On Windows, double-click `启动.bat`. Requires Python 3.10+ and `pip install openai pywin32`.

## Configuration

Copy `.env.example` to `.env`. Use `LLM_PROVIDER` shortcuts to auto-resolve base_url and model:

```
LLM_PROVIDER=deepseek   # deepseek-chat (default, recommended)
LLM_PROVIDER=qwen       # qwen-plus (free tier available)
LLM_PROVIDER=glm        # glm-4
LLM_PROVIDER=ollama     # local model (free, offline)
```

Without `LLM_PROVIDER`, set `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` manually.

## Architecture

### Data Flow

```
User input → intent detection → slot extraction → [local DB query] → [web search] → LLM inference → formatted reply
```

The agent enforces a strict 3-tier data sourcing order: (1) local SQLite → (2) Baidu web search → (3) admit no data, forbid fabrication. When local data exists but is from a different province than the user's, it's presented with an explicit cross-province warning.

### Slot System (agent.py)

The agent manages 7 slots (`province`, `score_rank`, `subject`, `interest`, `region`, `family`, `goal`) parsed from user messages via regex. At least province + score/rank + goal must be filled before recommendations are given. Slots are displayed to the LLM as a tracking table in every system message.

### Knowledge Base

- `knowledge_base.md` (837 lines, 17 modules) — Full counseling methodology loaded into every system message as context
- `system_prompt.md` — Persona definition: a blunt, experienced counselor who speaks in natural conversational Chinese, explicitly banning Markdown/emoji/tables in output. Defines the 5-slot collection workflow and family-background matching rules

### Database Pipeline

The local database (`admission_clean.db.gz`, 20MB compressed) is auto-decompressed to ~132MB SQLite on first run. The build pipeline for regenerating it from raw data:

1. `build_all_provinces.py` / `build_real_db.py` — Parse `.xls`/`.xlsx` files from `E:\桌面\高考志愿填报\` directory, auto-detect headers and column positions heuristically
2. `clean_data.py` — Filter to valid schools (must contain 大学/学院), validate score (300-750) and rank (>100) ranges, output `admission_clean.db`
3. `verify_provinces.py` — Per-province data quality check against known universities

The cleaned DB schema (`admission` table): `province TEXT, school TEXT, major TEXT, score INTEGER, rank INTEGER, year INTEGER`. `agent.py` queries with `LIKE '%keyword%'` fuzzy matching on school, major, and province.

### Provider Presets (agent.py)

`PRESETS` dict maps provider names to base_url + model. `LLM_PROVIDER` env var selects a preset; `LLM_BASE_URL`/`LLM_MODEL` override individual fields. The `resolve_config()` function handles resolution.

### Web Search (agent.py)

Baidu-based search with page content extraction. `should_search()` triggers on keywords like 分数线/录取/就业率/985/211 etc. The `web_search()` function scrapes result pages, strips HTML, and returns cleaned text snippets. Web results are presented with mandatory source attribution and a cross-verification note.

### Key Design Decisions

- **No Markdown in output**: `cleanup_format()` strips `**bold**`, `# headers`, `- lists`, `1. numbering` from LLM responses to enforce conversational style
- **Model-agnostic**: Any OpenAI-compatible endpoint works. Provider presets eliminate the need to know base URLs
- **Data-first, not LLM-first**: The agent injects real database results as user-prompt messages before LLM inference, not as function-calling tools
- **Clipboard integration**: Windows-only `/paste` command reads from clipboard via `win32clipboard`
- **No truncated history**: Full conversation retained (not limited to N rounds) since the model has a 1M context window

## HyperFrames Video

`zhiyuan-video/` contains a HyperFrames HTML composition (`index.html`) and build script (`build_video.py`) for the promo/demo video. Rendered output is `zhiyuan-video/index.mp4`.
