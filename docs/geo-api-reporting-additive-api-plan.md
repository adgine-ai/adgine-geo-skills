# GEO-Api 国际版场景报告接口增量改造方案

> 状态（2026-08-19）：已在 Skills 与 GEO-Api 两侧实施；最终契约见 `docs/report-data-api-contract.md`。本文保留设计背景与数据库分析。  
> 性能落地：Topic/Prompt 聚合复用单次当前/上期数据读取；GEO-Api `089_report_data_indexes` 提供对应 CitationTest 部分索引。  
> 约束：优先新增接口，不修改现有已上线接口的 URL、参数、响应字段或语义。后端只返回结构化 JSON，HTML 继续由 `adgine/geo-reports` 生成。

## 目录

- 1. 结论与目标
- 2. 现状代码证据
- 3. 建议新增的公共协议
- 4. P0–P3 新接口清单
- 5. 各接口实现与数据表
- 6. 性能与数据库改造
- 7. 兼容和上线顺序
- 8. 测试与验收标准
- 9. Skills 切换条件

## 1. 结论与目标

### 1.1 结论

新增聚合接口是有效的，但有效点主要在以下三层：

1. 把 Prompt/Topic 名称解析和指标计算合并到同一个 HTTP 请求，直接减少 Agent 往返。
2. 把页面、流量、内容管线等场景的多个只读接口合并成稳定的 `report-data` 响应，减少 HTTP、鉴权、JSON 和 Agent 编排开销。
3. 在后端用面向报告的 SQL 聚合、批量查询和索引替代现有服务的重复查询/N+1；如果只是新接口内部顺序调用所有旧 service，虽然会减少 HTTP 次数，但数据库耗时改善有限。

GEO-Api 当前使用同一个 PostgreSQL engine/session 配置，各数据源落在不同逻辑表中，并非不同数据库。因此多数场景可以在一个请求内组合；但 GA4、Cloudflare、Worker、AI Agent 的单位和采集时间不同，组合响应必须保持分源 section，不能相加成一个“总流量”。

### 1.2 目标指标

| 场景 | Skills 当前调用 | 新接口目标 | 预期收益 |
|---|---:|---:|---|
| Topic 名称 + 最近 7/14 天详情 | 2 | 1 | 少一次实体解析往返 |
| Prompt 文本 + 最近 7/14 天表现 | 2 | 1 | 名称解析和聚合一次完成 |
| 管理层 GEO 总览 | 4（并发） | 1 | 固定口径、统一覆盖元数据 |
| Bot / 真人多视图 | 3（并发） | 1 | 少鉴权和 JSON 开销 |
| 页面详情 | 4（并发） | 1 | 统一 path 和数据新鲜度 |
| 页面机会 | 3（并发） | 1 | 页面信号与机会一次返回 |
| 内容管线 | 2 + 列表内部 N+1 风险 | 1 | 批量获取 latest version/job |

目标不是把所有 SQL 强行合成一条，而是让每个用户场景只有一个稳定的 HTTP 契约，并让后端用合理数量的批量 SQL 完成。

## 2. 现状代码证据

### 2.1 已有接口可以继续运行

- 核心分析：`src/geo/monitoring/router.py`，现有 `/analytics/visibility`、`/analytics/topics`、`/analytics/topics/{topic_id}/prompts`、Prompt overview/executions、citation、sentiment、matrix。
- 账号信息：`src/geo/auth/router.py` 的现有 `GET /api/auth/me` 已返回 `created_at`、`name`、`phone`、`email`；Skills 直接复用此接口，不需要新增或修改 GEO-Api 接口，报告层只展示这四个字段。
- GA4：`src/geo/integrations/ga4/router.py`，本地读接口为 `/overview`、`/sources`、`/ai-referrals`、`/pages`。
- Cloudflare：`src/geo/integrations/cloudflare/router.py`，本地读接口为 `/overview`、`/bot-traffic`、`/bot-pages`、Worker overview/pages/events。
- AI Agent：`src/geo/integrations/ai_agent/router.py`，已有 Bot、人类、页面、Flow、GA4 AI 和 PageSpeed 缓存接口。
- 页面机会：`src/geo/opportunities/router.py`。
- 内容：`src/geo/content/router.py`；若后续纳入新媒体母稿，再单独使用 `src/geo/media_content/router.py`。

这些接口保持不变；新接口使用新的 prefix 和独立 schema。

### 2.2 数据同库但逻辑分表

