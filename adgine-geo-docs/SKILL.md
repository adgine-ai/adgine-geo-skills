---
name: adgine/geo-docs
description: Provides the Adgine platform user manual (使用手册). Use when the user asks how to use Adgine, needs help documentation, asks for the user guide, or mentions 使用手册, 帮助文档, 产品说明, user manual, documentation, help guide, how to use, 怎么用, 操作指南, 教程. This skill bundles the official Adgine user manual in both PDF (for reading/download) and Markdown (for agent content lookup) formats. No API key required.
---

# GEO Docs — Adgine 使用手册

This skill provides access to the official Adgine platform user manual.

## No authentication required

This skill is purely local — it reads bundled documentation files. No `GEO_API_KEY` or network access is needed.

## Files included

| File | Purpose |
|---|---|
| `Adgine使用手册-v20260531.pdf` | Formatted PDF manual for user viewing/download |
| `Adgine使用手册-v20260531.md` | Markdown version — agent can read this to answer content questions |

**Current version:** v20260531 (2025-05-31)

## Usage

### When the user asks about how to use Adgine

1. **Read** `Adgine使用手册-v20260531.md` (in this skill's directory) to find relevant content.
2. **Answer** the user's question based on the manual content.
3. **Reference** the PDF file if the user wants a downloadable/printable version.

### When the user asks for the manual file itself

Point the user to the PDF location:

```
<this-skill-directory>/Adgine使用手册-v20260531.pdf
```

### Finding content in the manual

To answer specific questions, read the `.md` file and search for relevant sections:

```bash
grep -i "<keyword>" "Adgine使用手册-v20260531.md"
```

Or read the full file to understand the manual structure and locate the answer.

## Output Format

When answering questions from the manual:

- Provide a clear, concise answer based on the manual content
- Quote relevant sections when helpful
- Mention that this comes from the official Adgine 使用手册 (v20260531)
- If the user wants more detail, suggest they review the full PDF manual
