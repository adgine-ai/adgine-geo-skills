---
name: adgine/geo-domains
description: Search available domains by keyword, list registered domains, and view domain registration details. Use when the user asks about domain availability, domain registration, domain search, 域名搜索, 域名注册, 查询域名, 我的域名, 域名状态. Read-only — does not register domains directly (direct users to the web UI for registration).
---

# GEO Domains

Read-only access to domain search and your registered domains. Use this skill when the
user asks "search domains for my brand" / "is example.com available?" / "show my
domains" / "域名搜索" / "查询域名" / "我的域名" / "这个域名能注册吗".

**Domain registration itself is done via the web UI** — after finding an available
domain, this skill provides a clickable registration link.

## Output rules — IDs (apply to every reply)

These rules apply to **every list, table, and confirmation message** in this skill.
Their goal: keep user-facing output friendly while preserving the IDs the agent needs
internally.

1. **Lists & tables — never show raw UUIDs in cells.** Use a 1-based `#` index column
   instead. Keep a private mental mapping of `#N → actual UUID` so that follow-up
   commands like *"show details of #3"* resolve to the right entity.
   - Index numbers restart from 1 in each new list — they are not stable across calls.

2. **Single-item operations — prefer a human name over an ID.**
   - ✅ *"Domain **example.com** — status: Active"*
   - ❌ *"Domain `a4305b57-...` — status: Active"*

3. **Always exception: `--json` mode.** When the user passes `--json` to a script or
   explicitly asks for raw JSON / debug output, print the script output verbatim — do
   not strip IDs.

4. **Internally, the agent still uses full UUIDs** for every API call (e.g.
   `get_domain.py <domain_id>`). The display rules only affect what is shown back to
   the user.

---

## Step 1: Make sure GEO_API_KEY is configured

Scripts auto-load `GEO_API_KEY` from `<skills-root>/.env` on import — **no `export`
needed, no shell restart needed**. To check the configuration, run any script (it prints
the exact `.env` path if the key is missing).

- ✅ Key already in `<skills-root>/.env` → proceed.
- ❌ Key missing, or user just gave you a new key → go to the **adgine-geo-projects**
  skill, **Step 0**, which runs `python3 <skills-root>/setup.py <KEY>` to write the key
  into the correct `.env` file. **Never** write the key to `~/.zshrc`, `~/.bashrc`,
  Hermes global config, or any user-secrets store.

> ⚠️ **IMPORTANT:** In all shell/exec commands, always reference the key as
> `$GEO_API_KEY` (the environment variable). Never hardcode the literal value.

---

## Scripts

### Search available domains by keyword

```bash
python3 scripts/search_domains.py <keyword> [--limit 20] [--json]
```

Searches for candidate domains matching the keyword. Returns availability status
(`available` / `taken` / `unsupported`), pricing (registration + renewal, including
service fees), and tier information.

**For available domains**, the script outputs a `## 马上注册` section at the end with
plain-text registration URLs in the format:
`https://platform.adgine.ai/domains/contact?domain={domain_name}`

> ⚠️ **YOU MUST include the full `## 马上注册` section verbatim in your reply.**
> Do NOT omit, summarise, or reformat this section. The user needs these URLs to
> register a domain. Simply copy-paste the entire section from the script output.

Already-registered or unsupported domains do not show a registration link.

### List my registered domains

```bash
python3 scripts/list_domains.py [--json]
```

Returns all domains registered by the current user, with status, expiration date,
auto-renew setting, and DNS status.

### Get domain registration details

```bash
python3 scripts/get_domain.py <domain_id> [--json]
```

Returns full details for a specific domain registration: Cloudflare state, Zone ID,
pricing, DNS configuration status, and any error messages.

---

## Agent Output Format

Run `search_domains.py <keyword>` (no `--json`). The script output uses a structured
plain-text format with labelled fields — parse it and render the results as described
below.

### Script output format

