---
name: adgine/geo-content
description: Generates and manages international GEO article titles, outlines, article versions, refinements, covers, metadata, media, publish status, and unified workflow jobs. Use for 写文章, 生成大纲, 标题推荐, 内容编辑, 文章版本, 微调文章, 生成封面, 上传封面, 发布状态, article generation, outline generation, content jobs, and retrying failed content tasks.
---

# GEO Content

Use this Skill for content mutations and individual content/job inspection. Use `adgine/geo-reports` for content-pipeline overviews and larger read-only datasets that benefit from an HTML report.

Scripts load `GEO_API_KEY` from the repository `.env`. If it is missing, use
the repository `setup.py` flow; never place or print the literal key in a shell
command, Skill file, or user-facing output.

## Interaction defaults

- Treat omitted update fields as “keep the current value.” Send only fields the user changes.
- When an operation needs `version_id` and the user omits it, fetch the content and use `selected_version_id`; fall back to the highest `version_no`.
- Let GEO-Api inherit/default values when appropriate: Prompt language for article generation and `authoritative` for outline article type.
- Render a single job status inline. Do not generate HTML for one task unless the user explicitly requests HTML.
- Use `--json` only when raw IDs/debug data are needed. Otherwise refer to content by title and jobs/versions by an 8-character ID prefix.

## Content lifecycle

```text
select Topic + Prompts
  → recommend titles (title + type + strategy)
  → generate outline
  → review/edit outline
  → generate article version
  → edit or refine version
  → generate/upload cover
  → set version publish status
```

Content stage is `draft`, `outline`, or `article`. Publish state is version-level `unpublished` or `published`; it is changed through the dedicated publish-status endpoint, not by editing content stage.

## Commands

Run commands from this Skill directory. Supply `--project-id` or set `GEO_PROJECT_ID`.

### Read content

```bash
python3 scripts/list_content.py [--status draft|outline|article] \
  [--publish-status unpublished|published|partial] [--topic-id <id>] \
  [--page 1] [--limit 40] [--json]

python3 scripts/manage_content.py get --content-id <id> [--version-id <id>] [--json]
python3 scripts/manage_content.py versions --content-id <id> [--json]
python3 scripts/manage_content.py get-version --content-id <id> [--version-id <id>] [--json]
```

`get-version` automatically selects the current/latest version if `--version-id` is omitted.

### Recommend titles

```bash
python3 scripts/generate_titles.py --topic-id <id> --prompt-ids <id1,id2,...>
```

Use the returned `title`, `type`, and `strategy` together when generating the outline.

### Generate an outline

```bash
python3 scripts/generate_outline.py --topic-id <id> --prompt-ids <id1,id2,...> \
  [--title "Chosen title"] \
  [--article-type authoritative|listicle|comparison] \
  [--article-strategy "Why this format fits"] \
  [--reference-urls "https://a.example,https://b.example"] \
  [--instructions "Audience, tone, and constraints"] [--json]
```

Omit `--title` to let GEO-Api generate one. Omit `--article-type` to use `authoritative`.

### Generate an article version

```bash
python3 scripts/generate_article.py --content-id <id> [--language zh] \
  [--show-article] [--json]
```

Omit `--language` to inherit the first selected Prompt’s language.

### Partially edit content

```bash
python3 scripts/manage_content.py edit --content-id <id> \
  [--version-id <id>] [--title "New title"] [--outline-file outline.md] \
  [--body-file article.md] [--meta-title "SEO title"] \
  [--meta-description "Summary"] [--meta-slug "url-slug"] \
  [--schema-file schema.json] [--cover-image-url https://...] \
  [--cover-image-alt "Description"]
```

Map files/arguments to the current GEO-Api schema:

- `--body-file` → `full_content`
- `--outline-file` → `page_outline`
- `--schema-file` → validated JSON serialized as `schema_markup`
- cover/meta/body fields → the selected/latest version
- title/outline/slug → the shared content record

Never send the obsolete mutation fields `article_body` or `status`.

### Refine an article

```bash
python3 scripts/refine_article.py --content-id <id> \
  (--instructions "Make the tone more concise" | --instructions-file request.txt) \
  [--version-id <id>] [--show-article] [--json]
```

The backend refines the selected version in place through a unified workflow job.

### Manage covers and media

```bash
python3 scripts/generate_cover.py --content-id <id> [--version-id <id>] \
  [--prompt "Visual direction"] [--include-title] [--include-summary] [--include-body]

python3 scripts/manage_media.py list [--q "article title"] [--source content] \
  [--page 1] [--limit 40] [--json]

python3 scripts/manage_media.py upload --file cover.png \
  [--content-id <id>] [--version-id <id>] [--alt "Accessible description"] [--json]
```

Uploads accept JPG, JPEG, PNG, WebP, or GIF up to 5 MB. With `--content-id`, the script automatically selects a version, sets the cover, and lets GEO-Api register it in project media. Alt text defaults to the article title, then the filename.

### Set publish status and delete

```bash
python3 scripts/manage_content.py publish-status --content-id <id> \
  --status unpublished|published [--version-id <id>]

python3 scripts/manage_content.py delete-version --content-id <id> \
  [--version-id <id>] --yes

python3 scripts/manage_content.py delete --content-id <id> --yes
```

These commands manage GEO content state only. Publishing to WordPress remains a separate integration flow and is outside this change.

### Inspect and retry jobs

GEO-Api uses one job collection for `outline`, `article`, `refine`, and `cover_image`.

```bash
python3 scripts/manage_jobs.py list [--workflow-type outline|article|refine|cover_image] \
  [--topic-id <id>] [--page 1] [--limit 40]
python3 scripts/manage_jobs.py get --job-id <id>
python3 scripts/manage_jobs.py retry --job-id <id>
```

Legacy command aliases (`list-outline`, `list-article`, `get-outline`, `get-article`, and workflow variants) still work, but all call `/content/jobs`.

## Output

- Keep small mutation confirmations and individual job/version details inline.
- Use human titles and numbered rows for lists; do not expose full UUIDs unless raw JSON was requested.
- After an async operation completes, state the content title, resulting stage/status, selected version, and the natural next action.
- Do not claim that a GEO publish-status change published an article to an external CMS.

See `WORKFLOW.md` for the recommended end-to-end sequence.
