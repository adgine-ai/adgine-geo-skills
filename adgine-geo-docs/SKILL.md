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

### When the user asks to view or download the user manual (查看手册 / 下载手册 / 我要手册)

**必须输出 PDF 文件的 Markdown 链接，让用户看到可点击的下载/预览按钮：**

> ⚠️ **CRITICAL — 必须输出可点击的文件链接：**
> 当用户说 "查看使用手册", "下载手册", "给我手册", "我要用户手册", "view manual", "download manual", "打开手册" 时：
> 1. **必须** 输出 Markdown 格式的文件链接，让用户可以直接点击下载或预览
> 2. **禁止** 自动执行 `open` 命令打开文件（用户没有要求自动打开）
> 3. **禁止** 仅输出纯文本路径让用户复制粘贴
> 4. **禁止** 读取 markdown 内容做摘要/预览 — 用户要的是完整 PDF 文件
> 5. **禁止** 用 `cat` 或 `read_file` 读取 PDF 内容（二进制文件无法预览）
>
> 正确做法 — 输出以下 Markdown 链接（用户点击即可下载/预览）：
> ```markdown
> [📄 Adgine使用手册-v20260531.pdf](adgine-geo-docs/Adgine使用手册-v20260531.pdf)
> ```
> 或使用绝对路径：
> ```markdown
> [📄 Adgine使用手册-v20260531.pdf](/Users/lixingtang/longlu/project/backend/GEO/skills/adgine-geo-skills/adgine-geo-docs/Adgine使用手册-v20260531.pdf)
> ```

### When the user asks a specific question about how to use Adgine

1. **Read** `Adgine使用手册-v20260531.md` (in this skill's directory) to find relevant content.
2. **Answer** the user's question based on the manual content.
3. **Reference** the PDF file if the user wants a formatted/printable version.

### Finding content in the manual

To answer specific questions, read the `.md` file and search for relevant sections:

```bash
grep -i "<keyword>" "Adgine使用手册-v20260531.md"
```

Or read the full file to understand the manual structure and locate the answer.

## Output Format

### For view/download requests

**直接输出以下内容（Markdown 文件链接 + 说明）：**

> 📄 **Adgine 使用手册 (v20260531)**
>
> [点击下载/预览 PDF](adgine-geo-docs/Adgine使用手册-v20260531.pdf)
>
> 这是 Adgine 平台的完整使用手册，包含所有功能的详细操作指南。

### For content questions

- Provide a clear, concise answer based on the manual content
- Quote relevant sections when helpful
- Mention that this comes from the official Adgine 使用手册 (v20260531)
- If the user wants more detail, suggest they review the full PDF manual