| 数据域 | 主要表 |
|---|---|
| Topic / Prompt / 模型执行 | `topics`, `prompts`, `citation_tests` |
| GA4 | `ga4_daily_summary`, `ga4_source_data`, `ga4_page_data`, `ga4_ai_landing_page_data` |
| Cloudflare API | `cf_daily_analytics`, `cf_bot_daily_visits`, `cf_bot_page_crawls` |
| Cloudflare Worker | `cf_worker_daily_stats`, `cf_worker_page_daily`, `cf_worker_events` |
| 机会 | `opportunity_runs`, `opportunities` |
| 国际内容 | `content`, `content_versions`, `workflow_jobs` |
| 新媒体母稿（如后续纳入国际报告） | `media_content`, `media_platform_versions`, `workflow_jobs` |
| 品牌 | `brand_profiles`, `brand_jobs` |
| WordPress | `wp_publish_records` |

可以围绕 `project_id + date` 聚合；页面域还需要统一 `path_key`。不要直接用未经规范化的 URL/path 做跨表 join。

### 2.3 新接口必须避开的现状问题

1. `src/geo/integrations/geo_metrics/router.py` 在同一个请求注入的 `AsyncSession` 上用 `asyncio.gather` 并发多个 service 方法。SQLAlchemy `AsyncSession` 不应被并发 task 共享。
2. `src/geo/dashboard/service.py` 同样有多处 `asyncio.gather` 共享 session；旧 Dashboard Cloudflare 条件仍使用 `bot_category == "ai_crawler"`，而当前 Cloudflare 分类为 `ai_search / ai_training / ai_assistant / ai_agent`。
3. `src/geo/integrations/geo_metrics/service.py` 的页面排序把 bot HTTP requests、Worker requests 与 GA4 sessions 直接相加；这些单位不可加。`ga4_ai_sessions / ga4_total_page_views` 也不是严格同指标分母，应改名并明确只是交叉指标，或不要在 v2 返回。
4. `src/geo/monitoring/router.py` 的 Prompt execution/overview 和 `src/geo/monitoring/prompt_analytics.py` 会读取完整 `CitationTest` ORM 对象，可能连同大字段 `response_text` 一起加载；汇总接口不需要全文。
5. 内容列表的版本和 active job 获取存在 N+1 风险。新内容管线接口必须用批量子查询/窗口函数处理。
6. `src/geo/content/router.py` 中静态 `/jobs` 路由声明在动态 `/{content_id}` 之后；需增加路由优先级回归测试。若运行时被动态 UUID 参数路由截获，单独修正注册顺序（不改变 URL/schema），而报告接口仍直接使用新的 `/report-data/content-pipeline`。

## 3. 建议新增的公共协议

新增模块：

```text
src/geo/report_data/
├── router.py
├── schemas.py
├── service.py
├── visibility.py
├── traffic.py
├── pages.py
└── operations.py
```

路由 prefix：

```text
/api/projects/{id}/report-data
```

所有响应继续使用现有 `ApiResponse[T]` envelope。每个 `T` 必须包含统一元数据：

```json
{
  "schema_version": "1.0",
  "requested_range": {"from": "2026-08-05", "to": "2026-08-18"},
  "effective_range": {"from": "2026-08-05", "to": "2026-08-18"},
  "as_of": "2026-08-18T23:59:59Z",
  "partial": false,
  "warnings": [],
  "sources": [
    {
      "name": "ga4",
      "status": "available",
      "unit": "sessions",
      "effective_range": {"from": "2026-08-05", "to": "2026-08-18"},
      "as_of": "2026-08-19T03:00:00Z",
      "reason": null
    }
  ]
}
```

规则：

- `status`: `available | empty | unavailable | stale | error`。
- `partial=true`：任一非主数据源不可用或 effective range 不完整。
- `unit` 必填；多单位 section 可使用 `requests`, `sessions`, `users`, `page_views`, `percent`, `position`, `records`。
- 不返回 HTML/CSS/SVG。
- 不返回 API token、OAuth token、Worker secret、WordPress 密码。
- 报告接口只读，不触发 sync、refresh、生成、测试、发布或重试。
- 所有列表参数默认 `limit=40`；page-based 接口翻页时保持 `limit=40` 并递增 `page`，offset-based 接口每页递增 `offset=40`。

## 4. P0–P3 新接口清单

### P0：能力发现与契约固定

