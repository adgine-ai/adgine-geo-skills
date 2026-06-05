---
name: adgine/geo-projects
description: Lists, creates, retrieves, updates, and deletes GEO platform website projects, manages a project's competitor list (add / list / remove), and verifies API authentication. Use when the user needs to see their website projects, select a project to work on, create a new website project, check which project is active, manage competitors (竞争对手 / 竞品 / competitors / competitor brands), or when any other GEO operation needs to identify a project ID before proceeding. Also use this skill first to verify authentication is configured correctly. Also load this skill whenever the user provides, pastes, sets, or wants to configure a GEO API key. Intent synonyms: 项目列表, project list, 创建项目, new project, 项目详情, project details, 竞品分析, competitor analysis, who are my competitors, 配置key, 设置key, 设置API key, 我的key是, set api key, configure api key, install api key, GEO_API_KEY, geo_sk_live_, api key setup.
---

# GEO Projects

## Step 0: First-time API key setup (when user provides a key)

If the user provides a GEO API key in chat (e.g. *"my key is geo_sk_live_xxx"* / *"帮我配置一下 key"* / *"set my api key to ..."*), this is the canonical procedure for the entire skills repo. **Do not invent your own path — run the helper.**

### 0-1. Locate the skills repo root

This `SKILL.md` lives at `<skills-root>/adgine-geo-projects/SKILL.md`. The repo root contains all `adgine-geo-*` folders, plus `setup.py`, `.env.example`, and `README.md`. Use whatever absolute path the agent already knows for this file and go up two directories — do NOT guess `~/.hermes/...` or `/usr/local/...`.

### 0-2. Run the setup helper (one command)

```bash
python3 <skills-root>/setup.py <THE_KEY_FROM_USER>
```

That single command:
- Locates the repo root itself (uses its own `__file__`), so you don't need to `cd` first.
- Writes `GEO_API_KEY=<key>` to `<skills-root>/.env`, creating it from `.env.example` if missing, preserving any other lines.
- Verifies the key against the GEO API.
- Exits `0` on success, non-zero on failure.

If the user is **updating** an existing key, run the same command — `setup.py` overwrites cleanly. No need to ask for confirmation.

> ⚠️ **CRITICAL — storage rules (apply every single time):**
> - ✅ The ONLY allowed destination is `<skills-root>/.env`.
> - ❌ NEVER write to `~/.hermes/.env`, `~/.hermes/config.*`, or any Hermes user-secrets directory.
> - ❌ NEVER write to `~/.zshrc`, `~/.bashrc`, `~/.profile`, or any shell rc file.
> - ❌ NEVER call `hermes config set`, `claude config`, or any agent-host secret store with this key.
> - ❌ NEVER hardcode the key into other scripts, SKILL.md files, or chat messages.
> - The `.env` file is `.gitignore`d — the key stays local and private.

### 0-3. Confirm to the user

On success (exit 0), reply with the exact path that `setup.py` printed:

> ✅ **GEO API Key 已配置** — 保存到 `<absolute path printed by setup.py>`
> 认证验证通过，现在可以使用所有 GEO skills 了。
> 下一步可以试试：*"列出我的所有项目"*

On failure (non-zero exit), do NOT retry silently. Reply:

