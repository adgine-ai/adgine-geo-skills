---
name: adgine/geo-projects
description: Lists, creates, retrieves, and manages GEO platform website projects.
  Use when the user needs to see their website projects, select a project to work
  on, create a new website project, check which project is active, or when any
  other GEO operation needs to identify a project ID before proceeding. Also use
  this skill first to verify authentication is configured correctly.
---

# GEO Projects

## Step 1: Locate your API key

Work through these in order:

**A)** Check if already set in environment:
```bash
printenv GEO_API_KEY
```
→ Returns a value → proceed to Step 2.

**B)** Check `.env` file:
```bash
grep '^GEO_API_KEY=' .env 2>/dev/null
```
→ Found → export it:
```bash
export GEO_API_KEY=$(grep '^GEO_API_KEY=' .env | cut -d= -f2-)
```

**C)** Not found → ask the user to create a key at https://platform.adgine.ai, then:
```bash
export GEO_API_KEY=geo_sk_live_xxx
```

> ⚠️ **IMPORTANT:** In all shell/exec commands, always reference the key as `$GEO_API_KEY` (the environment variable). Never hardcode the key value or use placeholder strings like `API_KEY=***` or `API_KEY=geo_sk_live_xxx` directly in a command — this will cause authentication failures.


Verify authentication is working:
```bash
python3 scripts/check_auth.py
```

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

## Output format

Default: human-readable summary table.
Pass `--json` for raw JSON (useful for piping to other scripts).

## Output Format

**When listing projects** (`list_projects.py`):
> 📁 **Your GEO Projects** (N total)

| # | Name | URL | Project ID | GSC | GA4 | CF | Created |
|---|------|-----|------------|-----|-----|----|---------|
| 1 | Example Site | example.com | `abc-123` | ✅ | ✅ | ❌ | 2025-01-15 |
| 2 | My Blog | myblog.io | `xyz-456` | ❌ | ❌ | ❌ | 2025-03-22 |

After listing, ask: *"Which project would you like to work with?"* (if context requires a selection).

---

**When showing project details** (`manage_project.py get`):

| Field | Value |
|-------|-------|
| Name | Example Site |
| Project ID | `abc-123-def` |
| URL | https://example.com |
| Created | 2025-01-15 |
| GSC | ✅ Connected |
| GA4 | ✅ Connected |
| Cloudflare | ❌ Not connected |

---

**When creating a project:**
> ✅ **Project created!**

| Field | Value |
|-------|-------|
| Name | Example Site |
| Project ID | `abc-123-def` |
| URL | https://example.com |

> Next: connect integrations at https://platform.adgine.ai

**When updating:**
> ✅ Project `abc-123-def` updated.

**When deleting:**
> 🗑️ Project `abc-123-def` deleted.

**After auth check** (`check_auth.py`):
> ✅ Authenticated — key is valid for user `<email or user-id>`  
> or: ❌ Authentication failed — check your `GEO_API_KEY`
