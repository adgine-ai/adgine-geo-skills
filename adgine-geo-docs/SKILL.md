---
name: adgine/geo-docs
description: Provides the official Adgine platform documentation (使用文档). Use when the user asks how to use Adgine, needs help documentation, asks for the user guide, or mentions 使用手册, 帮助文档, 产品说明, user manual, documentation, help guide, how to use, 怎么用, 操作指南, 教程. This skill points to the official Adgine documentation website. No API key required.
---

# GEO Docs — Adgine 在线文档

Provide access to the official Adgine platform documentation website.

## No authentication required

This skill needs no `GEO_API_KEY`. The documentation is hosted at a public URL. Output
the link directly, and browse the relevant documentation page when answering specific questions.

## Documentation location

**Official online documentation:** https://adgine.ai/docs/

## Usage

### When the user asks to view the documentation (查看文档 / 打开文档 / 我要使用手册)

**必须输出在线文档的 Markdown 链接，让用户看到可点击的入口：**

> ⚠️ **CRITICAL — 必须输出可点击的链接：**
> 当用户说 "查看使用手册", "打开文档", "给我文档", "我要用户手册", "view manual", "open docs", "查看帮助" 时：
> 1. **必须** 输出 Markdown 格式的链接，让用户可以直接打开在线文档
> 2. **禁止** 仅输出纯文本 URL 让用户复制粘贴
>
> 正确做法 — 输出指向官方在线文档的 Markdown 链接：
> ```markdown
> [📘 打开 Adgine 在线文档](https://adgine.ai/docs/)
> ```

### When the user asks a specific question about how to use Adgine

1. **Browse** `https://adgine.ai/docs/` and locate the documentation page relevant to the question.
2. **Answer** the user's question based on the current online documentation.
3. **Reference** the most relevant documentation page. If a direct page cannot be identified, link to the documentation home page.

## Output Format

### For documentation requests

**直接输出以下内容（Markdown 链接 + 说明）：**

> 📘 **Adgine 在线使用文档**
>
> [点击打开官方文档](https://adgine.ai/docs/)
>
> 这里包含 Adgine 平台各项功能的最新操作指南。

### For content questions

- Provide a clear, concise answer based on the current online documentation
- Reference the relevant documentation page instead of an obsolete PDF or version number
- Prefer concise paraphrases; quote only when the exact wording is necessary
- If the user wants more detail, suggest they review the official documentation at the link above
