#!/usr/bin/env python3
"""AI visibility sampling prompt generation and result scoring."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse


UNMENTIONED_RANK = 11
SUBAGENT_CONCURRENCY_LIMIT = 5

CATEGORY_RULES = [
    ("online brokerage", ["brokerage", "stocks", "etf", "reits", "options", "trading", "market access"]),
    ("payment infrastructure", ["payments", "checkout", "billing", "invoicing", "subscriptions"]),
    ("school or education provider", ["school", "course", "tuition", "student", "learning", "education"]),
    ("software platform", ["software", "platform", "api", "dashboard", "workflow", "automation"]),
    ("financial service", ["finance", "financial", "investment", "wealth", "banking"]),
]

REGION_KEYWORDS = [
    "Singapore",
    "Hong Kong",
    "United States",
    "United Kingdom",
    "China",
    "Australia",
    "Europe",
    "Global",
]

PRODUCT_TERM_STOPWORDS = {
    "about", "account", "accounts", "all", "and", "an", "app", "apps", "are", "as",
    "at", "article", "articles", "blog", "blogs", "brand", "business", "businesses",
    "by", "case", "category", "center", "commi", "commission", "company", "contact", "content", "customer",
    "customers", "data", "description", "docs", "documentation", "english",
    "cms101211", "discover", "enterprise", "faq", "features", "fee", "fees", "financial", "for", "form", "from",
    "global", "globally", "guide", "guides", "headquartered", "help", "hits", "holding", "home", "homepage",
    "h1", "http", "https", "index", "info", "infrastructure", "insights", "into", "intro", "is", "its",
    "learn", "learning", "licenses", "lifetime", "links", "login", "longbridgeai", "low", "main",
    "market", "markets", "mas-regulated", "meta", "multi-jurisdictional", "myinfo", "news", "next-generation", "n-px", "of", "offer", "offers", "on", "online", "open", "or", "our", "overview",
    "explained", "page", "pages", "platform", "pricing", "privacy", "product", "products", "proxy",
    "regulatory", "resources", "results", "same", "sec", "service", "services", "site", "solution",
    "solutions", "story", "student", "students", "support", "team", "terms", "that", "the", "this",
    "first", "llms.txt", "title", "to", "today", "tool", "tools", "total", "use", "user", "users", "usd", "via", "vote",
    "website", "with", "www", "your", "我们", "产品", "服务", "平台", "官网",
    "首页", "帮助", "关于",
}

URL_SEGMENT_STOPWORDS = PRODUCT_TERM_STOPWORDS | {
    "api", "assets", "auth", "cdn", "css", "developer", "developers", "download",
    "en", "es", "fr", "html", "images", "img", "js", "login", "media", "page",
    "post", "sg", "sitemap", "static", "zh",
}


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip()
        key = normalized.lower()
        if normalized and key not in seen:
            result.append(normalized)
            seen.add(key)
    return result


def _elapsed_since(started: float) -> float:
    return round(time.perf_counter() - started, 3)


def _domain_root(domain: str) -> str:
    parts = [p for p in domain.lower().split(".") if p]
    if len(parts) >= 2 and parts[-2] not in {"com", "co", "org", "net"}:
        return parts[-2]
    return parts[0] if parts else domain


def _normalize_domain(value: str) -> str:
    domain = (value or "").strip().lower()
    if "://" in domain:
        domain = urlparse(domain).netloc
    domain = domain.split("@")[-1].split(":")[0]
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def _clean_brand_name(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    if not value:
        return ""
    value = re.split(r"\s+[|—–-]\s+|:", value, maxsplit=1)[0].strip()
    value = re.sub(r"\$0.*$", "", value).strip()
    return value


def _first_nonempty(values: list[Any]) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _infer_category(text: str) -> str:
    lower = text.lower()
    best_category = "website or digital service"
    best_hits = 0
    for category, keywords in CATEGORY_RULES:
        hits = sum(1 for keyword in keywords if keyword in lower)
        if hits > best_hits:
            best_category = category
            best_hits = hits
    return best_category


def _infer_regions(text: str) -> list[str]:
    lower = text.lower()
    regions = [region for region in REGION_KEYWORDS if region.lower() in lower]
    return _dedupe(regions) or ["target market"]


def _display_term(term: str, original_forms: dict[str, str]) -> str:
    original = original_forms.get(term, term)
    if original.isupper() and 2 <= len(original) <= 8:
        return original
    return term


def _is_candidate_term(term: str, excluded_terms: set[str], stopwords: set[str]) -> bool:
    normalized = term.strip().lower()
    if (
        not normalized
        or normalized in stopwords
        or normalized in excluded_terms
        or len(normalized) < 3
        or normalized.isdigit()
    ):
        return False
    return bool(re.search(r"[a-zA-Z\u4e00-\u9fff]", normalized))


def _term_words(text: str) -> list[tuple[str, str]]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+.-]*|[\u4e00-\u9fff]{2,}", text)
    return [(word.lower().strip(".-+"), word.strip(".-+")) for word in words if word.strip(".-+")]


def _add_term(
    scores: dict[str, int],
    original_forms: dict[str, str],
    term: str,
    score: int,
    excluded_terms: set[str],
    stopwords: set[str],
    display_term: Optional[str] = None,
) -> None:
    normalized = re.sub(r"\s+", " ", term.strip().lower())
    if not _is_candidate_term(normalized, excluded_terms, stopwords):
        return
    scores[normalized] = scores.get(normalized, 0) + score
    original_forms.setdefault(normalized, (display_term or term).strip())


def _rank_product_terms(scores: dict[str, int], original_forms: dict[str, str]) -> list[str]:
    ranked = sorted(scores.items(), key=lambda item: (item[0].count(" "), -item[1], len(item[0]), item[0]))
    selected: list[str] = []
    for term, _score in ranked:
        if any(term in existing.lower() or existing.lower() in term for existing in selected):
            continue
        selected.append(_display_term(term, original_forms))
        if len(selected) >= 8:
            break
    return selected


def _infer_product_terms(
    text: str,
    source_urls: Optional[list[str]] = None,
    excluded_terms: Optional[list[str]] = None,
) -> list[str]:
    excluded = {
        value.lower()
        for value in (excluded_terms or [])
        if value and len(value.lower()) >= 2
    }
    for value in list(excluded):
        excluded.update(part for part in re.split(r"[\s.-]+", value) if len(part) >= 3)
    scores: dict[str, int] = {}
    original_forms: dict[str, str] = {}

    for normalized, original in _term_words(text):
        score = 5 if original.isupper() and 2 <= len(original) <= 8 else 2
        _add_term(scores, original_forms, normalized, score, excluded, PRODUCT_TERM_STOPWORDS, original)

    clean_words = [
        (normalized, original)
        for normalized, original in _term_words(text)
        if _is_candidate_term(normalized, excluded, PRODUCT_TERM_STOPWORDS)
    ]
    for index in range(len(clean_words) - 1):
        first, first_original = clean_words[index]
        second, second_original = clean_words[index + 1]
        phrase = f"{first} {second}"
        original_phrase = f"{first_original} {second_original}"
        _add_term(scores, original_forms, phrase, 3, excluded, PRODUCT_TERM_STOPWORDS, original_phrase)

    if len(_rank_product_terms(scores, original_forms)) < 3:
        for url in source_urls or []:
            path = urlparse(str(url)).path
            for segment in re.split(r"[/?#]", path):
                segment = segment.strip("-_ ")
                if not segment:
                    continue
                parts = [part for part in re.split(r"[-_]+", segment) if part]
                normalized_parts = [part.lower() for part in parts]
                meaningful_parts = [
                    part for part in normalized_parts
                    if _is_candidate_term(part, excluded, URL_SEGMENT_STOPWORDS)
                ]
                for part in meaningful_parts:
                    _add_term(scores, original_forms, part, 4, excluded, URL_SEGMENT_STOPWORDS)
                if 2 <= len(meaningful_parts) <= 4:
                    phrase = " ".join(meaningful_parts)
                    _add_term(scores, original_forms, phrase, 8, excluded, URL_SEGMENT_STOPWORDS)

    return _rank_product_terms(scores, original_forms)


def _source_urls(audit_data: dict[str, Any]) -> list[str]:
    meta = audit_data.get("meta", {})
    signals = audit_data.get("signals", {})
    sitemap = signals.get("d1_sitemap", {})
    third_party = signals.get("d3_third_party", {})
    urls = [meta.get("url", "")]
    urls.extend(sitemap.get("sampled_page_urls", [])[:6])
    urls.extend(third_party.get("same_as_links", [])[:6])
    return _dedupe([str(url) for url in urls if url])


def build_brand_profile(audit_data: dict[str, Any]) -> dict[str, Any]:
    meta = audit_data.get("meta", {})
    signals = audit_data.get("signals", {})
    snippets = audit_data.get("snippets", {})
    domain = _normalize_domain(str(meta.get("domain") or urlparse(str(meta.get("url", ""))).netloc))

    brand_name_signals = signals.get("d3_brand_name", {})
    third_party = signals.get("d3_third_party", {})
    knowledge_graph = signals.get("d3_knowledge_graph", {})
    brand_candidates = [
        brand_name_signals.get("schema_org_name"),
        brand_name_signals.get("llms_title"),
        brand_name_signals.get("title_brand"),
        meta.get("brand_query"),
        _domain_root(domain),
    ]
    brand_name = _clean_brand_name(_first_nonempty(brand_candidates)) or _domain_root(domain).title()

    description = _first_nonempty([
        snippets.get("d3_brand_description_content"),
        snippets.get("d4_definition_content"),
        snippets.get("d1_llms_txt_content"),
        meta.get("brand_query"),
    ])
    product_text = " ".join([
        description,
        snippets.get("d1_llms_txt_content", ""),
        snippets.get("d2_depth_sample", ""),
        snippets.get("d4_definition_content", ""),
    ])
    combined = " ".join([
        product_text,
        json.dumps(third_party, ensure_ascii=False),
        json.dumps(knowledge_graph, ensure_ascii=False),
    ])
    source_urls = _source_urls(audit_data)
    sitemap = signals.get("d1_sitemap", {})
    site_urls = _dedupe([str(meta.get("url", ""))] + [str(url) for url in sitemap.get("sampled_page_urls", [])[:10]])
    domain_root = _domain_root(domain)
    regions = _infer_regions(combined)
    brand_variants = _dedupe([brand_name, domain_root, brand_name.replace(" ", "")])
    category = _infer_category(combined)
    excluded_terms = brand_variants + regions + [domain, category]

    return {
        "brand_name": brand_name,
        "brand_variants": brand_variants,
        "domain": domain,
        "category": category,
        "regions": regions,
        "product_terms": _infer_product_terms(product_text, site_urls, excluded_terms),
        "description": description[:800],
        "source_urls": source_urls,
        "third_party_sources": {
            "platforms_found": third_party.get("platforms_found", []),
            "same_as_links": third_party.get("same_as_links", []),
            "knowledge_graph": knowledge_graph,
        },
    }


def generate_visibility_prompts(brand_profile: dict[str, Any]) -> list[dict[str, Any]]:
    brand = brand_profile["brand_name"]
    category = brand_profile.get("category") or "website or digital service"
    region = (brand_profile.get("regions") or ["target market"])[0]
    product_terms = brand_profile.get("product_terms") or ["service"]
    product_phrase = ", ".join(product_terms[:3])

    prompt_specs = [
        ("brand_identification", f"{brand} 是什么？请简要说明它的主要产品、服务对象和适用地区。", True),
        ("brand_identification", f"What does {brand} do, and what kind of customer should consider it?", True),
        ("category_discovery", f"在 {region} 选择 {category} 时，有哪些品牌或平台值得考虑？请按推荐顺序列出。", False),
        ("category_discovery", f"Compare leading {category} options for users in {region}. Which brands would you shortlist?", False),
        ("problem_solution", f"我想解决和 {product_phrase} 相关的问题，应该考虑哪些方案或平台？", False),
        ("problem_solution", f"What tools or providers can help with {product_phrase} for users in {region}?", False),
        ("competitor_alternative", f"What are the main alternatives or competitors to {brand}?", True),
        ("competitor_alternative", f"如果不使用 {brand}，还有哪些类似服务可以选择？请说明差异。", True),
        ("source_reference", f"Where can I find reliable official information about {brand}? Include source URLs if you know them.", True),
        ("source_reference", f"请列出了解 {category} 的可信来源，并说明是否有官方站点可参考。", False),
    ]

    return [
        {
            "id": f"visibility-{index:02d}",
            "type": prompt_type,
            "prompt": prompt,
            "mentions_brand_in_prompt": mentions_brand,
        }
        for index, (prompt_type, prompt, mentions_brand) in enumerate(prompt_specs, start=1)
    ]


def build_subagent_task(prompt_item: dict[str, Any]) -> str:
    return f"""Answer the prompt below using only your own model knowledge.

