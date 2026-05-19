# Brand Cognition Generation Workflow

Brand cognition is how AI search engines (ChatGPT, Perplexity, Gemini, etc.) understand and represent your brand. This workflow covers initial brand setup and ongoing refinement.

---

## First-time setup

### Step 1 — Check current status
```bash
python3 scripts/get_brand.py --project-id <id>
```
If status is already `completed` and the fields look accurate, no further action needed.

### Step 2 — Generate brand profile (if missing or outdated)
```bash
python3 scripts/generate_brand.py --project-id <id> --language English --region US
```
The AI scrapes your website and auto-generates all brand fields. Typically 30–90 seconds.

**What gets generated:**
- `brand_introduction` — concise, authoritative brand description
- `ideal_customer` — ICP based on your product/service
- `competitors` — detected competitor landscape
- `brand_perspective` — unique angles and differentiators
- `author_persona` — narrative voice for content
- `voice_and_tone` — communication style
- `writing_rules` — usage guidelines

### Step 3 — Review each field
```bash
python3 scripts/get_brand.py --project-id <id>
```
Read through each generated field and decide what to refine.

### Step 4 — Refine specific fields
```bash
python3 scripts/update_brand.py --project-id <id> \
  --field voice_and_tone \
  --value "Professional but approachable. Rarely uses jargon. Uses data to support claims."
```
Repeat for each field that needs adjustment.

---

## Re-generation triggers

Re-run `generate_brand.py` when:
- Major website or product rebrand
- Significant new product / service launch
- Quarterly refresh for active content strategies
- Expanding to a new language or region

```bash
# Regenerate for a new market
python3 scripts/generate_brand.py --project-id <id> --language "Spanish" --region "MX"
```

---

## Integration with other skills

Brand cognition feeds into:
- **geo-content** — articles are written with your voice and tone
- **geo-topics** — generated prompts reflect your brand's ICP
- **geo-citation** — AI platforms cite you using your brand introduction
