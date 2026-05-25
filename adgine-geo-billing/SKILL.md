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

## Step 1: Locate your API key

**A)** `printenv GEO_API_KEY` → returns a value → proceed.
**B)** `grep '^GEO_API_KEY=' .env 2>/dev/null` → found → `export GEO_API_KEY=$(grep '^GEO_API_KEY=' .env | cut -d= -f2-)`
**C)** Not found → ask the user for a key from the GEO platform.

> In shell commands always reference the key as `$GEO_API_KEY` — never hardcode the literal value.

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
