---
name: adgine/geo-saas
description: Creates and tracks GEO SaaS-hosted websites — checks if a subdomain is available, kicks off an async website deployment with brand details, and polls deployment task status. Use when the user wants to launch a new SaaS website on the GEO platform (创建 SaaS 网站, 新建网站, 部署网站, launch website, create SaaS site), check whether a subdomain is taken (检查域名, subdomain availability, 二级域名), or check the progress of a website deployment task (部署状态, deployment status, task progress).
---

# GEO SaaS

Three-script flow for spinning up a SaaS-hosted website on the GEO platform:

1. **Check** that the desired subdomain is available.
2. **Create** the website (returns a task_id; deployment runs asynchronously).
3. **Poll** the task until it reaches a terminal state.

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
> ✅ When the task reports `Completed`, the website URL is available in the task payload.

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

## Related endpoints

| Method | Path |
|---|---|
| GET | `/api/saas/domain/check` |
| POST | `/api/saas/websites` |
| GET | `/api/saas/task/{task_id}` |
