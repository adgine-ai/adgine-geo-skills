import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_default_report_template_uses_new_score_table(self):
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("## GEO 总分", skill_text)
        self.assertIn("| 维度五：AI 可推荐 |", skill_text)
        self.assertIn("| # | 检测项 | 状态 | 说明 |", skill_text)
        self.assertNotIn("子项分值", skill_text)
        self.assertIn("5 大项、30 个压缩检测项", skill_text)
        self.assertIn("scripts/geo_score.py", skill_text)
        self.assertIn("可选 AI 引用性/可见性采样测试", skill_text)
        self.assertIn("普通“审计/检测 URL”默认不执行", skill_text)
        self.assertIn("默认报告不得输出 AI 可见性采样、AI 引用性测试", skill_text)
        self.assertIn("可选 AI 引用性/可见性采样章节不得出现在 GEO 总分表中", skill_text)
        self.assertNotIn("## D6: AI 可见性采样测试", skill_text)
        self.assertNotIn("公开数据 GEO 分 × 70% + AI 可见性采样分 × 30%", skill_text)
        self.assertNotIn("31 项", skill_text)
        self.assertIn("一站式 GEO/AI 可见性代运营服务", skill_text)
        self.assertIn("同时运行不得超过 5 个", skill_text)
        self.assertIn("**抽样子页**: {sub_pages_requested} 页抽样，{sub_pages_fetched} 页成功", skill_text)
        self.assertIn("若 sitemap 不存在或没有可用页面 URL，则从首页同域链接中提取候选页再抽样", skill_text)
        self.assertIn("必须优先尝试可用的外部/agent 搜索能力", skill_text)
        self.assertIn("外部兜底信号不能把真实 crawler 阻断项改判为直接可达", skill_text)
        self.assertIn("不得输出“未使用外部搜索抵消 crawler 阻断”", skill_text)
        self.assertIn("核心转化页、核心信任页、核心引用页、关键模板页、技术入口页、高风险验证页", skill_text)
        self.assertIn("每种重要残余页面模板至少抽 1 个", skill_text)
        self.assertIn("没有可用 sitemap 时必须判定 `FAIL`", skill_text)
        self.assertIn("报告正文暂不输出报告生成耗时", skill_text)
        self.assertIn("报告正文不包含 `报告生成耗时`", skill_text)
        self.assertNotIn("report_generation_elapsed_seconds", skill_text)
        self.assertIn("报告正文不要描述 URL 获取、sitemap 抽样、页面优先级或采集调度逻辑", skill_text)
        self.assertIn("meta.timings", skill_text)
        self.assertIn("meta.timings.notfound_probe_seconds", skill_text)
        self.assertIn("WARN` 使用每个检测项自己的待优化系数", skill_text)
        self.assertIn("总分最高 62", skill_text)
        self.assertIn("render_report_pdf.py` 可用 `--timings-output`", skill_text)
        self.assertIn("默认使用 ReportLab 生成 PDF，不调用 Chrome/Playwright", skill_text)
        self.assertIn("--engine reportlab", skill_text)
        self.assertIn("scripts/geo_timing.py artifacts", skill_text)
        self.assertIn("默认不做逐步骤 `mark` 打点", skill_text)
        self.assertNotIn("assessment_generation_start", skill_text)
        self.assertIn("geo_audit_timing_summary.json", skill_text)
        self.assertIn("--max-subpages 20 --concurrency 6", skill_text)
        self.assertIn("python <SKILL_DIR>/scripts/geo_score.py validate", skill_text)
        self.assertNotIn("76 个检测项", skill_text)


if __name__ == "__main__":
    unittest.main()
