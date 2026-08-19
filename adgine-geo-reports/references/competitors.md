# Competitor reports

Use these read-only scenarios for customer-facing competitor analysis. They call the existing GEO-Api routes directly and never modify competitors or GEO-Api.

## Routing

| User intent | Scenario | Required selector |
|---|---|---|
| All competitors / competitor ranking | `competitor-rankings` | Project |
| Compare one competitor with our brand | `competitor-overview` | Competitor |
| One competitor by Topic | `competitor-topics` | Competitor |
| One competitor by Prompt in a Topic | `competitor-prompts` | Competitor + Topic |

Examples:

```bash
python3 scripts/report.py competitor-rankings --project-id <project-id> --period 7d --locale zh-CN
python3 scripts/report.py competitor-overview --project-id <project-id> --competitor "Acme" --period 14d --locale zh-CN
python3 scripts/report.py competitor-topics --project-id <project-id> --competitor-id <competitor-id> --period 30d --locale en-US
python3 scripts/report.py competitor-prompts --project-id <project-id> --competitor-id <competitor-id> --topic-id <topic-id> --period 7d --locale en-US
```

## Selectors and filters

- Prefer `--competitor-id` for one business call. `--competitor` accepts an ID, exact configured name, or exact configured domain. Name/domain lookup uses `GET /api/projects/{id}/competitors` and accepts its current `{items, total}` response.
- Prefer `--topic-id` for Prompt reports. `--topic` resolves an exact ID/name through the existing Topic analytics endpoint.
- Repeat `--platform` or use comma-separated platform values.
- Topic and Prompt competitor reports default `types=visibility`. Repeat `--type` or use comma-separated types to override it.
- Repeat `--tag-id` or use comma-separated UUIDs to filter Topic/Prompt reports.
- Competitor overview optionally accepts repeatable/comma-separated `--filter-topic-id` and `--filter-prompt-id`. A single `--topic-id`/`--topic` and `--prompt-id` are also accepted as conveniences.

## Endpoint contract

- Rankings: `GET /api/projects/{id}/competitors/visibility-rankings`
- Overview: `GET /api/projects/{id}/competitors/{competitor_id}/overview`
- Topics: `GET /api/projects/{id}/competitors/{competitor_id}/topics`
- Prompts: `GET /api/projects/{id}/competitors/{competitor_id}/topics/{topic_id}/prompts`

All accept `date_from`, `date_to`, and repeatable `platform`. Topic/Prompt routes also accept repeatable `types` and `tags`. The overview route accepts repeatable `topic_id` and `prompt_id`.

## Interpretation rules

- The ranking endpoint response is the complete “all competitors” result. Do not join or merge configured competitors into it and do not claim omitted configured competitors have zero visibility.
- Visibility score is the percentage of analyses mentioning the competitor. Share of voice is the competitor's mentions divided by all brand mentions. Average position is the average best mention position per analysis.
- Positive visibility-rank or average-position change means performance worsened; lower rank/position values are better.
- Sentiment percentages exclude unclassified items from their denominator; keep classified and unclassified counts separate when displayed.
- These endpoints return period aggregates and previous-period changes, not daily points. Use bars, donuts, scatter plots, progress/gauge elements, and tables. Never fabricate a line chart.
- Hide internal IDs unless `--show-ids` is explicit.