```
DOMAIN_SEARCH_RESULTS keyword=<kw>

TAKEN_DOMAINS count=N
  TAKEN <name>
  ...

AVAILABLE_DOMAINS count=N
  AVAILABLE name=<name> price=<price> renewal=<renewal> register_url=<url>
  ...

UNSUPPORTED_DOMAINS count=N
  UNSUPPORTED <name>
  ...
```

### How to render the results

**⚠️ MANDATORY RULE: every `AVAILABLE` domain MUST be rendered with a clickable
"[马上注册](register_url)" link. No exceptions. If a domain is available and you do
not show its registration link, the user cannot register it.**

Use this exact structure:

---

**❌ 已注册域名**

| 域名 | 状态 |
|------|------|
| mybrand.com | ❌ 已注册 |

---

**🏆 推荐首选** — pick the `.com` from the AVAILABLE list (or the first available if no `.com`)

| 域名 | 年费 | 续费 | |
|------|------|------|---|
| **mybrand.com** | $11.51 | $11.51/yr | [马上注册](https://platform.adgine.ai/domains/contact?domain=mybrand.com) |

---

**📋 其他可注册域名**

| # | 域名 | 年费 | 续费 | |
|---|------|------|------|---|
| 2 | mybrand.net | $13.05 | $13.05/yr | [马上注册](https://platform.adgine.ai/domains/contact?domain=mybrand.net) |
| 3 | mybrand.org | $9.35 | $12.32/yr | [马上注册](https://platform.adgine.ai/domains/contact?domain=mybrand.org) |

---

**💡 建议**

推荐优先注册 `.com`。所有可注册域名：

- [马上注册 mybrand.com](https://platform.adgine.ai/domains/contact?domain=mybrand.com)
- [马上注册 mybrand.net](https://platform.adgine.ai/domains/contact?domain=mybrand.net)
- [马上注册 mybrand.org](https://platform.adgine.ai/domains/contact?domain=mybrand.org)

---

The `register_url` value from the script output is the exact URL to use in the
`[马上注册](URL)` links. Do not construct it yourself — copy it directly from the
`register_url=` field in the script output.

> 🌐 **我的域名**

```
┌────┬──────────────────────┬──────────┬──────────────────────┬──────────┬──────────┐
│ #  │ Domain               │ Status   │ Expires              │ Renew    │ DNS      │
├────┼──────────────────────┼──────────┼──────────────────────┼──────────┼──────────┤
│ 1  │ mybrand.com          │ Active   │ 2027-06-16           │ Auto     │ OK       │
│ 2  │ another-site.io      │ Pending  │ --                   │ Auto     │ Pending  │
└────┴──────────────────────┴──────────┴──────────────────────┴──────────┴──────────┘
```

### get_domain.py

> 🌐 **Domain: mybrand.com**

```
┌────────────────────┬──────────────────────────────────┐
│ Field              │ Value                            │
├────────────────────┼──────────────────────────────────┤
│ Status             │ Active                           │
│ Cloudflare State   │ registered                       │
│ Zone ID            │ abc123...                        │
│ Price              │ $12.99 USD                       │
│ Expires            │ 2027-06-16                       │
│ Auto Renew         │ Yes                              │
│ DNS Status         │ configured                       │
│ Created            │ 2026-06-16T10:00:00Z             │
└────────────────────┴──────────────────────────────────┘
```

---

## Registration Flow

When the user has identified a domain they want to register, **do not attempt to
register via API**. Instead, present the clickable registration link:

```
[注册 {domain_name}](https://platform.adgine.ai/domains/contact?domain={domain_name})
```

The user will complete the registration form (contact info, Stripe payment) on the web.

---

## Related endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/domains/search` | 按关键词搜索候选域名 |
| GET | `/api/domains` | 当前用户的域名注册记录列表 |
| GET | `/api/domains/{domain_id}` | 单条域名注册记录详情 |
