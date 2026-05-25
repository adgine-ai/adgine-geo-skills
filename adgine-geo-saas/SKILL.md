---
name: adgine/geo-saas
description: Creates and tracks GEO SaaS-hosted websites — checks if a subdomain is available, kicks off an async website deployment with brand details, and polls deployment task status. Use when the user wants to launch a new SaaS website on the GEO platform (创建 SaaS 网站, 新建网站, 部署网站, launch website, create SaaS site), check whether a subdomain is taken (检查域名, subdomain availability, 二级域名), or check the progress of a website deployment task (部署状态, deployment status, task progress).
---

# GEO SaaS

Three-script flow for spinning up a SaaS-hosted website on the GEO platform:

1. **Check** that the desired subdomain is available.
2. **Create** the website (returns a task_id; deployment runs asynchronously).
3. **Poll** the task until it reaches a terminal state.

## Step 1: Locate your API key

**A)** `printenv GEO_API_KEY` → returns a value → proceed.
**B)** `grep '^GEO_API_KEY=' .env 2>/dev/null` → found → `export GEO_API_KEY=$(grep '^GEO_API_KEY=' .env | cut -d= -f2-)`
**C)** Not found → ask the user for a key from the GEO platform.

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
