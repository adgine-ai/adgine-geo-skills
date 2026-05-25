# adgine-geo-skills

A collection of **GitHub Copilot Agent skills** for the [Adgine GEO platform](https://platform.adgine.ai) — enabling AI-powered Generative Engine Optimization (GEO) workflows directly from your editor or CI pipeline via natural language.

Each skill exposes a focused domain of the GEO API through lightweight Python scripts, with structured `SKILL.md` files that tell Copilot Agent when and how to invoke them.

---

## What is GEO?

**Generative Engine Optimization (GEO)** is the practice of optimizing your brand and content to be cited, referenced, and recommended by AI search engines (ChatGPT, Perplexity, Google AI Overviews, Gemini, etc.). This repo gives you programmatic access to the full GEO workflow: from setting up a project and building brand identity, to measuring AI visibility, creating optimized content, and publishing it to WordPress.

---

## Skills Overview

| Skill | Description |
|---|---|
| [`adgine-geo-projects`](adgine-geo-projects/) | List, create, update, delete projects; manage competitor lists; verify API auth |
| [`adgine-geo-dashboard`](adgine-geo-dashboard/) | Project snapshot — visibility score, 7-day trend, integration health |
| [`adgine-geo-analytics`](adgine-geo-analytics/) | Traffic overview — GA4 sessions, AI referrals, crawler data |
| [`adgine-geo-aiagent`](adgine-geo-aiagent/) | AI bot & human traffic analytics — crawler KPIs, platform breakdowns, page Sankey flows, per-page deep dives |
| [`adgine-geo-visibility`](adgine-geo-visibility/) | Deep AI visibility analytics — Visibility Score, Share of Voice, Average Position, competitor matrix, prompt-level history |
| [`adgine-geo-citation`](adgine-geo-citation/) | Run citation tests across ChatGPT / Perplexity / Google AIO / Gemini; view brand mention rates and cited URLs |
| [`adgine-geo-brand`](adgine-geo-brand/) | Generate and manage AI-facing brand cognition profiles (brand intro, ICP, competitor analysis, voice & tone) |
| [`adgine-geo-topics`](adgine-geo-topics/) | Create topics and AI search prompts; batch-generate prompts with AI |
| [`adgine-geo-content`](adgine-geo-content/) | Generate GEO-optimized article titles, outlines, and full articles; manage content pipeline and jobs |
| [`adgine-geo-performance`](adgine-geo-performance/) | Per-page AI crawlability, optimization scores, and content health checks |
| [`adgine-geo-integrations`](adgine-geo-integrations/) | Connect GA4 (OAuth) and Cloudflare; deploy AI crawler tracking Worker; sync traffic data |
| [`adgine-geo-wordpress`](adgine-geo-wordpress/) | Publish GEO articles to WordPress; manage WP credentials; update existing posts |
| [`adgine-geo-saas`](adgine-geo-saas/) | Check subdomain availability; create and track SaaS-hosted website deployments |
| [`adgine-geo-billing`](adgine-geo-billing/) | View subscription plan, status, renewal date, and remaining credits |

---

## Repository Structure

```
adgine-geo-skills/
├── adgine-geo-<domain>/
│   ├── SKILL.md          # Copilot Agent skill definition (name, description, instructions)
│   ├── WORKFLOW.md       # (some skills) End-to-end workflow guide
│   └── scripts/
│       ├── _client.py    # Shared API client for the domain
│       └── *.py          # One script per operation
└── .env.example          # Environment variable template
```

---

## Getting Started

### 1. Get your API key

Sign in at [platform.adgine.ai](https://platform.adgine.ai) and generate an API key.

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env and set your key:
# GEO_API_KEY=geo_sk_live_YOUR_KEY_HERE
```

Then export it in your shell session:

```bash
export GEO_API_KEY=$(grep '^GEO_API_KEY=' .env | cut -d= -f2-)
```

### 3. Find your project ID

```bash
python3 adgine-geo-projects/scripts/list_projects.py
export GEO_PROJECT_ID=<your-project-id>
```

### 4. Run any script

```bash
# Dashboard snapshot
python3 adgine-geo-dashboard/scripts/get_overview.py

# AI visibility score
python3 adgine-geo-visibility/scripts/get_visibility.py score

# Which AI bots crawl my site?
python3 adgine-geo-aiagent/scripts/bot_traffic.py platforms

# Generate an article outline
python3 adgine-geo-content/scripts/generate_outline.py --topic-id <id> --prompt-ids <id1,id2>
```

### 5. Use with GitHub Copilot Agent

Each `SKILL.md` is automatically discovered by Copilot Agent. Once the repo is in your workspace, you can ask things like:

> *"What's my AI visibility score this week?"*  
> *"Generate a brand profile for my project."*  
> *"Which AI platforms are sending me the most traffic?"*  
> *"Publish article 123 to my WordPress site."*

---

## Authentication

All scripts authenticate via the `GEO_API_KEY` environment variable. **Never hardcode your key** in scripts or commit it to version control. The `.env` file is gitignored by default.

---

## Requirements

- Python 3.9+
- `requests` library (`pip install requests`)
- A GEO platform account with an active API key

---

## License

See [LICENSE](LICENSE) for details.