Do not use hidden parent-agent context, local files, prior audit JSON, or any supplied brand profile. Return a concise answer and then the structured block exactly as requested.

Prompt:
{prompt_item["prompt"]}

Return format:
prompt: <repeat the prompt>
answer: <your answer>
mentioned_brand: true|false
brand_position: <number|null>
mentioned_urls: [<url>, ...]
competitors_mentioned: [<name>, ...]
"""


def batch_subagent_tasks(
    prompts: list[dict[str, Any]],
    max_concurrency: int = SUBAGENT_CONCURRENCY_LIMIT,
) -> list[list[str]]:
    if max_concurrency < 1:
        raise ValueError("max_concurrency must be at least 1")
    prompt_ids = [prompt["id"] for prompt in prompts]
    return [
        prompt_ids[index:index + max_concurrency]
        for index in range(0, len(prompt_ids), max_concurrency)
    ]


def visibility_reference_metadata(public_geo_score: Optional[float] = None) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "agent_visibility_included": False,
        "score_formula": "visibility_reference_only",
    }
    if public_geo_score is not None:
        metadata["geo_score_reference"] = round(float(public_geo_score), 1)
    return metadata


def _answer_by_prompt_id(answers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for answer in answers:
        prompt_id = answer.get("prompt_id") or answer.get("id")
        if prompt_id:
            result[str(prompt_id)] = answer
    return result


def _contains_any(text: str, values: list[str]) -> bool:
    lower = text.lower()
    return any(value and value.lower() in lower for value in values)


def _as_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0", "null", "none", ""}:
            return False
    return None


def _mentioned_brand(answer: dict[str, Any], text: str, brand_profile: dict[str, Any]) -> bool:
    # Parent scoring is the source of truth. Sub-agent self labels are useful
    # hints, but they can be wrong and must not override answer-text evidence.
    return _contains_any(text, brand_profile.get("brand_variants", []))


def _brand_position(answer: dict[str, Any], mentioned: bool) -> int:
    raw = answer.get("brand_position")
    if isinstance(raw, int) and raw > 0:
        return min(raw, UNMENTIONED_RANK)
    if isinstance(raw, str) and raw.isdigit():
        return min(int(raw), UNMENTIONED_RANK)
    return UNMENTIONED_RANK if not mentioned else 5


def _mentioned_urls(answer: dict[str, Any], text: str) -> list[str]:
    urls = answer.get("mentioned_urls")
    if isinstance(urls, list):
        return [str(url) for url in urls]
    return re.findall(r"https?://[^\s)\]]+", text)


def _correct_entity(answer: dict[str, Any], text: str, brand_profile: dict[str, Any], mentioned: bool) -> bool:
    if "correct_entity" in answer:
        return bool(_as_bool(answer["correct_entity"]))
    if not mentioned:
        return False
    expected_terms = [brand_profile.get("category", "")]
    expected_terms.extend(brand_profile.get("regions", []))
    expected_terms.extend(brand_profile.get("product_terms", []))
    return _contains_any(text, [term for term in expected_terms if term])


def _hallucinated(answer: dict[str, Any], mentioned: bool) -> bool:
    if not mentioned:
        return False
    if "hallucinated" in answer:
        return bool(_as_bool(answer["hallucinated"]))
    if "hallucination" in answer:
        return bool(_as_bool(answer["hallucination"]))
    incorrect_claims = answer.get("incorrect_claims")
    return bool(incorrect_claims)


def score_visibility_results(
    brand_profile: dict[str, Any],
    prompts: list[dict[str, Any]],
    answers: list[dict[str, Any]],
    public_geo_score: Optional[float] = None,
) -> dict[str, Any]:
    answers_by_id = _answer_by_prompt_id(answers)
    rows: list[dict[str, Any]] = []

    for prompt in prompts:
        answer = answers_by_id.get(prompt["id"], {})
        answer_text = str(answer.get("answer") or answer.get("text") or "")
        urls = _mentioned_urls(answer, answer_text)
        evidence_text = " ".join([
            answer_text,
            " ".join(urls),
            json.dumps(answer.get("competitors_mentioned", []), ensure_ascii=False),
        ])
        mentioned = _mentioned_brand(answer, evidence_text, brand_profile)
        position = _brand_position(answer, mentioned)
        source_visible = _contains_any(" ".join(urls + [answer_text]), [brand_profile.get("domain", "")])
        correct_entity = _correct_entity(answer, evidence_text, brand_profile, mentioned)
        hallucinated = _hallucinated(answer, mentioned)

        rows.append({
            "prompt_id": prompt["id"],
            "type": prompt["type"],
            "prompt": prompt["prompt"],
            "mentioned_brand": mentioned,
            "brand_position": position if mentioned else None,
            "source_visible": source_visible,
            "correct_entity": correct_entity,
            "hallucinated": hallucinated,
            "mentioned_urls": urls,
            "competitors_mentioned": answer.get("competitors_mentioned", []),
        })

    total = len(rows) or 1
    mentioned_rows = [row for row in rows if row["mentioned_brand"]]
    mention_count = len(mentioned_rows)
    category_rows = [row for row in rows if row["type"] == "category_discovery"]
    source_rows = [row for row in rows if row["type"] == "source_reference"]
    rank_values = [
        row["brand_position"] if row["brand_position"] is not None else UNMENTIONED_RANK
        for row in rows
    ]
    average_rank = sum(rank_values) / total
    rank_score = max(0.0, 1.0 - ((average_rank - 1) / (UNMENTIONED_RANK - 1)))

    mention_rate = mention_count / total
    correct_entity_rate = (
        sum(1 for row in mentioned_rows if row["correct_entity"]) / mention_count
        if mention_count else 0.0
    )
    category_visibility_rate = (
        sum(1 for row in category_rows if row["mentioned_brand"]) / len(category_rows)
        if category_rows else 0.0
    )
    source_visibility_rate = (
        sum(1 for row in source_rows if row["source_visible"]) / len(source_rows)
        if source_rows else 0.0
    )
    hallucination_rate = (
        sum(1 for row in mentioned_rows if row["hallucinated"]) / mention_count
        if mention_count else 0.0
    )
    visibility_score = round(100 * (
        0.30 * mention_rate
        + 0.20 * correct_entity_rate
        + 0.20 * category_visibility_rate
        + 0.15 * source_visibility_rate
        + 0.10 * rank_score
        + 0.05 * (1 - hallucination_rate)
    ), 1)

    metrics = {
        "mention_rate": round(mention_rate, 4),
        "correct_entity_rate": round(correct_entity_rate, 4),
        "category_visibility_rate": round(category_visibility_rate, 4),
        "source_visibility_rate": round(source_visibility_rate, 4),
        "average_rank": round(average_rank, 2),
        "hallucination_rate": round(hallucination_rate, 4),
        "visibility_score": visibility_score,
    }
    metrics.update(visibility_reference_metadata(public_geo_score))

    return {
        "brand_profile": brand_profile,
        "metrics": metrics,
        "rows": rows,
    }


def _md_cell(value: Any, max_len: int = 240) -> str:
    text = str(value or "").replace("\n", " ").replace("|", "\\|").strip()
    if len(text) > max_len:
        return text[: max_len - 1].rstrip() + "…"
    return text


def _visibility_recommendations(metrics: dict[str, Any]) -> list[str]:
    recommendations: list[str] = []
    if metrics["category_visibility_rate"] < 0.5:
        recommendations.append("补充围绕品类、场景、对比和选择标准的页面，让不含品牌名的问题也能命中品牌实体。")
    if metrics["source_visibility_rate"] < 0.7:
        recommendations.append("强化官网来源可引用入口，例如 llms.txt、About、FAQ、Docs、对比页和结构化数据中的官方 URL。")
    if metrics["correct_entity_rate"] < 0.8:
        recommendations.append("统一品牌主体说明、地区、产品线和目标用户表述，降低 AI 把品牌归错类或描述不完整的概率。")
    if metrics["hallucination_rate"] > 0.1:
        recommendations.append("在官网与第三方资料中补齐可核验事实，优先修正易被误述的业务范围、地区、价格和资质信息。")
    if not recommendations:
        recommendations.append("保持当前实体资料、可引用页面和第三方资料一致性，并持续用隔离 prompt 做回归采样。")
    return recommendations


def format_visibility_report(results: dict[str, Any]) -> str:
    metrics = results["metrics"]
    rows = results["rows"]
    mentioned_count = sum(1 for row in rows if row["mentioned_brand"])
    category_rows = [row for row in rows if row["type"] == "category_discovery"]
    source_rows = [row for row in rows if row["type"] == "source_reference"]
    lines = [
        "## AI 可见性采样参考",
        "",
        "> 本章节基于当前运行模型采样，仅用于粗略观察品牌在 AI 回答中的可见性；该采样不参与 GEO 总分。如需更精确、持续的 AI 可见性数据，可注册 [adgine.ai](https://adgine.ai/) 进行持续监测。",
        "",
        "| 指标 | 结果 |",
        "|------|------|",
        f"| AI 可见性采样分 | {metrics['visibility_score']}/100 |",
        f"| 品牌命中率 | {metrics['mention_rate'] * 100:.1f}% |",
        f"| 实体描述正确率 | {metrics['correct_entity_rate'] * 100:.1f}% |",
        f"| 品类主动可见率 | {metrics['category_visibility_rate'] * 100:.1f}% |",
        f"| 来源可见率 | {metrics['source_visibility_rate'] * 100:.1f}% |",
        f"| 平均排名 | {metrics['average_rank']} |",
        f"| 事实错误率 | {metrics['hallucination_rate'] * 100:.1f}% |",
    ]
    lines.extend([
        "",
        "### 统计摘要",
        "",
        f"- 共执行 {len(rows)} 个隔离 prompt，目标品牌出现在 {mentioned_count} 个回答中。",
        f"- 不含品牌名的品类发现 prompt 命中 {sum(1 for row in category_rows if row['mentioned_brand'])}/{len(category_rows) or 0}。",
        f"- 来源型 prompt 命中官网或站内 URL {sum(1 for row in source_rows if row['source_visible'])}/{len(source_rows) or 0}。",
        "",
        "### Prompt 明细",
        "",
        "| ID | 类型 | Prompt | 是否可见 | 排名 | 官网/站内来源 |",
        "|----|------|--------|------|---:|------|",
    ])
    for row in rows:
        lines.append(
            "| {prompt_id} | {type} | {prompt} | {mentioned} | {rank} | {source} |".format(
                prompt_id=row["prompt_id"],
                type=row["type"],
                prompt=_md_cell(row["prompt"]),
                mentioned="✅" if row["mentioned_brand"] else "❌",
                rank=row["brand_position"] if row["brand_position"] is not None else "—",
                source="✅" if row["source_visible"] else "❌",
            )
        )
    lines.extend([
        "",
        "### 改进建议",
        "",
    ])
    lines.extend(f"- {item}" for item in _visibility_recommendations(metrics))
    return "\n".join(lines) + "\n"


def _load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Optional[str], data: Any) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if path:
        Path(path).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare and score agent-simulated GEO visibility tests.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Build brand profile and prompt set from audit JSON")
    prepare.add_argument("audit_json")
    prepare.add_argument("--output", "-o")

    score = subparsers.add_parser("score", help="Score sub-agent answers")
    score.add_argument("visibility_plan_json")
    score.add_argument("answers_json")
    score.add_argument("--output", "-o")
    score.add_argument("--report", help="Optional Markdown report output path")
    score.add_argument("--public-geo-score", type=float, help="Optional GEO score reference; visibility sampling does not change it")

    args = parser.parse_args(argv)
    command_started = time.perf_counter()
    timings: dict[str, float] = {}

    if args.command == "prepare":
        stage_started = time.perf_counter()
        audit_data = _load_json(args.audit_json)
        timings["audit_json_read_seconds"] = _elapsed_since(stage_started)
        stage_started = time.perf_counter()
        brand_profile = build_brand_profile(audit_data)
        timings["brand_profile_build_seconds"] = _elapsed_since(stage_started)
        stage_started = time.perf_counter()
        prompts = generate_visibility_prompts(brand_profile)
        timings["prompt_generation_seconds"] = _elapsed_since(stage_started)
        stage_started = time.perf_counter()
        subagent_batches = batch_subagent_tasks(prompts)
        subagent_tasks = {
            prompt["id"]: build_subagent_task(prompt)
            for prompt in prompts
        }
        timings["subagent_task_build_seconds"] = _elapsed_since(stage_started)
        timings["total_visibility_prepare_seconds"] = _elapsed_since(command_started)
        plan = {
            "brand_profile": brand_profile,
            "prompts": prompts,
            "subagent_concurrency_limit": SUBAGENT_CONCURRENCY_LIMIT,
            "subagent_batches": subagent_batches,
            "subagent_tasks": subagent_tasks,
            "timings": timings,
        }
        _write_json(args.output, plan)
        return 0

    if args.command == "score":
        stage_started = time.perf_counter()
        plan = _load_json(args.visibility_plan_json)
        timings["visibility_plan_read_seconds"] = _elapsed_since(stage_started)
        stage_started = time.perf_counter()
        raw_answers = _load_json(args.answers_json)
        timings["answers_read_seconds"] = _elapsed_since(stage_started)
        answers = raw_answers.get("answers", raw_answers) if isinstance(raw_answers, dict) else raw_answers
        stage_started = time.perf_counter()
        results = score_visibility_results(
            plan["brand_profile"],
            plan["prompts"],
            answers,
            public_geo_score=args.public_geo_score,
        )
        timings["visibility_score_calculation_seconds"] = _elapsed_since(stage_started)
        report_text = ""
        if args.report:
            stage_started = time.perf_counter()
            report_text = format_visibility_report(results)
            timings["visibility_report_render_seconds"] = _elapsed_since(stage_started)
        timings["total_visibility_score_seconds"] = _elapsed_since(command_started)
        results["timings"] = timings
        _write_json(args.output, results)
        if args.report:
            Path(args.report).write_text(report_text, encoding="utf-8")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
