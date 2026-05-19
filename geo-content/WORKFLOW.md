# Content Generation Workflow

This guide walks through the complete GEO content creation pipeline, from prompts to a published-ready article.

---

## Prerequisites

- **API key configured** — See [SETUP.md](../SETUP.md)
- **Prompts** — You need prompt IDs. Generate them first with the **geo-topics** skill.
- **Brand profile** — For best quality, ensure your brand profile is complete via the **geo-brand** skill.

---

## Step-by-step

### Step 1 — Get topic and prompt IDs

Use the **geo-topics** skill to list topics and prompts:

```bash
# From geo-topics/ skill directory:
python3 scripts/manage_topics.py list
python3 scripts/manage_prompts.py list --topic-id <topic-id>
```

Note: gather the `topic_id` and the prompt `id` values you want to use.

---

### Step 2 — (Optional) Suggest article titles

```bash
python3 scripts/generate_titles.py \
  --topic-id <tid> \
  --prompt-ids "prompt-id-1,prompt-id-2,prompt-id-3"
```

Returns AI-suggested titles. Pick one or write your own.

---

### Step 3 — Generate article outline

```bash
python3 scripts/generate_outline.py \
  --topic-id <tid> \
  --prompt-ids "prompt-id-1,prompt-id-2,prompt-id-3" \
  --title "Your Chosen Article Title" \
  --instructions "Emphasize cost-saving benefits, target CMO audience"
```

This creates a content item (status: `outline`) and polls until complete (~30–90 s).
The script prints the outline on completion and shows the `content_id`.

---

### Step 4 — Review the outline

```bash
python3 scripts/list_content.py --status outline
```

Review the generated outline. If needed, you can edit it:
- Contact your geo-platform dashboard to edit outline content
- Or proceed to article generation using the existing outline

---

### Step 5 — Generate the full article

```bash
python3 scripts/generate_article.py --content-id <content-id>
```

Polls until the article is complete (~60–180 s). Prints the article on completion.

---

### Step 6 — Review the article

```bash
python3 scripts/list_content.py --status article
```

The full article is ready in `full_content` (Markdown format). It includes:
- Article body
- FAQ section
- Citation opportunities analysis
- SEO metadata (title, description, slug)
- Word count

---

## Tips

- **Multiple articles**: Run steps 3–5 in parallel with different topics/prompts.
- **Re-generation**: Delete a content item with status `draft` or `outline` and start over.
- **Custom instructions**: Use `--instructions` in `generate_outline.py` to guide tone, audience, and structure.
- **Reference URLs**: Pass competitor or reference URLs via `--reference-urls` for better-informed outlines.