#### 4.1 `GET /report-data/capabilities`

用途：Skills 在后端新接口上线后一次确认 schema 和能力，不通过逐个 404 探测。

响应：

```json
{
  "schema_version": "1.0",
  "features": {
    "executive_overview": true,
    "topic_performance": true,
    "prompt_performance": true,
    "traffic_overview": true,
    "page_detail": true,
    "content_pipeline": true
  },
  "max_range_days": 366,
  "supported_granularities": ["day", "week", "month"]
}
```

无日期参数；可短缓存 5 分钟。

### P1：核心 GEO 分析

#### 4.2 `GET /report-data/executive-overview`

参数：`date_from`, `date_to`, `granularity`, 重复 `platform`。

返回 section：

- `visibility`: 五项核心指标、trend、品牌榜单摘要。
- `topics`: Top/Bottom Topic 摘要。
- `citations`: count/share/rank 摘要。
- `opportunities`: ready/pending/empty + top items。
- `integrations`: 数据源状态。
- `traffic`: 分源小结，不生成跨源 total。

#### 4.3 `GET /report-data/topic-performance`

参数：

- `topic_id` 或 `q` 二选一；`q` 对 `Topic.name` 做 case-insensitive exact match。
- `date_from`, `date_to`, `granularity`, 重复 `platform`。
- `include_lifecycle=false`。

歧义：`q` 多条匹配返回 409，响应携带最多 10 个候选的 `id/name`；不要自动猜。

返回：`topic`, `metrics`, `prompts[]`, `citation_sources[]`；`include_lifecycle=true` 时补 `created_at/cohort`，cohort 规则由后端明确。

#### 4.4 `GET /report-data/prompt-performance`

参数：

- `prompt_id` 或 `q` 二选一；可选 `topic_id` 限定。
- `date_from`, `date_to`, `granularity`, 重复 `platform`。
- `include_executions=false`, `execution_limit=40`。

返回：

- `prompt`: id/content/topic/created_at/platforms。
- `visibility_score`, `average_position`, `share_of_voice`。
- `by_platform`, `trend`, `prev_trend`。
- `execution_summary`: total/mentioned/citation count/sentiment distribution。
- `executions[]`：只有 `include_executions=true` 时返回预览，禁止返回 `response_text` 全文。
- `citation_sources[]`。

这是“xx Prompt 最近一周/半个月”提速的最关键接口。名称解析和聚合必须在一次请求内完成。

### P2：GA4、Cloudflare、AI Bot 与页面

#### 4.5 `GET /report-data/traffic-overview`

参数：`date_from`, `date_to`, 可选 `platform`。

返回并列 section：

- `ga4`: sessions/users/page_views/channels/AI referrals。
- `cloudflare`: requests/bandwidth/threats/page_views/visitors。
- `worker`: AI event categories/referrals。
- `ai_agent`: derived Bot/Human KPI。

每个 section 自带 `source/unit/effective_range/as_of`。响应不得有 `grand_total`。

#### 4.6 `GET /report-data/pages`

参数：`date_from`, `date_to`, `limit`, `offset`, `sort_by`, `sort_direction`，可选 `platform`。

建议每行：

```json
{
  "path": "/blog/example",
  "path_key": "/blog/example",
  "bot": {"requests": 120, "source": "cf_api"},
  "worker_human": {"events": 12, "source": "worker"},
  "ga4": {"sessions": 22, "page_views": 31, "source": "ga4"},
  "visibility": {"citations": 4},
  "sort_score": null
}
```

排序必须基于同单位字段，或要求调用方显式 `sort_by`。不要再用 `bot_requests + human_requests + ga4_sessions`。

#### 4.7 `GET /report-data/page-detail`

参数：`path`（必填、精确匹配）、`date_from`, `date_to`, 可选 `platform`, `strategy=mobile|desktop`。

返回：

- `page` + `path_key`。
- `kpis`（AI citation/index/training/agent/bots）。
- `platforms[]`。
- `human_referrals` 与 `ga4` 分源。
- `related_pages[]`。
- `health.report`（只读缓存）。
- `opportunities[]`（按规范化 path 匹配）。
- `data_quality`。

禁止在此接口内部调用 PageSpeed 外部 API；只读已有缓存。

#### 4.8 `GET /report-data/data-freshness`

参数：无，或可选 `source`。

返回每个数据源最新落库时间、最新自然日、状态、预计延迟。这可以避免 Agent 为判断“有没有数据”分别调用 GA4/CF/Worker 状态接口。

