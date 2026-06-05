# adgine-geo-skills

Agent Skills are folders of instructions, scripts, and resources that AI agents load to perform specialized tasks in a repeatable way. This repository packages the full [Adgine GEO platform](https://platform.adgine.ai) workflow as a set of skills — from setting up a project and measuring AI visibility, to generating optimized content and publishing it to WordPress.

**Works with all mainstream AI agents.** Supports [WorkBuddy](https://workbuddy.ai), [Codex](https://openai.com/codex), [OpenClaw](https://github.com/openclaw/openclaw), and [Hermes](https://github.com/hermes-agent/hermes).

**Current version:** [`v1.0.2`](VERSION) · [All releases](https://github.com/adgine-ai/adgine-geo-skills/releases)

---

## Install

The install prompt is the same for every supported agent — send it directly to your agent of choice:

```
Install skills from https://github.com/adgine-ai/adgine-geo-skills
```

Known compatible agents:

- **[WorkBuddy](https://workbuddy.ai)**
- **[Codex](https://openai.com/codex)**
- **[OpenClaw](https://github.com/openclaw/openclaw)**
- **[Hermes](https://github.com/hermes-agent/hermes)**

After the agent finishes installing, paste your GEO API key in chat (e.g. *"my GEO API key is geo_sk_live_xxx, please configure it"*). The agent will run the included `setup.py` helper to write the key to a local, gitignored `.env` file at the skills repo root — not to your shell rc, not to the agent's global config.

### Manual install (advanced)

Clone the repo and run the setup helper yourself:

```bash
git clone https://github.com/adgine-ai/adgine-geo-skills.git
cd adgine-geo-skills

# One-shot setup — writes your API key to a local .env (gitignored):
python3 setup.py <YOUR_GEO_API_KEY>
# ...or run the interactive wizard:
python3 setup.py
```

All scripts auto-load `GEO_API_KEY` from `.env` on import — no `export`, no shell rc edits, no terminal restart needed.

---

## Updates

The installed version is recorded in the [`VERSION`](VERSION) file at the repo root. Releases are published at [github.com/adgine-ai/adgine-geo-skills/releases](https://github.com/adgine-ai/adgine-geo-skills/releases).

### For AI agents — how to check and apply updates

Use the following steps whenever the user asks whether skills are up to date, or to update skills:

**Step 1 — Read the installed version**

```bash
cat "$(find ~ -name VERSION -path '*/adgine-geo-skills/VERSION' 2>/dev/null | head -1)"
```

**Step 2 — Fetch the latest release from GitHub**

```bash
curl -s https://api.github.com/repos/adgine-ai/adgine-geo-skills/releases/latest
```

Key fields to read from the response:
- `tag_name` — latest version (e.g. `v1.3.0`)
- `name` — release title
- `body` — changelog / release notes
- `published_at` — release date

Alternatively, fetch just the raw version string (no JSON parsing needed):

```bash
curl -s https://raw.githubusercontent.com/adgine-ai/adgine-geo-skills/main/VERSION
```

**Step 3 — Present result to user**

- If versions match: report that skills are up to date and show the current version.
- If behind: show the current version, the latest version, and the release notes from `body`. Ask the user if they want to update.

**Step 4 — Apply update (if requested)**

```bash
cd <skills-repo-path>
git pull
```

The `.env` file (API key) is gitignored and is never modified by `git pull`. No reconfiguration needed after updating.

### User-facing prompt

Users can trigger a version check or update with natural language:

> *"Are my Adgine skills up to date?"*  
> *"Check for skill updates."*  
> *"Update my Adgine skills to the latest version."*

---

## What is GEO?

**Generative Engine Optimization (GEO)** is the practice of optimizing your brand and content to be cited, referenced, and recommended by AI search engines — ChatGPT, Perplexity, Google AI Overviews, Gemini, and more. These skills give you programmatic access to the full GEO workflow through natural language, with your agent as the interface.

---

## Skills

| Skill | What it does |
|---|---|
| [`adgine-geo-projects`](adgine-geo-projects/) | List, create, update, delete projects; manage competitors; verify auth; configure API key |
| [`adgine-geo-dashboard`](adgine-geo-dashboard/) | Project snapshot — visibility score, aggregate metrics, 7-day trend, integration health |
| [`adgine-geo-analytics`](adgine-geo-analytics/) | Traffic overview — GA4 sessions, active users, source breakdown, AI referral summary |
| [`adgine-geo-aiagent`](adgine-geo-aiagent/) | AI bot & human traffic deep drill-down — 27 endpoints: per-bot KPIs, platform rankings, Sankey flows, raw event logs, per-page deep dives (KPI / logs / platforms / PageSpeed) |
| [`adgine-geo-visibility`](adgine-geo-visibility/) | Deep AI visibility analytics — Visibility Score, Share of Voice, Average Position, competitor matrix, topic/prompt-level metrics, historical AI execution details & full responses |
| [`adgine-geo-citation`](adgine-geo-citation/) | Citation tests across ChatGPT / Perplexity / Google AIO / Gemini; brand mention rates, cited URLs, full AI reply text |
| [`adgine-geo-brand`](adgine-geo-brand/) | Generate and manage AI-facing brand profiles — intro, ICP, competitor analysis, author persona, voice & tone, writing rules; list/inspect/retry brand generation jobs |
| [`adgine-geo-topics`](adgine-geo-topics/) | Create and manage topics & AI search prompts; batch-generate prompts with AI; cross-topic prompt listing |
| [`adgine-geo-content`](adgine-geo-content/) | Full content pipeline — generate titles, outlines, and full GEO-optimized articles; manage content library; inspect and retry background jobs |
| [`adgine-geo-performance`](adgine-geo-performance/) | Per-page AI crawlability, optimization scores, and content health checks (mobile/desktop) |
| [`adgine-geo-opportunities`](adgine-geo-opportunities/) | AI-discovered content gaps and optimization opportunities ranked by impact — relevance, traffic, competition, urgency, AI citation scores |
| [`adgine-geo-integrations`](adgine-geo-integrations/) | Connect GA4 (OAuth) and Cloudflare; deploy AI crawler tracking Worker; sync traffic data; query integration-specific data |
| [`adgine-geo-wordpress`](adgine-geo-wordpress/) | Publish GEO articles to WordPress; manage credentials & categories; track publish history; update existing posts |
| [`adgine-geo-saas`](adgine-geo-saas/) | Check subdomain availability; create and track SaaS-hosted website deployments |
| [`adgine-geo-billing`](adgine-geo-billing/) | View plan, status, renewal date, remaining credits, and credits pricing |
| [`adgine-geo-docs`](adgine-geo-docs/) | Adgine platform user manual (使用手册) — hosted PDF, no API key required |
| [`adgine-geo-site-audit`](adgine-geo-site-audit/) | **Standalone** GEO technical audit for any public URL — 5-dimension 30-item checklist, local crawl, PDF report export. No API key required |

Each skill is self-contained in its own folder with a `SKILL.md` file containing the instructions and metadata that agents use for tool routing and intent matching.

---

## Repository Structure

```
adgine-geo-skills/
├── VERSION                        # Current release version
├── setup.py                       # API key configuration helper
├── .env.example                   # Environment variable template
├── adgine-geo-<domain>/
│   ├── SKILL.md                   # Agent skill definition — YAML frontmatter (name, description) + usage instructions
│   ├── WORKFLOW.md                # (some skills) End-to-end workflow guide
│   └── scripts/
│       ├── _client.py             # Shared API client for the domain
│       └── *.py                   # One script per operation
├── adgine-geo-site-audit/
│   ├── SKILL.md
│   ├── README.md                  # Site audit-specific docs
│   ├── requirements.txt           # Standalone dependencies (curl_cffi, bs4, reportlab, etc.)
│   ├── scripts/                   # geo_collect, geo_score, geo_visibility, render_report_pdf, etc.
│   └── tests/                     # Unit tests for site audit modules
└── ref/                           # Reference documentation (Chinese)
```

---

## Setup

### 1. Get your API key

Sign in at [platform.adgine.ai](https://platform.adgine.ai) and generate an API key.

### 2. Configure environment

Use the included setup helper — it writes the key to `<repo>/.env` and verifies it:

```bash
python3 setup.py <YOUR_GEO_API_KEY>     # non-interactive (good for AI agents)
python3 setup.py                         # interactive wizard
```

Prefer to do it manually? Copy the template and edit:

```bash
cp .env.example .env
# then edit .env and set GEO_API_KEY=geo_sk_live_YOUR_KEY_HERE
```

All scripts read `.env` automatically on import — no `export` needed.

### 3. Find your project ID

```bash
python3 adgine-geo-projects/scripts/list_projects.py
export GEO_PROJECT_ID=<your-project-id>
```

### 4. Ask your agent

Once the skills are loaded, use natural language:

> *"What's my AI visibility score this week?"*  
> *"Generate a brand profile for my project."*  
> *"Which AI platforms are crawling my site the most?"*  
> *"Publish article 123 to my WordPress site."*  
> *"Audit example.com for GEO score and export a PDF."*  
> *"What optimization opportunities does my project have?"*

Or run scripts directly:

```bash
# Dashboard snapshot
python3 adgine-geo-dashboard/scripts/get_overview.py

# AI visibility score
python3 adgine-geo-visibility/scripts/get_visibility.py score

# AI bot traffic platform ranking
python3 adgine-geo-aiagent/scripts/bot_traffic.py platforms

# Generate article outline
python3 adgine-geo-content/scripts/generate_outline.py --topic-id <id> --prompt-ids <id1,id2>

# Standalone site audit (no API key needed)
python3 adgine-geo-site-audit/scripts/geo_collect.py https://example.com --max-subpages 20

# Check credits balance
python3 adgine-geo-billing/scripts/get_credits.py
```

---

## Authentication

All scripts read from the `GEO_API_KEY` environment variable. Never hardcode your key or commit it to version control. The `.env` file is gitignored by default.

---

## Requirements

- Python 3.9+
- `requests` (`pip install requests`)
- An [Adgine GEO](https://platform.adgine.ai) account with an active API key (not required for `adgine-geo-site-audit` and `adgine-geo-docs`)
- **Site audit only:** additional packages — run `pip install -r adgine-geo-site-audit/requirements.txt`

---

## Disclaimer

These skills are provided for use with the Adgine GEO platform API. Always test in your own environment before relying on them for critical workflows.

---

## License

See [LICENSE](LICENSE) for details.