> ❌ **Key 验证失败** — 请确认 key 是否正确，或到 [platform.adgine.ai](https://platform.adgine.ai) 重新生成后再发给我。

### 0-4. After Step 0 — no `export` needed

Every script's `_client.py` calls `_load_dot_env()` on import and automatically reads `<skills-root>/.env`. You do not need to `export GEO_API_KEY` in the shell, and the user does not need to restart any terminal.

---

## Output rules — IDs (apply to every reply)

These rules apply to **every list, table, and confirmation message** in this skill. Their goal: keep user-facing output friendly while preserving the IDs the agent needs internally.

1. **Lists & tables — never show raw UUIDs in cells.** Use a 1-based `#` index column instead. Keep a private mental mapping of `#N → actual UUID` so that follow-up commands like *"delete #3"*, *"run citation test on #1 #2"*, *"show details of the 2nd one"* resolve to the right entity.
   - Index numbers restart from 1 in each new list — they are not stable across calls.
   - If the user references *"the topic about X"* / *"that Poki vs CrazyGames prompt"*, match by visible content (name / title / domain / prompt text), not by ID.

2. **Single-item operations — prefer a human name over an ID.**
   - ✅ *"Project **Poki vs Competitors** deleted."*
   - ✅ *"Topic **Brand mentions in 2024** updated — name → 'Brand mentions 2025'."*
   - ❌ *"Project `a4305b57-1c79-4cec-a17c-16eb1d959ea6` deleted."*
   - If the entity has **no human-readable name** (e.g. an anonymous prompt or a job), use a short 8-character prefix: *"Prompt `2a2a8f4f…` deleted."* Never paste the full UUID.

3. **Always exception: `--json` mode.** When the user passes `--json` to a script or explicitly asks for raw JSON / debug output, print the script output verbatim — do not strip IDs.

4. **Internally, the agent still uses full UUIDs** for every API call (`--project-id`, `--topic-id`, `--prompt-id`, etc.). The display rules only affect what is shown back to the user.

---

## Step 1: Confirm authentication is working

Scripts auto-load `GEO_API_KEY` from `<skills-root>/.env` on import — **you don't need to `export` it**. To verify the configuration is healthy:

```bash
python3 scripts/check_auth.py
```

- ✅ Exits with "Authentication successful" → proceed.
- ❌ Exits with "GEO_API_KEY is not set" → the error message prints the exact `.env` path. Go to **Step 0** to install a key.
- ❌ Exits with 401 / auth failure → the key is invalid or expired. Ask the user for a new one and go to **Step 0**.

> ⚠️ **IMPORTANT:** In all shell/exec commands, always reference the key as `$GEO_API_KEY` (the environment variable). Never hardcode the key value or use placeholder strings like `API_KEY=***` or `API_KEY=geo_sk_live_xxx` directly in a command — this will cause authentication failures.

## Determine project ID

One API key manages all your projects. Resolve the project for each operation in this order:

1. `--project-id` argument passed to the script
2. `GEO_PROJECT_ID` env var (session shortcut, if set)
3. User mentioned a domain or website name → run `list_projects.py` and match
4. Nothing known → run `list_projects.py`, show results, ask the user to pick

To avoid repeating `--project-id` within a terminal session:
```bash
export GEO_PROJECT_ID=<id-from-list>   # resets when terminal closes
```

## Commands

### List all projects
```bash
python3 scripts/list_projects.py [--limit 20] [--json]
```

### Get project details
```bash
python3 scripts/manage_project.py get --project-id <id>
```

### Create a new project
```bash
python3 scripts/manage_project.py create --url https://example.com [--description "My site"]
```

### Update a project
```bash
python3 scripts/manage_project.py update --project-id <id> [--name "New Name"] [--url https://new.com]
```

### Delete a project
```bash
python3 scripts/manage_project.py delete --project-id <id>
```

### Manage competitors

List the competitor brands tied to a project:
```bash
python3 scripts/manage_competitors.py list [--project-id <id>] [--json]
```

Add a competitor:
```bash
python3 scripts/manage_competitors.py add --name "Acme" [--domain acme.com] \
    [--aliases "Acme Inc,Acme Corp"] [--source manual|brand_profile|ai_discovery]
```

Remove a competitor (DESTRUCTIVE — requires `--yes`):
```bash
python3 scripts/manage_competitors.py remove --competitor-id <id> --yes
```

## Output format

Default: human-readable summary table.
Pass `--json` for raw JSON (useful for piping to other scripts).

## Output Format

> ⚠️ **CRITICAL — Table cell content rule (must follow exactly):**
> Tables use fenced code blocks with box-drawing borders. They only align correctly when **every cell contains ASCII characters exclusively**.
> - **NEVER** put emoji inside table cells. They are 2 display units wide but count as 1 character, permanently misaligning all following columns.
> - Emoji go ONLY on the label line **above** the ` ``` ` fence.
> - Integration status in cells: `Connected` / `---` (NOT ✅/❌)

---

### When listing projects (`list_projects.py`)

> 📁 **Your GEO Projects** — **N** total

📋 Projects
```
┌────┬──────────────────┬─────┬─────┬────────────┐
│  # │ Name             │ GA4 │ CF  │ Created    │
├────┼──────────────────┼─────┼─────┼────────────┤
│  1 │ Example Site     │ OK  │ --- │ 2025-01-15 │
│  2 │ My Blog          │ --- │ --- │ 2025-03-22 │
└────┴──────────────────┴─────┴─────┴────────────┘
```
List project URLs below as clickable links:
- Example Site → [example.com](https://example.com)
- My Blog → [myblog.io](https://myblog.io)

If a selection is needed ask: *"Which project would you like to work with?"*

---

### When showing project details (`manage_project.py get`)

📁 Project Details
```
┌────────────┬──────────────────────────────────────┐
│ Name       │ Example Site                         │
│ URL        │ https://example.com                  │
│ Created    │ 2025-01-15                           │
│ GA4        │ Connected                            │
│ Cloudflare │ ---                                  │
└────────────┴──────────────────────────────────────┘
```
If any integration is `---`: > 🔌 Connect integrations at [platform.adgine.ai](https://platform.adgine.ai)

---

### When creating a project

✅ Project Created
```
┌────────────┬──────────────────────────────────────┐
│ Name       │ Example Site                         │

│ URL        │ https://example.com                  │
└────────────┴──────────────────────────────────────┘
```
> **Next:** connect integrations at [platform.adgine.ai](https://platform.adgine.ai)

### When updating

> ✅ Project **&lt;project name&gt;** updated — **&lt;field&gt;** → `<new value>`

### When deleting

> 🗑️ Project **&lt;project name&gt;** deleted.

### After auth check (`check_auth.py`)

> ✅ **Authenticated** — key valid for `<email or user-id>`

On failure:

> ❌ **Authentication failed.** Check `GEO_API_KEY` — get a key at [platform.adgine.ai](https://platform.adgine.ai)

---

## Post-task recommendations

After completing project operations, always end with 2–3 actionable next steps
based on what the project still needs. To check current state, run:

```bash
python3 <skills-root>/adgine-geo-dashboard/scripts/get_overview.py [--project-id <id>]
```

Read these indicators and suggest the earliest missing step in the GEO pipeline:

| Dashboard indicator | If zero / missing → Suggest |
|---|---|
| Topics count = 0 | `adgine-geo-topics` — 创建主题和提示词 |
| Prompts count = 0 | `adgine-geo-topics` — 批量生成 AI 搜索提示词 |
| Tests count = 0 | `adgine-geo-citation` — 运行引用测试 |
| Articles count = 0 | `adgine-geo-content` — 生成 GEO 优化文章 |
| GA4 not connected | `adgine-geo-integrations` — 连接 GA4 获取流量数据 |
| Cloudflare not connected | `adgine-geo-integrations` — 接入 Cloudflare 追踪 AI 爬虫 |
| Brand not generated | `adgine-geo-brand` — 生成品牌画像 |

Always present suggestions as:

> 💡 **建议下一步：**
> 1. **[action description]** → `skill-name`
> 2. **[action description]** → `skill-name`
