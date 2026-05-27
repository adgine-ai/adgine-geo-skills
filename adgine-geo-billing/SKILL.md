---
name: adgine/geo-billing
description: Queries GEO platform subscription information — lists all available subscription plans (pricing, features, billing interval) and reports the current user's active subscription (plan, status, renewal date, credits remaining). Use when the user asks about pricing, plans, subscription status, billing, renewal, credits, 套餐, 订阅, 价格, 续费, 余额, 我用的什么套餐. Read-only — does not perform purchases or plan changes (that requires the web UI).
---

# GEO Billing

Read-only access to subscription state. Use this skill when the user asks
"what plan am I on?" / "how much does X cost?" / "when does my subscription
renew?" / "how many credits do I have left?".

For purchases or plan changes, direct the user to the web checkout flow on the
GEO platform — those operations are not covered by this skill.

## Step 1: Make sure GEO_API_KEY is configured

Scripts auto-load `GEO_API_KEY` from `<skills-root>/.env` on import — **no `export` needed, no shell restart needed**. To check the configuration, run any script (it prints the exact `.env` path if the key is missing).

- ✅ Key already in `<skills-root>/.env` → proceed.
- ❌ Key missing, or user just gave you a new key → go to the **adgine-geo-projects** skill, **Step 0**, which runs `python3 <skills-root>/setup.py <KEY>` to write the key into the correct `.env` file. **Never** write the key to `~/.zshrc`, `~/.bashrc`, Hermes global config, or any user-secrets store.

> ⚠️ **IMPORTANT:** In all shell/exec commands, always reference the key as `$GEO_API_KEY` (the environment variable). Never hardcode the literal value.

## Scripts

### List all subscription plans

```bash
python3 scripts/list_plans.py [--json]
```

### Get the current user's subscription

```bash
python3 scripts/get_subscription.py [--json]
```

## Output Format

> **Table cell rule:** ASCII only inside fenced tables. Emoji allowed only on
> labels above the fence. Status vocabulary: `Active` / `Trialing` /
> `Cancelled` / `Past_due` etc. Change values: `+N` / `-N` / `--` / `0`.

### Recommended layout

> 💳 **Current Subscription**

```
┌────────────────────┬──────────────────────────────┐
│ Field              │ Value                        │
├────────────────────┼──────────────────────────────┤
│ Plan               │ Pro                          │
│ Status             │ Active                       │
│ Renews             │ 2025-12-01                   │
│ Credits Remaining  │ 4,210 / 10,000               │
└────────────────────┴──────────────────────────────┘
```

> 💰 **Available Plans**

```
┌────────────────────┬──────────┬──────────┬──────────────────────────┐
│ Plan               │    Price │ Interval │ Notes                    │
├────────────────────┼──────────┼──────────┼──────────────────────────┤
│ Free               │        0 │ month    │ Starter tier             │
│ Pro                │   49 USD │ month    │ 10,000 credits           │
│ Enterprise         │  Custom  │ month    │ Contact sales            │
└────────────────────┴──────────┴──────────┴──────────────────────────┘
```

## Related endpoints

| Method | Path |
|---|---|
| GET | `/api/payments/plans` |
| GET | `/api/payments/subscription` |