### P3：内容、发布、集成与运营

#### 4.9 `GET /report-data/content-pipeline`

参数：`page`, `limit`, 可选 `status`, `publish_status`, `topic_id`。

返回：

- `summary`: 各内容状态、publish 状态、active/failed job 数。
- `items[]`: 内容基础字段 + `latest_version` + `active_job` + 最新 publish record。
- `jobs[]`: 最近 job，默认不返回大文本结果。

实现必须批量查询，不能对每个 content 分别查询版本和 job。

#### 4.10 `GET /report-data/operations-overview`

参数：可选 `job_limit`, `publication_limit`。

返回：

- `integrations[]`：仅公开状态和时间，过滤 secrets/password。
- `brand_job_summary`。
- `content_job_summary`。
- `wordpress_publications[]`。
- `opportunity_state`。
- `data_freshness[]`。

账户级 `projects/domains` 当前各自一次调用，暂不建议为了合并而新增跨权限域接口；收益小且权限边界更复杂。

## 5. 各接口实现与数据表

| 新接口 | 主要表/服务 | 建议实现方式 |
|---|---|---|
| capabilities | 常量/配置 | 不访问业务表 |
| executive-overview | citation_tests/topics/prompts/opportunities/integration credentials + 各本地流量表 | 分 section 批量聚合；同 session 顺序执行 |
| topic-performance | topics/prompts/citation_tests | Topic resolve + 一次当前/上期条件聚合 + source resolver |
| prompt-performance | prompts/topics/citation_tests | 只 select 需要列；不要加载 response_text |
| traffic-overview | GA4/CF/Worker 表 | 并列 source DTO；不跨单位 total |
| pages | cf_bot_page_crawls/cf_worker_page_daily/ga4_page_data/ga4_ai_landing_page_data | 先规范 path，再分别聚合并 merge |
| page-detail | 上述页面表 + PageSpeed cache + opportunities | 路径规范化一次，批量查询；health 只读 |
| data-freshness | 各表 MAX(date/updated_at) | 可用 UNION ALL 或短缓存 |
| content-pipeline | content/content_versions/workflow_jobs/wp_publish_records | lateral/window subquery 或批量 IN 查询 |
| operations-overview | integrations/jobs/wp/opportunities | summary SQL，不返回密钥字段 |

### 5.1 Path 规范化

建议新增共享函数 `canonical_path_key(value: str) -> str`：

- 如果传入完整 URL，取 path；忽略 scheme/host/query/fragment。
- 确保以 `/` 开头。
- 合并重复 `/`。
- 对 root 固定为 `/`。
- trailing slash 的策略必须与采集表一致；如无法迁移历史数据，查询时同时匹配 canonical 与 alternate trailing slash，并在响应返回实际 `path_key`。
- 大小写默认保留；不要在不确认站点语义时 lower-case。

## 6. 性能与数据库改造

### 6.1 AsyncSession 使用

以下二选一：

1. 推荐：在一个 request-scoped `AsyncSession` 中顺序执行经过优化的聚合 SQL；通常 DB 本身已经并行执行计划，避免应用层 session 并发。
2. 只有确有收益且连接池容量可控时，给每个并发 task 创建独立 session；禁止共享一个 `AsyncSession` 给 `asyncio.gather`。

新增 `report-data` service 不要直接复制现有 `geo_metrics/router.py` 的 gather 方式。

### 6.2 CitationTest 索引

当前 migration `81bdda40c696_add_citation_tests_perf_indexes.py` 创建 `(project_id, status, created_at)`，但高频分析过滤的是 `analyzed_at`。建议新增 migration（不要修改旧 migration）：

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS
  idx_citation_tests_project_analyzed_at_analyzed
ON citation_tests (project_id, analyzed_at DESC)
WHERE status = 'analyzed';

CREATE INDEX CONCURRENTLY IF NOT EXISTS
  idx_citation_tests_prompt_analyzed_at_analyzed
ON citation_tests (prompt_id, analyzed_at DESC)
WHERE status = 'analyzed';
```

如果生产 migration 框架不允许 transaction 内 `CONCURRENTLY`，使用 Alembic autocommit block；测试环境可用普通 index。上线前用 `EXPLAIN (ANALYZE, BUFFERS)` 验证 Topic/Prompt 7/14/30 天查询。

视实际执行计划考虑：

```sql
CREATE INDEX IF NOT EXISTS idx_prompts_topic_created
ON prompts (topic_id, created_at, id);

