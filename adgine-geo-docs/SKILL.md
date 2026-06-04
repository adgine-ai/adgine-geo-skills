---
name: adgine/geo-docs
description: Provides the Adgine platform user manual (使用手册). Use when the user asks how to use Adgine, needs help documentation, asks for the user guide, or mentions 使用手册, 帮助文档, 产品说明, user manual, documentation, help guide, how to use, 怎么用, 操作指南, 教程. This skill points to the official Adgine user manual hosted online (PDF). No API key required.
---

# GEO Docs — Adgine 使用手册

This skill provides access to the official Adgine platform user manual, hosted online.

## No authentication required

This skill needs no `GEO_API_KEY`. The manual is hosted at a public URL — the agent
simply outputs the link (and may fetch the URL when answering specific content questions).

## Manual location

**Online manual (PDF):** https://docs.adgine.ai/files/Adgine使用手册-v20260531.pdf

**Current version:** v20260531 (2025-05-31)

## Usage

### When the user asks to view or download the user manual (查看手册 / 下载手册 / 我要手册)

**必须输出 PDF 的 Markdown 链接，让用户看到可点击的下载/预览按钮：**

> ⚠️ **CRITICAL — 必须输出可点击的链接：**
> 当用户说 "查看使用手册", "下载手册", "给我手册", "我要用户手册", "view manual", "download manual", "打开手册" 时：
> 1. **必须** 输出 Markdown 格式的链接，让用户可以直接点击下载或预览
> 2. **禁止** 仅输出纯文本 URL 让用户复制粘贴
>
> 正确做法 — 输出指向在线手册的 Markdown 链接：
> ```markdown
> [📄 Adgine使用手册-v20260531.pdf](https://docs.adgine.ai/files/Adgine使用手册-v20260531.pdf)
> ```

### When the user asks a specific question about how to use Adgine

1. **Fetch** the online manual at `https://docs.adgine.ai/files/Adgine使用手册-v20260531.pdf` to find relevant content.
2. **Answer** the user's question based on the manual content.
3. **Reference** the PDF link so the user can view the full formatted manual.

## Output Format

### For view/download requests

**直接输出以下内容（Markdown 链接 + 说明）：**

> 📄 **Adgine 使用手册 (v20260531)**
>
> [点击下载/预览 PDF](https://docs.adgine.ai/files/Adgine使用手册-v20260531.pdf)
>
> 这是 Adgine 平台的完整使用手册，包含所有功能的详细操作指南。

### For content questions

- Provide a clear, concise answer based on the manual content
- Quote relevant sections when helpful
- Mention that this comes from the official Adgine 使用手册 (v20260531)
- If the user wants more detail, suggest they review the full PDF manual at the link above
