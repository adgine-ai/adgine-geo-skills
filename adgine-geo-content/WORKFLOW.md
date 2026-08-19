# Content Generation Workflow

## 1. Select the source Topic and Prompts

Use the Topics Skill to list Topics and Prompts. Keep their full IDs internally, but show numbered, human-readable options to the user.

## 2. Recommend a title, type, and strategy

```bash
python3 scripts/generate_titles.py \
  --topic-id <topic-id> --prompt-ids <prompt-id-1,prompt-id-2>
```

Each recommendation contains a `title`, `type`, and `strategy`. If the user chooses one, pass all three to outline generation. If they provide only a title, let article type default to `authoritative`.

## 3. Generate the outline

```bash
python3 scripts/generate_outline.py \
  --topic-id <topic-id> --prompt-ids <prompt-id-1,prompt-id-2> \
  --title "Chosen title" --article-type comparison \
  --article-strategy "Compare decision criteria for buyers"
```

The script starts an async workflow, polls `/content/jobs/{job_id}`, then fetches the resulting content record to show the actual title and outline.

## 4. Review or edit the outline

```bash
python3 scripts/manage_content.py get --content-id <content-id>
python3 scripts/manage_content.py edit --content-id <content-id> --outline-file revised-outline.md
```

Only send changed fields. Omitted title, outline, metadata, body, schema, and cover values remain unchanged.

## 5. Generate an article version

```bash
python3 scripts/generate_article.py --content-id <content-id>
```

The article language inherits from the first selected Prompt. Pass `--language` only when the user explicitly wants a different language/version.

## 6. Edit or refine the article

For deterministic replacement fields:

```bash
python3 scripts/manage_content.py edit --content-id <content-id> \
  --body-file revised.md --meta-title "SEO title" --schema-file schema.json
```

For AI-guided changes:

```bash
python3 scripts/refine_article.py --content-id <content-id> \
  --instructions "Shorten the introduction and preserve all citations"
```

Both commands automatically use the selected/latest version unless `--version-id` is supplied.

## 7. Add a cover

Generate one:

```bash
python3 scripts/generate_cover.py --content-id <content-id> \
  --include-title --include-summary
```

Or upload a local image:

```bash
python3 scripts/manage_media.py upload --file cover.webp \
  --content-id <content-id> --alt "Accessible cover description"
```

## 8. Set GEO publish status

```bash
python3 scripts/manage_content.py publish-status --content-id <content-id> \
  --status published
```

This updates the selected article version’s GEO state. It does not push content to WordPress or another CMS.

## 9. Recover failed jobs

```bash
python3 scripts/manage_jobs.py get --job-id <job-id>
python3 scripts/manage_jobs.py retry --job-id <job-id>
```

Render one task inline. Use an HTML content-pipeline report only for multi-record analysis or when the user explicitly requests a report.
