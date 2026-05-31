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

**必须使用 `open` 命令打开 PDF 文件，让用户在系统默认 PDF 阅读器中查看：**

```bash
open "<this-skill-directory>/Adgine使用手册-v20260531.pdf"
```

> ⚠️ **CRITICAL — 必须执行，不可只输出路径：**
> 当用户说 "查看使用手册", "下载手册", "给我手册", "我要用户手册", "view manual", "download manual", "打开手册" 时：
> 1. **必须执行** `open` 命令（macOS）打开 PDF 文件，让系统弹出 PDF 阅读器
> 2. **禁止** 仅输出文件路径文本让用户自己去找文件
> 3. **禁止** 读取 markdown 内容做摘要/预览 — 用户要的是完整 PDF 文件
> 4. **禁止** 用 `cat` 或 `read_file` 读取 PDF 内容（二进制文件无法预览）
>
> 正确做法（在终端中执行）：
> ```bash
> open "/Users/lixingtang/longlu/project/backend/GEO/skills/adgine-geo-skills/adgine-geo-docs/Adgine使用手册-v20260531.pdf"
> ```
> 这会在系统默认 PDF 阅读器（如预览.app）中打开文件，用户可以直接阅读和下载/保存。

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

**执行以下命令打开 PDF（不是输出文本）：**

```bash
open "/Users/lixingtang/longlu/project/backend/GEO/skills/adgine-geo-skills/adgine-geo-docs/Adgine使用手册-v20260531.pdf"
```

执行后回复用户：

> 📄 **Adgine 使用手册 (v20260531)** 已在系统 PDF 阅读器中打开。
>
> 如果没有自动弹出，文件位置：
> `/Users/lixingtang/longlu/project/backend/GEO/skills/adgine-geo-skills/adgine-geo-docs/Adgine使用手册-v20260531.pdf`

### For content questions

- Provide a clear, concise answer based on the manual content
- Quote relevant sections when helpful
- Mention that this comes from the official Adgine 使用手册 (v20260531)
- If the user wants more detail, suggest they review the full PDF manual
