#!/usr/bin/env python3
"""Score GEO audit assessments using the compressed v3 evaluation table.

The collector gathers evidence. The auditor or agent assigns item statuses and
evidence notes. This module performs deterministic score math against the
30-item "five dimension compressed strict v3" table.

Formula:
    dimension_score = floor(sum(item_points * status_coefficient) / effective_points * 100)
    final_score = floor(sum(capped_dimension_score * dimension_weight))

Statuses:
    PASS = 1.0, WARN = item-specific coefficient, FAIL = 0.0,
    ERROR/N/A are excluded from the effective denominator.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SCORE_TABLE_VERSION = "five-dimension-compressed-strict-v3"
EXPECTED_ITEM_COUNT = 30

STATUS_BADGES: dict[str, str] = {
    "PASS": "✅ PASS",
    "WARN": "⚠️ WARN",
    "FAIL": "❌ FAIL",
    "ERROR": "🔴 ERROR",
    "N/A": "➖ N/A",
}

STATUS_COEFFICIENTS: dict[str, float | None] = {
    "PASS": 1.0,
    "FAIL": 0.0,
    "ERROR": None,
    "N/A": None,
}


@dataclass(frozen=True)
class ScoreItem:
    id: str
    name: str
    points: int
    warn_coefficient: float
    score_rule: str
    focus: str
    detail: str


@dataclass(frozen=True)
class ScoreDimension:
    id: str
    label: str
    short_label: str
    weight: float
    items: tuple[ScoreItem, ...]


def item(
    item_id: str,
    name: str,
    points: int,
    warn_percent: int,
    score_rule: str,
    focus: str,
    detail: str,
) -> ScoreItem:
    return ScoreItem(
        id=item_id,
        name=name,
        points=points,
        warn_coefficient=warn_percent / 100,
        score_rule=score_rule,
        focus=focus,
        detail=detail,
    )


DIMENSIONS: tuple[ScoreDimension, ...] = (
    ScoreDimension(
        "discoverability",
        "维度一：AI 可发现",
        "AI 可发现",
        0.25,
        (
            item("1.1", "入口规范与可达性", 19, 50, "通过=100%；待优化=50%；不通过=0。若首页不可达、跳转链异常、最终 URL 错误或返回非真实 HTML，通常不高于待优化。", "域名规范化与入口统一、首页可达性、状态码与最终 URL 正确性。", "检查是否优先使用 HTTPS，是否统一 www / 非 www、尾斜杠、参数与 fragment 等 URL 变体；同时确认首页可正常返回真实页面内容，各核心入口页面的 status code、redirect、final URL、content-type 均正常。"),
            item("1.2", "抓取入口文件健康", 19, 50, "通过=100%；待优化=50%；不通过=0。robots / sitemap / llms 任一关键入口缺失或异常时通常记待优化；多项异常或关键入口长期缺失记不通过。", "robots.txt、sitemap、llms.txt / llms-full.txt。", "检查 /robots.txt、/sitemap.xml、/sitemap_index.xml、/llms.txt、/llms-full.txt 是否存在、可访问、格式正确且引用关系正常，并确认这些入口文件没有错误配置或异常限制。"),
            item("1.3", "核心页面发现覆盖", 12, 50, "通过=100%；待优化=50%；不通过=0。高价值页面覆盖不足、发现链路断裂或 sitemap/nav 仅覆盖少量品牌页时，通常记待优化。", "核心页面收录入口覆盖、Crawl set 覆盖质量、站内发现链路。", "检查 sitemap、首页导航、页脚和正文内链中，是否覆盖 product、service、pricing、blog、docs、resources、about、contact、legal 等核心页面，并确认 crawler 能顺利发现高价值页面。"),
            item("1.4", "AI crawler 实际可访问性", 24, 20, "通过=100%；待优化=20%；不通过=0。若 AI crawler 被拦截、返回 challenge page、429/403、仅能拿到非正文模板或主内容不可抓取，通常直接记不通过；并触发跨维度与总分封顶。", "AI 爬虫 UA 可访问性、WAF / CDN / 安全验证拦截、渲染可抓取性。", "检查 Googlebot、Bingbot、GPTBot、ClaudeBot、PerplexityBot 等访问首页、robots、sitemap 及核心页面时，是否能拿到真实 HTML 与正文内容；确认不存在 403/429/challenge page、安全验证、纯前端渲染或 hydration 异常。"),
            item("1.5", "索引控制与可收录状态", 8, 20, "通过=100%；待优化=20%；不通过=0。核心页出现 noindex、canonical 冲突、x-robots-tag 异常或误去收录时，通常不高于待优化；严重时记不通过并触发封顶。", "Indexability 基础状态。", "检查 robots meta、x-robots-tag、noindex、nofollow、canonical 等索引控制信号是否正确，确保核心页面没有被误排除出抓取或索引，也不存在互相冲突的收录指令。"),
            item("1.6", "错误页与模板回退风险", 15, 20, "通过=100%；待优化=20%；不通过=0。存在软404、homepage fallback、错误模板 200 返回或 404 模板索引冲突时，通常不高于待优化；成片出现时记不通过并触发跨维度封顶。", "软 404 与错误页识别、Homepage fallback / 模板回退、404 模板索引冲突。", "检查是否存在返回 200 但实际为错误页、title/H1/canonical 回退到首页或频道页、真实 404/410 页面错误输出 index,follow 等情况，避免 crawler 抓到错误模板内容。"),
            item("1.7", "Sitemap 质量与污染", 3, 50, "通过=100%；待优化=50%；不通过=0。没有可用 sitemap 时直接记不通过；存在失效 URL、错误语言版本、组件页或批量污染时记待优化；污染严重时记不通过。", "Sitemap 污染与失效 URL。", "检查 sitemap 是否存在且可用，并检查其中是否混入失效 URL、测试页、组件页、错误页或不存在的语言版本，避免浪费抓取预算、误导 crawler，并降低 AI 对站点内容结构的判断准确性。"),
        ),
    ),
    ScoreDimension(
        "understandability",
        "维度二：AI 可理解",
        "AI 可理解",
        0.20,
        (
            item("2.1", "页面标题与结构语义", 21, 50, "通过=100%；待优化=50%；不通过=0。标题/H1/层级不清但仍能基本表达主题时记待优化；大面积缺失或严重错位记不通过。", "页面标题语义清晰度、Meta description 语义清晰度、H1 唯一性与相关性、H2-H6 层级结构。", "检查 title、meta description、H1 与 H2-H6 层级是否准确表达页面主题、对象和核心价值，是否具备清晰的结构化语义。"),
            item("2.2", "业务定位与价值主张清晰度", 12, 50, "通过=100%；待优化=50%；不通过=0。业务描述模糊、类型难识别、价值主张与页面对象错位时记待优化。", "业务描述与价值主张、业务类型识别。", "检查首页与核心页面是否明确说明品牌做什么、为谁服务、提供什么价值，以及站点是否能被清晰识别为 SaaS、本地商家、电商、Publisher、Agency 或 Web App 等业务类型。"),
            item("2.3", "站点架构与内容组织表达", 16, 50, "通过=100%；待优化=50%；不通过=0。栏目存在但组织弱、主题页只是自动归档、结构无法承担导览职能时记待优化。", "站点信息架构完整性、主题页与分类页表达、内容聚类结构可辨识性。", "检查导航、页脚和页面集合是否清楚呈现 product、service、pricing、blog、docs、resources 等结构，并确认 category、resource hub、docs hub 等页面是真正承担主题组织与导览作用。"),
            item("2.4", "正文可总结性与页面差异化", 10, 50, "通过=100%；待优化=50%；不通过=0。可读但摘要性弱、同类页差异不足时记待优化；大量模板化时可记不通过。", "页面主内容摘要能力、页面差异化表达。", "检查页面正文是否能形成清晰的 visible text summary；同时确认同类页面在标题、首段、H2 结构、内容骨架与主题重点上有足够差异。"),
            item("2.5", "多语言表达一致性", 7, 50, "通过=100%；待优化=50%；不通过=0。语言版本结构、hreflang 或 schema 轻中度不一致时记待优化；严重错配记不通过。", "多语言关系表达、多语言 Schema 一致性。", "检查 hreflang、语言版本路径、语言切换关系以及不同语言页面的 schema 输出是否一致，避免 AI 无法理解不同语言页面的对应关系。"),
            item("2.6", "Schema 覆盖与实现质量", 30, 40, "通过=100%；待优化=40%；不通过=0。Schema 部分缺失/不完整/与可见内容不一致时通常不高于待优化；关键类型缺失、明显错误或误标类型时记不通过。", "Schema 类型覆盖、Schema 与可见内容一致性、Schema 完整性与字段质量、BlogPosting / Article 选择合理性、富结果错误风险。", "检查站点是否为不同页面使用适配的 schema 类型，JSON-LD / microdata 字段是否完整且与页面可见内容一致，文章类页面是否正确选择 BlogPosting 或 Article，并避免误标类型。"),
            item("2.7", "图片与社交元数据可理解性", 4, 60, "通过=100%；待优化=60%；不通过=0。属于增强项，alt/OG/Twitter 信息不完整通常记待优化。", "图片与社交元数据可读性。", "检查图片 alt、Open Graph、Twitter/X card 等是否完整且语义清晰，帮助 AI 和平台更准确理解页面主题、核心内容和分享预览信息。"),
        ),
    ),
    ScoreDimension(
        "citability",
        "维度三：AI 可引用",
        "AI 可引用",
        0.20,
        (
            item("3.1", "可直接摘录与回答能力", 27, 40, "通过=100%；待优化=40%；不通过=0。若缺少直接可摘录表达、关键问题回答或 FAQ/总结结构，通常不高于待优化；几乎无法直接提炼答案时记不通过。", "直接可摘录表达、关键问题回答能力、FAQ 与总结内容。", "检查页面是否存在直接、明确、可独立引用的句子和段落，是否能用简洁内容回答用户核心问题，并具备 FAQ、总结、key takeaways、结论段等结构。"),
            item("3.2", "引用型内容形态覆盖", 22, 50, "通过=100%；待优化=50%；不通过=0。definition/comparison/guide/how-to/case 等类型不全时记待优化。", "定义型内容、比较型内容、内容资产类型覆盖。", "检查站点是否具备 definition、comparison、guide、how-to、glossary、benchmark、report、case study、docs 等适合 AI 在解释、比较、推荐和操作型回答中调用的内容形态。"),
            item("3.3", "证据与事实支撑强度", 28, 40, "通过=100%；待优化=40%；不通过=0。缺少数据、案例、方法论、作者/时间信号时通常不高于待优化；事实支撑极弱时记不通过。", "统计/数据/事实信息、案例与第一手经验、方法论与出处、作者与时间信号。", "检查页面是否提供可验证的数据、量化结论、案例、实操经验、benchmark、来源说明、methodology、作者信息以及发布时间/更新时间等信号。"),
            item("3.4", "正文信息密度与可用性", 7, 50, "通过=100%；待优化=50%；不通过=0。内容偏薄但仍有基本信息时记待优化；大面积 thin content 时记不通过。", "正文信息密度。", "检查正文内容的字数、信息量、段落质量与主题聚焦度，避免页面过薄、描述空泛、信息密度不足或虽有内容但难以摘录成有效答案。"),
            item("3.5", "模板化、重复与语言深度风险", 16, 50, "通过=100%；待优化=50%；不通过=0。存在模板化、重复或语言深度不对称但未严重影响引用判断时记待优化。", "薄弱/模板化内容风险、同主题页重复风险、多语言内容深度差异。", "检查是否存在 vague claims、模板改写、duplicate content、thin variant 或不同语言版本深度明显不对称等问题，避免 AI 在判断引用对象时出现混淆。"),
        ),
    ),
    ScoreDimension(
        "trustworthiness",
        "维度四：AI 可信任",
        "AI 可信任",
        0.20,
        (
            item("4.1", "品牌主体与联系可验证性", 25, 30, "通过=100%；待优化=30%；不通过=0。品牌实体不清、About/Contact 缺失或不可验证时通常不高于待优化；严重时触发 AI可信任更严封顶。", "品牌实体清晰度、About 页面完整性、Contact 与支持信息。", "检查品牌名称、产品名称、组织身份与业务定位是否清楚一致，About 页面是否完整介绍品牌背景、团队和业务，是否存在可验证联系方式、支持入口和客服方式。"),
            item("4.2", "作者、团队与资质信号", 24, 50, "通过=100%；待优化=50%；不通过=0。团队/作者/资质信号偏弱时记待优化。", "Team / Author / Credential 信号、作者性与出处可信度、监管/资质/牌照信号。", "检查是否展示团队成员、作者简介、专业资历、出处说明、责任边界，以及金融、教育、医疗等行业是否具备资质牌照、监管记录或官方登记等高可信信号。"),
            item("4.3", "合规与安全透明度", 17, 30, "通过=100%；待优化=30%；不通过=0。缺少 legal/policy/trust/security 关键页面时通常不高于待优化；严重时触发 AI可信任更严封顶。", "Legal / Policy / Compliance 页面、Trust 页面与安全信息。", "检查是否具备 privacy、terms、compliance、risk disclosure、security、trust center、responsible use、support 等页面，帮助 AI 判断品牌在合规、安全、责任边界与服务支持上是否透明。"),
            item("4.4", "社会证明与外部验证", 23, 50, "通过=100%；待优化=50%；不通过=0。第三方平台、案例、媒体提及不足时记待优化。", "案例与客户证明、第三方平台实体信号、外部评价与媒体提及。", "检查是否存在 measurable case study、客户证明、外部媒体报道、行业引用，以及 LinkedIn、GitHub、YouTube、Wikipedia/Wikidata、应用商店、目录站等第三方平台上的官方存在。"),
            item("4.5", "信任可见性风险", 11, 60, "通过=100%；待优化=60%；不通过=0。登录墙/付费墙或弱信任页存在但仍有部分可验证内容时记待优化。", "弱信任页面风险、内容需登录后才可见。", "检查 About、Team、Support、Policy 等信任页是否过薄、缺失或内容空泛，并确认高价值内容是否被登录墙或付费墙完全阻断且没有可抓取预览。"),
        ),
    ),
    ScoreDimension(
        "recommendability",
        "维度五：AI 可推荐",
        "AI 可推荐",
        0.15,
        (
            item("5.1", "平台适配与搜索意图覆盖", 18, 30, "通过=100%；待优化=30%；不通过=0。AI 平台适配内容和搜索意图覆盖明显不足时通常不高于待优化；并触发 AI可推荐更严封顶。", "AI 平台适配内容覆盖、Search intent 覆盖。", "检查站点是否具备适配 Google AI Overviews、ChatGPT、Perplexity、Gemini、Claude、Copilot 等平台的内容资产与页面类型，并确认内容覆盖定义、比较、决策、操作、问题解决等常见意图。"),
            item("5.2", "主题权威与内容集群建设", 17, 30, "通过=100%；待优化=30%；不通过=0。主题集群弱、hub 不成体系、核心主题缺少可持续内容集群时通常不高于待优化；并触发 AI可推荐更严封顶。", "Topical authority 建设、资源中心 / Hub 建设。", "检查站点是否围绕核心主题形成 guides、comparisons、glossary、reports、case studies、docs 等内容集群，以及是否存在真正承担聚合、筛选、导览作用的 resource hub / docs hub。"),
            item("5.3", "首页导流与站内继续访问路径", 15, 50, "通过=100%；待优化=50%；不通过=0。首页导流弱或被推荐页后续路径不清时记待优化。", "首页到高价值内容的导流、站内继续访问路径。", "检查首页与导航是否能把用户和 AI 明确导向高价值内容资产，并确认被推荐页面内部是否存在相关推荐、内链、导航和 CTA。"),
            item("5.4", "推荐支撑内容资产", 22, 50, "通过=100%；待优化=50%；不通过=0。compare/FAQ/how-to/case/report/docs 等资产不够完整时记待优化。", "比较与决策页能力、案例、报告、方法论资产、Docs / Help / 操作型内容。", "检查站点是否具备 compare pages、best-of 页、替代方案页、case study、benchmark、report、methodology、docs、FAQ、how-to、教程与帮助中心等资产。"),
            item("5.5", "转化承接页完备度", 15, 30, "通过=100%；待优化=30%；不通过=0。高价值转化页缺失、承接链路弱或推荐落点不足时通常不高于待优化；并触发 AI可推荐更严封顶。", "产品/服务转化页完备度、应用下载与行动入口。", "检查是否具备 pricing、product、service、feature、integration、signup、demo、trial、下载入口、App Store / Google Play 等页面，确保 AI 推荐后用户能顺利进入下一步。"),
            item("5.6", "外部推荐辅助信号与阻碍因素", 13, 50, "通过=100%；待优化=50%；不通过=0。外部平台存在不足或阻碍因素明显时记待优化；若平台侧核心阻碍很强，可记不通过。", "外部平台推荐辅助信号、推荐意愿削弱因素。", "检查 YouTube、Reddit、LinkedIn、GitHub、Product Hunt、review sites、目录站等外部平台是否能为推荐提供辅助信号，同时识别首页与内容资产断裂、问题解决型页面不足、平台存在感弱、模板内容过重等问题。"),
        ),
    ),
)


def _floor_score(value: float) -> int:
    return int(math.floor(value + 1e-9))


def _elapsed_since(started: float) -> float:
    return round(time.perf_counter() - started, 3)


def normalize_status(value: str | None) -> str:
    if value is None:
        return "ERROR"
    normalized = str(value).strip().upper()
    aliases = {
        "NA": "N/A",
        "NOT_APPLICABLE": "N/A",
        "NOT APPLICABLE": "N/A",
        "不适用": "N/A",
        "PARTIAL": "WARN",
        "NEEDS_OPTIMIZATION": "WARN",
        "NEEDS OPTIMIZATION": "WARN",
        "待优化": "WARN",
        "通过": "PASS",
        "不通过": "FAIL",
        "失败": "FAIL",
        "检测失败": "ERROR",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized in {"PASS", "WARN", "FAIL", "ERROR", "N/A"}:
        return normalized
    return "ERROR"


def status_coefficient(status: str, score_item: ScoreItem) -> float | None:
    if status == "WARN":
        return score_item.warn_coefficient
    return STATUS_COEFFICIENTS.get(status)


def iter_items() -> Iterable[ScoreItem]:
    for dimension in DIMENSIONS:
        yield from dimension.items


def item_map() -> dict[str, ScoreItem]:
    return {score_item.id: score_item for score_item in iter_items()}


def validate_config() -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    for dimension in DIMENSIONS:
        total = sum(score_item.points for score_item in dimension.items)
        if total != 100:
            errors.append(f"{dimension.label} 检测项分值合计为 {total}，应为 100")
        for score_item in dimension.items:
            if score_item.id in ids:
                errors.append(f"重复检测项 ID: {score_item.id}")
            if not 0 <= score_item.warn_coefficient <= 1:
                errors.append(f"{score_item.id} 待优化系数非法: {score_item.warn_coefficient}")
            ids.add(score_item.id)
    weight_total = sum(dimension.weight for dimension in DIMENSIONS)
    if abs(weight_total - 1.0) > 0.0001:
        errors.append(f"大项权重合计为 {weight_total}，应为 1.0")
    if len(ids) != EXPECTED_ITEM_COUNT:
        errors.append(f"检测项数量为 {len(ids)}，应为 {EXPECTED_ITEM_COUNT}")
    return errors


def _coerce_assessments(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = payload.get("items") or payload.get("assessments") or payload
    if isinstance(raw, list):
        result: dict[str, dict[str, Any]] = {}
        for entry in raw:
            if isinstance(entry, dict) and entry.get("id"):
                result[str(entry["id"])] = entry
        return result
    if isinstance(raw, dict):
        result = {}
        for key, value in raw.items():
            if isinstance(value, str):
                result[str(key)] = {"status": value}
            elif isinstance(value, dict):
                result[str(key)] = value
        return result
    return {}


def _cap_payload(scope: str, dimension_id: str | None, cap: int, failed: list[str], reason: str) -> dict[str, Any]:
    return {
        "scope": scope,
        "dimension_id": dimension_id,
        "cap": cap,
        "failed_item_ids": failed,
        "reason": reason,
    }


def _apply_cap_if_needed(score: int, cap: int, payload: dict[str, Any], caps: list[dict[str, Any]]) -> int:
    if score > cap:
        caps.append(payload)
        return cap
    return score


def _apply_dimension_caps(dimension_id: str, statuses: dict[str, str], score: int) -> tuple[int, list[dict[str, Any]]]:
    caps: list[dict[str, Any]] = []

    if dimension_id == "discoverability":
        failed = [item_id for item_id in ("1.4", "1.5", "1.6") if statuses.get(item_id) == "FAIL"]
        if len(failed) >= 2:
            score = _apply_cap_if_needed(score, 35, _cap_payload("dimension", dimension_id, 35, failed, "AI crawler、索引控制或错误页模板回退中两项及以上不通过，AI 可发现最高 35 分。"), caps)
        elif failed:
            score = _apply_cap_if_needed(score, 55, _cap_payload("dimension", dimension_id, 55, failed, "AI crawler、索引控制或错误页模板回退中任一项不通过，AI 可发现最高 55 分。"), caps)

    if dimension_id == "citability":
        failed_core = [item_id for item_id in ("3.1", "3.3") if statuses.get(item_id) == "FAIL"]
        failed_density = statuses.get("3.4") == "FAIL"
        if len(failed_core) == 2 and failed_density:
            score = _apply_cap_if_needed(score, 35, _cap_payload("dimension", dimension_id, 35, [*failed_core, "3.4"], "可摘录/回答能力与证据支撑均不通过，并叠加正文信息密度不通过，AI 可引用最高 35 分。"), caps)
        elif len(failed_core) == 2:
            score = _apply_cap_if_needed(score, 45, _cap_payload("dimension", dimension_id, 45, failed_core, "可摘录/回答能力与证据支撑同时不通过，AI 可引用最高 45 分。"), caps)
        elif failed_core:
            score = _apply_cap_if_needed(score, 65, _cap_payload("dimension", dimension_id, 65, failed_core, "可摘录/回答能力或证据支撑任一项不通过，AI 可引用最高 65 分。"), caps)

    if dimension_id == "trustworthiness":
        failed = [item_id for item_id in ("4.1", "4.3") if statuses.get(item_id) == "FAIL"]
        if len(failed) >= 2:
            score = _apply_cap_if_needed(score, 35, _cap_payload("dimension", dimension_id, 35, failed, "品牌主体可验证性与合规安全透明度同时不通过，AI 可信任最高 35 分。"), caps)
        elif failed:
            score = _apply_cap_if_needed(score, 55, _cap_payload("dimension", dimension_id, 55, failed, "品牌主体可验证性或合规安全透明度不通过，AI 可信任最高 55 分。"), caps)

    if dimension_id == "recommendability":
        failed = [item_id for item_id in ("5.1", "5.2", "5.5") if statuses.get(item_id) == "FAIL"]
        if len(failed) >= 2:
            score = _apply_cap_if_needed(score, 45, _cap_payload("dimension", dimension_id, 45, failed, "平台适配、主题权威或转化承接中两项及以上不通过，AI 可推荐最高 45 分。"), caps)
        elif failed:
            score = _apply_cap_if_needed(score, 60, _cap_payload("dimension", dimension_id, 60, failed, "平台适配、主题权威或转化承接中任一项不通过，AI 可推荐最高 60 分。"), caps)

    if dimension_id == "understandability" and statuses.get("1.6") == "FAIL":
        score = _apply_cap_if_needed(score, 70, _cap_payload("cross_dimension", dimension_id, 70, ["1.6"], "错误页与模板回退风险不通过，AI 可理解最高 70 分。"), caps)
    if dimension_id == "citability":
        if statuses.get("1.4") == "FAIL":
            score = _apply_cap_if_needed(score, 70, _cap_payload("cross_dimension", dimension_id, 70, ["1.4"], "AI crawler 实际可访问性不通过，AI 可引用最高 70 分。"), caps)
        if statuses.get("1.6") == "FAIL":
            score = _apply_cap_if_needed(score, 65, _cap_payload("cross_dimension", dimension_id, 65, ["1.6"], "错误页与模板回退风险不通过，AI 可引用最高 65 分。"), caps)
    if dimension_id == "recommendability" and statuses.get("1.4") == "FAIL":
        score = _apply_cap_if_needed(score, 65, _cap_payload("cross_dimension", dimension_id, 65, ["1.4"], "AI crawler 实际可访问性不通过，AI 可推荐最高 65 分。"), caps)

    return score, caps


def _apply_final_cap(statuses: dict[str, str], score: int) -> tuple[int, dict[str, Any] | None]:
    # 新增：sitemap 无法访问时总分最高 10 分
    if statuses.get("1.7") == "FAIL" and score > 10:
        return 10, _cap_payload("overall", None, 10, ["1.7"], "Sitemap 无法访问，总分最高 10 分。")
    failed = [item_id for item_id in ("1.4", "1.5", "1.6") if statuses.get(item_id) == "FAIL"]
    if len(failed) >= 2 and score > 62:
        return 62, _cap_payload("overall", None, 62, failed, "存在 2 个及以上 P0 技术阻塞，总分最高 62 分。")
    if len(failed) == 1 and score > 70:
        return 70, _cap_payload("overall", None, 70, failed, "存在 1 个 P0 技术阻塞，总分最高 70 分。")
    return score, None


def score_assessment(payload: dict[str, Any]) -> dict[str, Any]:
    assessments = _coerce_assessments(payload)
    all_statuses: dict[str, str] = {}
    for score_item in iter_items():
        assessment = assessments.get(score_item.id, {})
        all_statuses[score_item.id] = normalize_status(assessment.get("status") if isinstance(assessment, dict) else None)

    dimensions_result: list[dict[str, Any]] = []
    caps: list[dict[str, Any]] = []

    for dimension in DIMENSIONS:
        weighted = 0.0
        effective_points = 0
        item_results: list[dict[str, Any]] = []
        for score_item in dimension.items:
            assessment = assessments.get(score_item.id, {})
            status = all_statuses[score_item.id]
            coeff = status_coefficient(status, score_item)
            if coeff is not None:
                weighted += score_item.points * coeff
                effective_points += score_item.points
            item_results.append({
                "id": score_item.id,
                "name": score_item.name,
                "points": score_item.points,
                "status": status,
                "badge": STATUS_BADGES[status],
                "coefficient": coeff,
                "warn_coefficient": score_item.warn_coefficient,
                "note": str(assessment.get("note", "")).strip() if isinstance(assessment, dict) else "",
                "detail": score_item.detail,
                "focus": score_item.focus,
                "score_rule": score_item.score_rule,
            })

        raw_score = 0 if effective_points == 0 else _floor_score((weighted / effective_points) * 100)
        capped_score, dimension_caps = _apply_dimension_caps(dimension.id, all_statuses, raw_score)
        caps.extend(dimension_caps)
        dimensions_result.append({
            "id": dimension.id,
            "label": dimension.label,
            "short_label": dimension.short_label,
            "weight": dimension.weight,
            "score": capped_score,
            "raw_score": raw_score,
            "effective_points": effective_points,
            "caps": dimension_caps,
            "items": item_results,
        })

    raw_final_score = _floor_score(
        sum(dimension["score"] * dimension["weight"] for dimension in dimensions_result)
    )
    final_score, final_cap = _apply_final_cap(all_statuses, raw_final_score)
    if final_cap:
        caps.append(final_cap)

    # When overall cap triggers, scale dimension display scores proportionally
    # so the report doesn't show high dimension scores contradicting a low total.
    if final_score < raw_final_score and raw_final_score > 0:
        ratio = final_score / raw_final_score
        for dimension in dimensions_result:
            dimension["display_score"] = _floor_score(dimension["score"] * ratio)
    else:
        for dimension in dimensions_result:
            dimension["display_score"] = dimension["score"]

    return {
        "score_table_version": SCORE_TABLE_VERSION,
        "final_score": final_score,
        "raw_final_score": raw_final_score,
        "dimensions": dimensions_result,
        "caps": caps,
    }


def render_markdown_report(results: dict[str, Any], *, title: str = "GEO 总分") -> str:
    lines = [
        f"## {title}: {results['final_score']}/100",
        "",
        "| 评估维度 | 得分 | 权重 |",
        "|---|---:|---:|",
    ]
    for dimension in results["dimensions"]:
        ds = dimension.get("display_score", dimension["score"])
        lines.append(
            f"| {dimension['label']} | {ds}/100 | {dimension['weight'] * 100:g}% |"
        )

    for dimension in results["dimensions"]:
        ds = dimension.get("display_score", dimension["score"])
        lines.extend([
            "",
            f"## {dimension['label']} ({ds}/100)",
            "",
            "| # | 检测项 | 状态 | 说明 |",
            "|---|---|---|---|",
        ])
        for item_result in dimension["items"]:
            note = (item_result["note"] or item_result["detail"]).replace("|", "\\|")
            lines.append(
                f"| {item_result['id']} | {item_result['name']} | {item_result['badge']} | {note} |"
            )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score GEO audit assessments with the compressed v3 table.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate the built-in score table")
    validate.add_argument("--json", action="store_true", help="Print validation details as JSON")

    score = subparsers.add_parser("score", help="Score an assessment JSON file")
    score.add_argument("assessment_json")
    score.add_argument("--output", "-o")
    score.add_argument("--report")
    score.add_argument("--title", default="GEO 总分")

    args = parser.parse_args(argv)
    command_started = time.perf_counter()
    timings: dict[str, float] = {}

    if args.command == "validate":
        stage_started = time.perf_counter()
        errors = validate_config()
        timings["config_validation_seconds"] = _elapsed_since(stage_started)
        timings["total_score_module_seconds"] = _elapsed_since(command_started)
        if args.json:
            print(json.dumps({"ok": not errors, "errors": errors, "timings": timings}, ensure_ascii=False, indent=2))
        elif errors:
            print("\n".join(errors))
        else:
            print(f"Score table is valid: 5 dimensions, {EXPECTED_ITEM_COUNT} items, compressed strict v3.")
        return 1 if errors else 0

    if args.command == "score":
        stage_started = time.perf_counter()
        payload = json.loads(Path(args.assessment_json).read_text(encoding="utf-8"))
        timings["assessment_read_seconds"] = _elapsed_since(stage_started)
        stage_started = time.perf_counter()
        results = score_assessment(payload)
        timings["score_calculation_seconds"] = _elapsed_since(stage_started)
        report_text = ""
        if args.report:
            stage_started = time.perf_counter()
            report_text = render_markdown_report(results, title=args.title)
            timings["score_report_render_seconds"] = _elapsed_since(stage_started)
        timings["total_score_module_seconds"] = _elapsed_since(command_started)
        results["timings"] = timings
        if args.output:
            Path(args.output).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        if args.report:
            Path(args.report).write_text(report_text, encoding="utf-8")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
