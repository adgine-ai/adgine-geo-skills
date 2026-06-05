---
name: adgine/geo-wordpress
description: Connects a GEO project to a WordPress site (站点凭证管理 — site URL + username + application password), lists WP categories, publishes generated articles to WordPress (one-click or direct markdown), tracks publish history, and updates an existing WP post with the latest content version. Use when the user wants to publish GEO articles to WordPress (发布到 WordPress, push to WP, publish article), manage WP credentials (连接 WordPress, 绑定 WP, save WordPress credentials, application password), update an already-published post with the newest content (更新 WordPress 文章, sync to WP), check publish history (发布历史), or list WordPress categories.
---

# GEO WordPress

End-to-end WordPress publishing for GEO-generated content. Three steps:

1. **Connect** your WordPress site (save URL + username + application password).
2. **Publish** an article — either by `content_id` from the GEO content
   library, or directly with a title + markdown body.
3. **Update** an existing WP post when the GEO article is revised.

Use the **adgine-geo-content** skill to generate articles before publishing them.

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

## Step 1: Make sure GEO_API_KEY is configured

Scripts auto-load `GEO_API_KEY` from `<skills-root>/.env` on import — **no `export` needed, no shell restart needed**. To check the configuration, run any script (it prints the exact `.env` path if the key is missing).

- ✅ Key already in `<skills-root>/.env` → proceed.
- ❌ Key missing, or user just gave you a new key → go to the **adgine-geo-projects** skill, **Step 0**, which runs `python3 <skills-root>/setup.py <KEY>` to write the key into the correct `.env` file. **Never** write the key to `~/.zshrc`, `~/.bashrc`, Hermes global config, or any user-secrets store.

> ⚠️ **IMPORTANT:** In all shell/exec commands, always reference the key as `$GEO_API_KEY` (the environment variable). Never hardcode the literal value.

## Project selection

```bash
export GEO_PROJECT_ID=<project-id>
```

## Scripts

### 1) Credentials & categories

```bash
python3 scripts/manage_credentials.py status                     # connection state
python3 scripts/manage_credentials.py categories                 # live WP categories
python3 scripts/manage_credentials.py connect \
    --site-url https://example.com \
    --username admin \
    --password "abcd efgh ijkl mnop"
python3 scripts/manage_credentials.py disconnect --yes           # DESTRUCTIVE
```

> **WordPress application password** must be created in WP Admin → Users →
> Profile → Application Passwords. Plain user passwords will **not** work.

### 2) Publish an article

First find publishable content:
```bash
python3 scripts/list_publishable.py
```

Then publish:
```bash
# Mode A: by GEO content ID
python3 scripts/publish.py --content-id <uuid> [--category-ids 2,5] [--status publish|draft]

# Mode B: raw title + markdown body
python3 scripts/publish.py --title "My Post" --content-body "# Hello..."
```

### 3) Manage existing publishes

```bash
python3 scripts/manage_publishes.py list                          # publish history
python3 scripts/manage_publishes.py update --record-id <id>       # push latest content
python3 scripts/manage_publishes.py update --record-id <id> --status draft
```

## Output Format

ASCII tables only. Status vocabulary: `Connected` / `Disconnected` /
`publish` / `draft`. Width ≤80 chars max for tables with WP IDs / URLs.

```
┌────────────────────┬──────────────────────────────┐
│ Field              │ Value                        │
├────────────────────┼──────────────────────────────┤
│ Status             │ Connected                    │
│ site_url           │ https://example.com          │
│ username           │ admin                        │
└────────────────────┴──────────────────────────────┘
```

## Workflow narrative

> 1. **Connect**: `manage_credentials.py connect ...` (one-time).
> 2. **Verify**: `manage_credentials.py status` returns `Connected`.
> 3. **Discover**: `manage_credentials.py categories` to know which IDs to assign.
> 4. **List candidates**: `list_publishable.py`.
> 5. **Publish**: `publish.py --content-id <uuid> --category-ids 2,5`.
> 6. **Iterate**: if the article is revised in GEO, run
>    `manage_publishes.py update --record-id <id>` to push the new version
>    to the same WP post.

## Related endpoints

| Method | Path |
|---|---|
| GET    | `/api/projects/{id}/integrations/wordpress/credentials` |
| PUT    | `/api/projects/{id}/integrations/wordpress/credentials` |
| DELETE | `/api/projects/{id}/integrations/wordpress/credentials` |
| GET    | `/api/projects/{id}/integrations/wordpress/categories` |
| GET    | `/api/projects/{id}/integrations/wordpress/publishable-content` |
| POST   | `/api/projects/{id}/integrations/wordpress/publish` |
| GET    | `/api/projects/{id}/integrations/wordpress/publishes` |
| PUT    | `/api/projects/{id}/integrations/wordpress/publishes/{record_id}` |

---

## Post-task recommendations

After WordPress operations, suggest the next content or analysis step:

| You just… | Suggest next |
|---|---|
| Connected WordPress | `adgine-geo-content` — 生成 GEO 文章（现在可以直接发布） |
| Published an article | `adgine-geo-performance` — 检查已发布页面的 AI 优化健康度 |
| Updated a published post | `adgine-geo-citation` — 运行引用测试，验证更新后 AI 引用是否提升 |
| Listed publishable content | `adgine-geo-wordpress` — 选择一篇发布到 WordPress |
| Checked publish history | `adgine-geo-content` — 生成更多文章扩展内容库 |
| Disconnected WordPress | `adgine-geo-integrations` — 管理其他集成（GA4 / Cloudflare） |

> 💡 **建议下一步：**
> 1. **[action]** → `skill-name`
> 2. **[action]** → `skill-name`
