"""Stable report scenario registry aligned with the current GEO-Api routers.

Keep this module declarative. Network calls and presentation belong in
``report.py`` and ``_reporting.py`` respectively.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RequestSpec:
    alias: str
    path: str
    date_style: str = "none"  # none | analytics | traffic | dashboard-period
    accepts_platform: bool = False
    paging: str = "none"  # none | page | page_size | offset
    required: bool = True
    query: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Scenario:
    name: str
    phase: str
    title: str
    title_zh: str
    density: str
    requests: tuple[RequestSpec, ...]
    requires: tuple[str, ...] = ()
    description: str = ""


def _r(alias, endpoint_path, date_style="none", *, platform=False, paging="none",
       required=True, **query):
    return RequestSpec(
        alias=alias,
        path=endpoint_path,
        date_style=date_style,
        accepts_platform=platform,
        paging=paging,
        required=required,
        query=query,
    )


SCENARIOS = {
    # P0/P1: facade and core GEO analytics.
    "executive-overview": Scenario(
        "executive-overview", "P1", "GEO Executive Overview", "GEO 管理层总览", "analysis",
        (
            _r("visibility", "/api/projects/{project_id}/analytics/visibility", "analytics", platform=True),
            _r("traffic", "/api/projects/{project_id}/geo-metrics/overview", "traffic", required=False),
            _r("opportunities", "/api/projects/{project_id}/opportunities", required=False),
            _r("integrations", "/api/projects/{project_id}/integrations", required=False),
        ),
        description="Visibility, source-separated traffic, opportunities, and integration coverage.",
    ),
    "catalog": Scenario(
        "catalog", "P1", "Topic and Prompt Catalog", "Topic / Prompt 目录", "inventory",
        (
            _r("topics", "/api/projects/{project_id}/topics", paging="page"),
            _r("prompts", "/api/projects/{project_id}/prompts", paging="page"),
        ),
    ),
    "visibility": Scenario(
        "visibility", "P1", "AI Visibility", "AI 可见性分析", "analysis",
        (_r("visibility", "/api/projects/{project_id}/analytics/visibility", "analytics", platform=True),),
    ),
    "matrix": Scenario(
        "matrix", "P1", "Brand × AI Platform Matrix", "品牌 × AI 平台矩阵", "analysis",
        (_r("matrix", "/api/projects/{project_id}/analytics/platforms/matrix", "analytics", metric="visibility_score"),),
    ),
    "topics": Scenario(
        "topics", "P1", "Topic Performance", "Topic 表现分析", "analysis",
        (_r("topics", "/api/projects/{project_id}/analytics/topics", "analytics", platform=True),),
    ),
    "topic-detail": Scenario(
        "topic-detail", "P1", "Topic Detail", "Topic 详细分析", "detail",
        (_r("prompts", "/api/projects/{project_id}/analytics/topics/{topic_id}/prompts", "analytics", platform=True),),
        requires=("topic",),
    ),
    "topic-lifecycle": Scenario(
        "topic-lifecycle", "P1", "Topic Lifecycle", "Topic 生命周期分析", "analysis",
        (
            _r("prompt_metadata", "/api/projects/{project_id}/topics/{topic_id}/prompts", paging="page"),
            _r("prompts", "/api/projects/{project_id}/analytics/topics/{topic_id}/prompts", "analytics", platform=True),
        ),
        requires=("topic",),
    ),
    "prompt-performance": Scenario(
        "prompt-performance", "P1", "Prompt Performance", "Prompt 表现分析", "detail",
        (_r("prompt", "/api/projects/{project_id}/analytics/prompts/{prompt_id}/overview", "analytics", platform=True),),
        requires=("prompt",),
    ),
    "prompt-executions": Scenario(
        "prompt-executions", "P1", "Prompt Executions", "Prompt 执行记录", "detail",
        (_r("executions", "/api/projects/{project_id}/analytics/prompts/{prompt_id}/executions", "analytics", platform=True, paging="page_size"),),
        requires=("prompt",),
    ),
    "citations": Scenario(
        "citations", "P1", "Citation Performance", "引用表现分析", "analysis",
        (_r("citations", "/api/projects/{project_id}/analytics/citation/aggregate", "analytics", platform=True),),
    ),
    "sentiment": Scenario(
        "sentiment", "P1", "Brand Sentiment", "品牌情感分析", "analysis",
        (_r("sentiment", "/api/projects/{project_id}/analytics/sentiment", "analytics", platform=True),),
    ),

    # P2: acquisition, crawlers, humans, pages, and flows.
    "ga4-overview": Scenario(
        "ga4-overview", "P2", "GA4 Traffic Overview", "GA4 流量总览", "analysis",
        (_r("ga4", "/api/projects/{project_id}/integrations/ga4/overview", "traffic"),),
    ),
    "ga4-referrals": Scenario(
        "ga4-referrals", "P2", "GA4 AI Referrals", "GA4 AI 引荐分析", "analysis",
        (_r("referrals", "/api/projects/{project_id}/integrations/ga4/ai-referrals", "traffic"),),
    ),
    "ga4-pages": Scenario(
        "ga4-pages", "P2", "GA4 Page Performance", "GA4 页面表现", "inventory",
        (_r("pages", "/api/projects/{project_id}/integrations/ga4/pages", "traffic", paging="offset"),),
    ),
    "cloudflare-overview": Scenario(
        "cloudflare-overview", "P2", "Cloudflare Traffic Overview", "Cloudflare 流量总览", "analysis",
        (_r("cloudflare", "/api/projects/{project_id}/integrations/cloudflare/overview", "traffic"),),
    ),
    "cloudflare-bots": Scenario(
        "cloudflare-bots", "P2", "Cloudflare Bot Traffic", "Cloudflare 爬虫流量", "analysis",
        (_r("bots", "/api/projects/{project_id}/integrations/cloudflare/bot-traffic", "traffic"),),
    ),
    "cloudflare-pages": Scenario(
        "cloudflare-pages", "P2", "Cloudflare Bot Pages", "Cloudflare 爬虫页面", "inventory",
        (_r("pages", "/api/projects/{project_id}/integrations/cloudflare/bot-pages", "traffic", paging="offset"),),
    ),
    "worker-traffic": Scenario(
        "worker-traffic", "P2", "Cloudflare Worker AI Traffic", "Worker AI 流量", "analysis",
        (_r("worker", "/api/projects/{project_id}/integrations/cloudflare/worker/overview", "traffic"),),
    ),
    "worker-pages": Scenario(
        "worker-pages", "P2", "Cloudflare Worker Pages", "Worker 页面流量", "inventory",
        (_r("worker_pages", "/api/projects/{project_id}/integrations/cloudflare/worker/pages", "traffic", paging="offset"),),
    ),
    "worker-events": Scenario(
        "worker-events", "P2", "Cloudflare Worker Events", "Worker 事件记录", "inventory",
        (_r("worker_events", "/api/projects/{project_id}/integrations/cloudflare/worker/events", "traffic", paging="page"),),
    ),
    "worker-deployment": Scenario(
        "worker-deployment", "P2", "Cloudflare Worker Deployment", "Worker 部署状态", "status",
        (_r("worker_deployment", "/api/projects/{project_id}/integrations/cloudflare/worker/deploy-status"),),
    ),
    "ai-overview": Scenario(
        "ai-overview", "P2", "AI Traffic Overview", "AI 流量总览", "analysis",
        (_r("overview", "/api/projects/{project_id}/ai-agent/overview-kpi", "traffic", platform=True),),
    ),
    "ai-bots": Scenario(
        "ai-bots", "P2", "AI Bot Analysis", "AI Bot 分析", "analysis",
        (
            _r("overview", "/api/projects/{project_id}/ai-agent/bot-traffic-overview", "traffic", platform=True),
            _r("platforms", "/api/projects/{project_id}/ai-agent/bot-platforms", "traffic", platform=True, required=False),
            _r("useragents", "/api/projects/{project_id}/ai-agent/bot-useragents", "traffic", platform=True, required=False),
        ),
    ),
    "ai-humans": Scenario(
        "ai-humans", "P2", "AI-Driven Human Traffic", "AI 真人引流分析", "analysis",
        (
            _r("overview", "/api/projects/{project_id}/ai-agent/human-traffic-overview", "traffic", platform=True),
            _r("platforms", "/api/projects/{project_id}/ai-agent/human-platforms", "traffic", platform=True, required=False),
            _r("pages", "/api/projects/{project_id}/ai-agent/human-pages", "traffic", platform=True, paging="offset", required=False),
        ),
    ),
    "ai-pages": Scenario(
        "ai-pages", "P2", "AI Page Performance", "AI 页面表现", "inventory",
        (_r("pages", "/api/projects/{project_id}/ai-agent/pages-detail", "traffic", platform=True, paging="offset"),),
    ),
    "ai-flow": Scenario(
        "ai-flow", "P2", "AI Platform → Page Flow", "AI 平台 → 页面流向", "analysis",
        (_r("flow", "/api/projects/{project_id}/ai-agent/pages-platform-flow", "traffic", platform=True),),
    ),
    "human-flow": Scenario(
        "human-flow", "P2", "AI Human Referral Flow", "AI 真人引荐流向", "analysis",
        (_r("flow", "/api/projects/{project_id}/ai-agent/human-platform-flow", "traffic", platform=True),),
    ),
    "ga4-flow": Scenario(
        "ga4-flow", "P2", "GA4 AI Landing Flow", "GA4 AI 着陆页流向", "analysis",
        (_r("flow", "/api/projects/{project_id}/ai-agent/ga-platform-landing-flow", "traffic", platform=True),),
    ),
    "page-detail": Scenario(
        "page-detail", "P2", "Page GEO Detail", "页面 GEO 详细分析", "detail",
        (
            _r("kpi", "/api/projects/{project_id}/ai-agent/pages/by-path/kpi", "traffic", path="{page_path}"),
            _r("platforms", "/api/projects/{project_id}/ai-agent/pages/by-path/platforms", "traffic", path="{page_path}", required=False),
            _r("related", "/api/projects/{project_id}/ai-agent/pages/by-path/related", "traffic", path="{page_path}", required=False),
            _r("health", "/api/projects/{project_id}/ai-agent/pages/by-path/health", path="{page_path}", required=False),
        ),
        requires=("path",),
    ),
    "page-health": Scenario(
        "page-health", "P2", "Page Health", "页面健康报告", "detail",
        (_r("health", "/api/projects/{project_id}/ai-agent/pages/by-path/health", path="{page_path}"),),
        requires=("path",),
    ),
    "page-opportunities": Scenario(
        "page-opportunities", "P2", "Page Opportunities", "页面优化机会", "analysis",
        (
            _r("kpi", "/api/projects/{project_id}/ai-agent/pages/by-path/kpi", "traffic", path="{page_path}"),
            _r("health", "/api/projects/{project_id}/ai-agent/pages/by-path/health", path="{page_path}", required=False),
            _r("opportunities", "/api/projects/{project_id}/opportunities", required=False),
        ),
        requires=("path",),
        description="Deterministic page recommendations; never triggers PageSpeed refresh.",
    ),

    # P3: operational, content, publication, account, and inventory reporting.
    "opportunities": Scenario(
        "opportunities", "P3", "Optimization Opportunities", "优化机会清单", "inventory",
        (_r("opportunities", "/api/projects/{project_id}/opportunities"),),
    ),
    "opportunity-detail": Scenario(
        "opportunity-detail", "P3", "Opportunity Detail", "优化机会详情", "detail",
        (_r("opportunity", "/api/projects/{project_id}/opportunities/{resource_id}"),),
        requires=("resource-id",),
    ),
    "content-pipeline": Scenario(
        "content-pipeline", "P3", "Content Pipeline", "内容生产管线", "status",
        (
            _r("content", "/api/projects/{project_id}/content", paging="page"),
            _r("jobs", "/api/projects/{project_id}/content/jobs", paging="page", required=False),
        ),
    ),
    "traffic-overview": Scenario(
        "traffic-overview", "P2", "Traffic Overview", "流量综合总览", "analysis",
        (
            _r("ga4", "/api/projects/{project_id}/integrations/ga4/overview", "traffic", required=False),
            _r("cloudflare", "/api/projects/{project_id}/integrations/cloudflare/overview", "traffic", required=False),
            _r("worker", "/api/projects/{project_id}/integrations/cloudflare/worker/overview", "traffic", required=False),
            _r("ai_agent", "/api/projects/{project_id}/ai-agent/overview-kpi", "traffic", platform=True, required=False),
        ),
        description="Source-separated GA4, Cloudflare, Worker, and AI Agent traffic coverage.",
    ),
    "data-freshness": Scenario(
        "data-freshness", "P3", "Data Freshness", "数据新鲜度", "status",
        (_r("integrations", "/api/projects/{project_id}/integrations", required=False),),
        description="Backend-defined freshness, expected lag, and source availability.",
    ),
    "operations-overview": Scenario(
        "operations-overview", "P3", "Operations Overview", "运营状态总览", "status",
        (
            _r("integrations", "/api/projects/{project_id}/integrations", required=False),
            _r("brand_jobs", "/api/projects/{project_id}/brand/jobs", required=False),
            _r("publications", "/api/projects/{project_id}/integrations/wordpress/publishes", required=False),
            _r("opportunities", "/api/projects/{project_id}/opportunities", required=False),
        ),
        description="Sanitized integration, job, publication, opportunity, and freshness state.",
    ),
    "content-detail": Scenario(
        "content-detail", "P3", "Content Detail", "内容详情", "detail",
        (_r("content", "/api/projects/{project_id}/content/{resource_id}"),),
        requires=("resource-id",),
    ),
    "brand-profile": Scenario(
        "brand-profile", "P3", "Brand Profile", "品牌画像", "detail",
        (_r("brand", "/api/projects/{project_id}/brand"),),
    ),
    "brand-jobs": Scenario(
        "brand-jobs", "P3", "Brand Generation Jobs", "品牌生成任务", "status",
        (_r("jobs", "/api/projects/{project_id}/brand/jobs"),),
    ),
    "integration-health": Scenario(
        "integration-health", "P3", "Integration Health", "数据集成状态", "status",
        (_r("integrations", "/api/projects/{project_id}/integrations"),),
    ),
    "wordpress-publications": Scenario(
        "wordpress-publications", "P3", "WordPress Publications", "WordPress 发布记录", "status",
        (_r("publications", "/api/projects/{project_id}/integrations/wordpress/publishes"),),
    ),
    "wordpress-publishable": Scenario(
        "wordpress-publishable", "P3", "WordPress Publishable Content", "WordPress 待发布内容", "inventory",
        (_r("content", "/api/projects/{project_id}/integrations/wordpress/publishable-content"),),
    ),
    "billing": Scenario(
        "billing", "P3", "Account and Billing", "账户与账单", "status",
        (
            _r("subscription", "/api/payments/subscription", required=False),
            _r("credits", "/api/payments/credits/me", required=False),
            _r("plans", "/api/payments/plans", required=False),
        ),
    ),
    "account-info": Scenario(
        "account-info", "P3", "My Account Information", "我的账号信息", "detail",
        (_r("account", "/api/auth/me"),),
        description="Authenticated account creation time, name, phone number, and email address.",
    ),
    "projects": Scenario(
        "projects", "P3", "Project Catalog", "项目目录", "inventory",
        (_r("projects", "/api/projects", paging="page"),),
    ),
    "domains": Scenario(
        "domains", "P3", "Domain Portfolio", "域名资产", "inventory",
        (_r("domains", "/api/domains"),),
    ),
    "saas-task": Scenario(
        "saas-task", "P3", "SaaS Deployment Status", "SaaS 部署状态", "status",
        (_r("task", "/api/saas/task/{resource_id}"),),
        requires=("resource-id",),
    ),
}


def get_scenario(name):
    try:
        return SCENARIOS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown report scenario: {name}") from exc


def scenario_rows():
    return [
        {
            "name": item.name,
            "phase": item.phase,
            "title": item.title,
            "title_zh": item.title_zh,
            "density": item.density,
            "requires": list(item.requires),
            "api_calls": len(item.requests),
        }
        for item in SCENARIOS.values()
    ]
