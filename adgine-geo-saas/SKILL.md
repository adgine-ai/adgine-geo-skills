---
name: adgine/geo-saas
description: Creates and tracks GEO SaaS-hosted websites — checks if a subdomain is available, kicks off an async website deployment with brand details, and polls deployment task status. Use when the user wants to launch a new SaaS website on the GEO platform (创建 SaaS 网站, 新建网站, 部署网站, launch website, create SaaS site), check whether a subdomain is taken (检查域名, subdomain availability, 二级域名), or check the progress of a website deployment task (部署状态, deployment status, task progress).
---

# GEO SaaS

Three-script flow for spinning up a SaaS-hosted website on the GEO platform:

1. **Check** that the desired subdomain is available.
2. **Create** the website (returns a task_id; deployment runs asynchronously).
3. **Poll** the task until it reaches a terminal state.

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

## Scripts

### 1) Check subdomain availability

```bash
python3 scripts/check_domain.py --subdomain mysite [--json]
```

### 2) Create the website (async)

```bash
python3 scripts/create_website.py --subdomain mysite \
    --brand-name "My Site" \
    --industry "SaaS" \
    --description "An AI-first content platform" \
    --language English \
    [--json]
```

Returns a `task_id`. Pass it to the next step.

### 3) Track the deployment task

```bash
python3 scripts/get_task.py --task-id <id> [--poll] [--json]
```

Add `--poll` to block until the task reaches `Completed` or `Failed`.

## Recommended flow

> 🌐 **Step 1.** Check `mysite` is available.
>
> 🚀 **Step 2.** Start deployment, capture `task_id`.
>
> ⏳ **Step 3.** Poll status (use `--poll`).
>
> ✅ When the task reports `Completed`, the script prints the site URL **and** the WordPress admin login URL, username, and password automatically.

## Output Format

ASCII tables only. Status vocabulary:
`Pending` / `Generating` / `Completed` / `Failed`.

```
┌────────────────────┬──────────────────────────────┐
│ Field              │ Value                        │
├────────────────────┼──────────────────────────────┤
│ status             │ Generating                   │
│ progress           │ 60%                          │
│ subdomain          │ mysite                       │
└────────────────────┴──────────────────────────────┘
```

### Completed state — always show WordPress credentials

When `status` is `Completed` **and** the response includes `wp_username` / `wp_password`, the script automatically appends a second table with the WordPress login details:

```
🎉 Your website is live! WordPress login details:

┌────────────────────┬──────────────────────────────┐
│ WordPress          │ Info                         │
├────────────────────┼──────────────────────────────┤
│ login URL          │ https://mysite.adgine.net/wp-login.php │
│ username           │ admin                        │
│ password           │ xxxxxxxx                     │
└────────────────────┴──────────────────────────────┘
```

- The login URL is derived from the `domain` field in the task response: `https://<domain>/wp-login.php`. The `domain` is the full subdomain (e.g. `gamecalc.adgine.net`); `adgine.net` and `/wp-login.php` are always fixed.
- **Never omit** the credentials table when status is Completed — this is the primary way the user learns how to access their new site.

## Related endpoints

| Method | Path |
|---|---|
| GET | `/api/saas/domain/check` |
| POST | `/api/saas/websites` |
| GET | `/api/saas/task/{task_id}` |
