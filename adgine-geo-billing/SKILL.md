---
name: adgine/geo-billing
description: Queries GEO platform subscription and credits information — lists subscription plans, reports active subscription status, and queries detailed credits balance (subscription pool + purchased pool). Use when the user asks about pricing, plans, subscription status, billing, renewal, credits, balance, 套餐, 订阅, 价格, 续费, 余额, 积分, 充值, 支付, 查询积分, 我的积分, credits balance, 我用的什么套餐, 还剩多少积分, 购买积分. Read-only — does not perform purchases or plan changes (that requires the web UI).
---

# GEO Billing

Read-only access to subscription and credits state. Use this skill when the user asks
"what plan am I on?" / "how much does X cost?" / "when does my subscription
renew?" / "how many credits do I have left?" / "查询积分" / "我还有多少积分" /
"积分余额" / "充值了多少".

For purchases or plan changes, direct the user to the web checkout flow on the
GEO platform — those operations are not covered by this skill.

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

### List all subscription plans

```bash
python3 scripts/list_plans.py [--json]
```

### Get the current user's subscription

```bash
python3 scripts/get_subscription.py [--json]
```

### Get the current user's credits balance

```bash
python3 scripts/get_credits.py [--json]
```

Returns detailed credits breakdown: subscription pool (monthly allocation) vs
purchased pool (top-ups). Use this when the user asks about credits, 积分, 余额,
balance, or "how many credits do I have".

### Get credits pricing information

```bash
python3 scripts/get_credits_pricing.py [--json]
```

Returns unit price, min/max purchase limits, and preset options. Use when the
user asks "how much do credits cost?" / "积分多少钱" / "充值价格".

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

| Method | Path | Description |
|---|---|---|
| GET | `/api/payments/plans` | 所有套餐列表 |
| GET | `/api/payments/subscription` | 当前订阅状态 |
| GET | `/api/payments/credits/me` | 积分余额（订阅池+购买池） |
| GET | `/api/payments/credits/pricing` | 积分购买定价信息 |