CREATE INDEX IF NOT EXISTS idx_topics_project_lower_name
ON topics (project_id, lower(name));
```

### 6.3 避免大字段与 N+1

- 汇总查询显式 select `CitationTest.id/platform/analyzed_at/our_brand_* /mentions/citations` 等需要列，不 select `response_text`。
- Prompt execution 列表只返回 preview；全文仍走现有单条 detail 接口。
- Content pipeline 使用 window function：`row_number() over (partition by content_id order by version desc)` 取 latest version。
- active job 使用一次子查询/CTE，按 content_id 聚合，不在 Python 循环逐条调用。

### 6.4 缓存与超时

- `capabilities`: 5 分钟进程/Redis 缓存。
- `data-freshness`: 30–60 秒。
- 其他 report-data：可选 30–60 秒，key 至少包含 project/date/platform/path/filter 和 API schema version。
- 不缓存用户权限结果到跨用户 key。
- 单请求软目标 P95 < 2 秒（Page detail/content pipeline < 3 秒）；绝不在报告接口等待外部 GA4/Cloudflare/PageSpeed 网络请求。

## 7. 兼容和上线顺序

1. 新增 `report_data` schemas/service/router，include 到 app；不触碰旧 router contract。
2. 增加索引 migration；先在 staging 用真实数据 explain。
3. 上线 `/capabilities` 和 P1 Prompt/Topic 接口。
4. 上线 P2 traffic/pages/page-detail/freshness。
5. 上线 P3 content/operations。
6. 观察 P95、DB pool、慢查询和响应体大小。
7. Skills 通过 capability flag 切换；保留现有接口 fallback 至少一个发布周期。

如果需要修复旧 service 的 AsyncSession 并发、旧 category 或错误跨单位排序，可作为内部 bugfix 单独提交；不要借此改变旧接口响应 schema。`report-data` 新接口从第一版即使用正确语义。

## 8. 测试与验收标准

### 8.1 Contract tests

- OpenAPI 中 10 个新增端点存在，query 参数 alias 正确。
- 所有响应包含 `schema_version/requested_range/effective_range/as_of/partial/sources/warnings`。
- `platform` 是 repeatable query parameter。
- q 歧义返回 409 + candidates；找不到返回 404；参数冲突返回 422。
- 旧接口 OpenAPI snapshot 无破坏性 diff。

### 8.2 数据口径测试

- 7d/14d/30d 包含自然日数量正确，当前/上一周期不重叠。
- Topic/Prompt 新接口与旧 analytics 接口在相同窗口、相同平台下指标一致。
- GA4/CF/Worker section 的 totals 与各自旧接口一致。
- 响应中不存在跨源 `grand_total`，页面排序不使用跨单位求和。
- health 无缓存时 `report=null`，且没有 PageSpeed 外部请求。
- integration/operations 响应不含 `password/token/secret/api_key` 类字段。

### 8.3 性能测试

- Prompt q + 14d：单 HTTP，固定 SQL 数，无 response_text 大字段。
- Topic + Prompts：SQL 数不随 Prompt 数线性增长。
- Content pipeline：SQL 数不随 content item 数线性增长。
- 同一个 `AsyncSession` 没有并发使用告警/异常。
- 典型 50 行页面响应体建议 < 500 KB；execution preview 限长。

### 8.4 回归测试

- 现有 `/analytics/*`, `/integrations/*`, `/ai-agent/*`, `/geo-metrics/*`, `/content/*` contract tests 全部通过。
- 新旧结果对账至少覆盖：空数据、部分集成、全量集成、当天部分数据、跨月、平台多选、Topic/Prompt 同名歧义。

## 9. Skills 切换条件

国际 Skills 当前不会主动探测未上线的新接口，避免每次报告多一次 404 和额外延迟。满足以下条件后再改 `_contracts.py`：

1. `/report-data/capabilities` 已上线并返回 `schema_version=1.0`。
2. 对应 feature flag 为 true。
3. staging contract/data parity/performance tests 通过。
4. production 观察期内错误率与 P95 达标。

切换建议：

- Prompt/Topic/页面详情先切到新单接口，并保留旧调用 fallback。
- executive/traffic/content 后切。
- fallback 只在 404/501 或 capability false 时使用；不要在 5xx 时悄悄回退并掩盖服务故障，应生成 partial/error coverage。
