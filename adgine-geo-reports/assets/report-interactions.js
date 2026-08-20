(function () {
  "use strict";

  var reportNode = document.getElementById("adgine-report-data");
  if (!reportNode || !window.echarts) return;

  var report;
  try {
    report = JSON.parse(reportNode.textContent || "{}");
  } catch (_error) {
    return;
  }

  var locale = report.locale === "zh-CN" ? "zh-CN" : "en-US";
  var colors = ["#2f6bf3", "#6558f5", "#38a9f5", "#14b8a6", "#f59e0b", "#ec6aa7", "#6f84a6", "#ef6464"];
  var instances = [];

  function number(value) {
    var parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function formatValue(value, format) {
    var parsed = number(value);
    if (parsed === null) return "—";
    if (format === "percent" || format === "percentage") return parsed.toLocaleString(locale, { maximumFractionDigits: 1 }) + "%";
    if (format === "integer" || format === "count") return parsed.toLocaleString(locale, { maximumFractionDigits: 0 });
    if (format === "rank") return "#" + parsed.toLocaleString(locale, { maximumFractionDigits: 0 });
    if (format === "seconds") return parsed.toLocaleString(locale, { maximumFractionDigits: 1 }) + "s";
    return parsed.toLocaleString(locale, { maximumFractionDigits: 2 });
  }

  function commonOption() {
    return {
      animationDuration: 420,
      animationDurationUpdate: 260,
      color: colors,
      textStyle: {
        color: "#334155",
        fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", "PingFang SC", sans-serif'
      },
      aria: { enabled: true }
    };
  }

  function richTooltip(trigger, formatter) {
    return {
      trigger: trigger,
      renderMode: "richText",
      confine: true,
      backgroundColor: "rgba(13,25,51,.94)",
      borderWidth: 0,
      textStyle: { color: "#fff", fontSize: 12 },
      formatter: formatter
    };
  }

  function lineOption(chart) {
    var rawSeries = chart.series || [];
    if (!rawSeries.length) return null;
    var longest = rawSeries.reduce(function (best, item) {
      return (item.points || []).length > (best.points || []).length ? item : best;
    }, rawSeries[0]);
    var categories = (longest.points || []).map(function (point) { return String(point.x == null ? "" : point.x); });
    var series = rawSeries.map(function (item, seriesIndex) {
      return {
        name: String(item.name || "Series " + (seriesIndex + 1)),
        type: "line",
        smooth: 0.2,
        connectNulls: false,
        showSymbol: true,
        symbolSize: 7,
        emphasis: { focus: "series" },
        lineStyle: item.dash ? { type: "dashed", width: 2.5 } : { width: 2.5 },
        data: (item.points || []).map(function (point) { return number(point.y); })
      };
    });
    var zoom = categories.length > 16 ? [
      { type: "inside", start: Math.max(0, 100 - 16 / categories.length * 100), end: 100 },
      { type: "slider", height: 18, bottom: 4, borderColor: "#dfe8f6", fillerColor: "rgba(47,107,243,.15)" }
    ] : [];
    return Object.assign(commonOption(), {
      legend: { type: "scroll", top: 0, selectedMode: true, textStyle: { color: "#61708d" } },
      tooltip: richTooltip("axis", function (params) {
        var rows = [String((params[0] || {}).axisValueLabel || "")];
        params.forEach(function (item) {
          rows.push(item.marker + " " + item.seriesName + ": " + formatValue(item.value, chart.format));
        });
        return rows.join("\n");
      }),
      grid: { left: 62, right: 24, top: 54, bottom: zoom.length ? 58 : 42, containLabel: false },
      xAxis: { type: "category", boundaryGap: false, data: categories, axisLine: { lineStyle: { color: "#cbd8eb" } }, axisLabel: { color: "#61708d", hideOverlap: true } },
      yAxis: { type: "value", axisLabel: { color: "#61708d", formatter: function (value) { return formatValue(value, chart.format); } }, splitLine: { lineStyle: { color: "#e8eff9" } } },
      dataZoom: zoom,
      series: series
    });
  }

  function barOption(chart) {
    var items = (chart.items || []).filter(function (item) { return number(item.value) !== null; });
    if (!items.length) return null;
    return Object.assign(commonOption(), {
      tooltip: richTooltip("item", function (item) { return item.marker + " " + item.name + ": " + formatValue(item.value, chart.format); }),
      grid: { left: 18, right: 54, top: 12, bottom: 18, containLabel: true },
      xAxis: { type: "value", axisLabel: { color: "#61708d", formatter: function (value) { return formatValue(value, chart.format); } }, splitLine: { lineStyle: { color: "#e8eff9" } } },
      yAxis: { type: "category", inverse: true, data: items.map(function (item) { return String(item.label || ""); }), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: "#334155", width: 210, overflow: "truncate" } },
      series: [{
        name: chart.title || "Value",
        type: "bar",
        barMaxWidth: 24,
        data: items.map(function (item) {
          return { value: number(item.value), itemStyle: { color: item.highlight ? colors[0] : (item.color || colors[2]), borderRadius: [0, 6, 6, 0] } };
        }),
        label: { show: true, position: "right", color: "#61708d", formatter: function (item) { return formatValue(item.value, chart.format); } },
        emphasis: { focus: "self" }
      }]
    });
  }

  function pieOption(chart) {
    var items = (chart.items || []).filter(function (item) { return number(item.value) !== null; });
    if (!items.length) return null;
    var donut = chart.variant === "donut";
    return Object.assign(commonOption(), {
      legend: { type: "scroll", orient: "vertical", right: 0, top: "middle", selectedMode: true, textStyle: { color: "#61708d" } },
      tooltip: richTooltip("item", function (item) { return item.marker + " " + item.name + ": " + formatValue(item.value, chart.format) + " (" + item.percent + "%)"; }),
      series: [{
        name: chart.title || "Distribution",
        type: "pie",
        radius: donut ? ["44%", "68%"] : [0, "68%"],
        center: ["38%", "52%"],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: "#fff", borderWidth: 2, borderRadius: 4 },
        label: { show: false },
        emphasis: { label: { show: true, fontWeight: 700 } },
        data: items.map(function (item) { return { name: String(item.label || ""), value: number(item.value) }; })
      }]
    });
  }

  function gaugeOption(chart) {
    if (number(chart.value) === null) return null;
    return Object.assign(commonOption(), {
      tooltip: richTooltip("item", function () { return formatValue(chart.value, chart.format); }),
      series: [{
        type: "gauge",
        min: number(chart.min) === null ? 0 : number(chart.min),
        max: number(chart.max) === null ? 100 : number(chart.max),
        startAngle: 210,
        endAngle: -30,
        progress: { show: true, width: 18, itemStyle: { color: colors[0] } },
        axisLine: { lineStyle: { width: 18, color: [[1, "#e6edf8"]] } },
        axisTick: { show: false },
        splitLine: { length: 8, lineStyle: { color: "#b9c8df", width: 1 } },
        axisLabel: { distance: 24, color: "#61708d", fontSize: 10 },
        pointer: { show: false },
        anchor: { show: false },
        detail: { valueAnimation: true, fontSize: 28, color: "#0d1933", formatter: function (value) { return formatValue(value, chart.format); } },
        data: [{ value: number(chart.value), name: chart.title || "" }]
      }]
    });
  }

  function funnelOption(chart) {
    var items = (chart.items || []).filter(function (item) { return number(item.value) !== null; });
    if (!items.length) return null;
    return Object.assign(commonOption(), {
      legend: { type: "scroll", bottom: 0, selectedMode: true, textStyle: { color: "#61708d" } },
      tooltip: richTooltip("item", function (item) { return item.marker + " " + item.name + ": " + formatValue(item.value, chart.format); }),
      series: [{
        name: chart.title || "Funnel",
        type: "funnel",
        top: 12,
        bottom: 42,
        left: "10%",
        width: "80%",
        sort: "none",
        gap: 3,
        label: { show: true, position: "inside", formatter: function (item) { return item.name + " · " + formatValue(item.value, chart.format); } },
        itemStyle: { borderColor: "#fff", borderWidth: 1 },
        emphasis: { focus: "self" },
        data: items.map(function (item) { return { name: String(item.label || ""), value: number(item.value) }; })
      }]
    });
  }

  function scatterOption(chart) {
    var points = (chart.points || []).filter(function (item) { return number(item.x) !== null && number(item.y) !== null; });
    if (!points.length) return null;
    return Object.assign(commonOption(), {
      tooltip: richTooltip("item", function (item) {
        var raw = item.data || {};
        return raw.name + "\n" + chart.x_label + ": " + formatValue(raw.value[0], chart.x_format) + "\n" + chart.y_label + ": " + formatValue(raw.value[1], chart.y_format);
      }),
      grid: { left: 76, right: 28, top: 24, bottom: 62 },
      xAxis: {
        type: "value", name: chart.x_label || "", nameLocation: "middle", nameGap: 42,
        min: chart.x_min, max: chart.x_max, inverse: !!chart.x_reverse,
        axisLabel: { color: "#61708d", formatter: function (value) { return formatValue(value, chart.x_format); } },
        splitLine: { lineStyle: { color: "#e8eff9" } }
      },
      yAxis: {
        type: "value", name: chart.y_label || "", nameLocation: "middle", nameGap: 54,
        min: chart.y_min, max: chart.y_max, inverse: !!chart.y_reverse,
        axisLabel: { color: "#61708d", formatter: function (value) { return formatValue(value, chart.y_format); } },
        splitLine: { lineStyle: { color: "#e8eff9" } }
      },
      series: [{
        type: "scatter",
        symbolSize: 12,
        emphasis: { focus: "self", scale: 1.35 },
        data: points.map(function (point) { return { name: String(point.label || ""), value: [number(point.x), number(point.y)] }; })
      }]
    });
  }

  function treemapOption(chart) {
    var items = (chart.items || []).filter(function (item) { return number(item.value) !== null && number(item.value) > 0; });
    if (!items.length) return null;
    return Object.assign(commonOption(), {
      tooltip: richTooltip("item", function (item) { return item.name + ": " + formatValue(item.value, chart.format); }),
      series: [{
        type: "treemap",
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        label: { show: true, formatter: function (item) { return item.name + "\n" + formatValue(item.value, chart.format); } },
        upperLabel: { show: false },
        itemStyle: { borderColor: "#fff", borderWidth: 3, gapWidth: 2 },
        emphasis: { focus: "self" },
        data: items.map(function (item) { return { name: String(item.label || ""), value: number(item.value) }; })
      }]
    });
  }

  function heatmapOption(chart) {
    var columns = chart.columns || [];
    var rows = chart.rows || [];
    if (!columns.length || !rows.length) return null;
    var data = [];
    rows.forEach(function (row, rowIndex) {
      columns.forEach(function (column, columnIndex) {
        var value = number((row.values || {})[column]);
        if (value !== null) data.push([columnIndex, rowIndex, value]);
      });
    });
    if (!data.length) return null;
    var maximum = Math.max.apply(null, data.map(function (item) { return item[2]; }).concat([1]));
    return Object.assign(commonOption(), {
      tooltip: richTooltip("item", function (item) {
        return rows[item.value[1]].label + "\n" + columns[item.value[0]] + ": " + formatValue(item.value[2], chart.format);
      }),
      grid: { left: 112, right: 24, top: 18, bottom: 64 },
      xAxis: { type: "category", data: columns, splitArea: { show: true }, axisLabel: { color: "#61708d", interval: 0, rotate: columns.length > 5 ? 25 : 0 } },
      yAxis: { type: "category", inverse: true, data: rows.map(function (row) { return String(row.label || ""); }), splitArea: { show: true }, axisLabel: { color: "#334155", width: 95, overflow: "truncate" } },
      visualMap: { min: 0, max: maximum, calculable: true, orient: "horizontal", left: "center", bottom: 0, inRange: { color: ["#edf5ff", "#9fc4ff", "#2f6bf3", "#5548e8"] }, textStyle: { color: "#61708d" } },
      series: [{ type: "heatmap", data: data, label: { show: true, color: "#0d1933", formatter: function (item) { return formatValue(item.value[2], chart.format); } }, emphasis: { itemStyle: { shadowBlur: 8, shadowColor: "rgba(13,25,51,.24)" } } }]
    });
  }

  function progressOption(chart) {
    var items = (chart.items || []).filter(function (item) { return number(item.value) !== null; });
    if (!items.length) return null;
    var maximum = Math.max.apply(null, items.map(function (item) { return number(item.max) || 100; }).concat([100]));
    return Object.assign(commonOption(), {
      tooltip: richTooltip("item", function (item) { return item.name + ": " + formatValue(item.value, chart.format); }),
      grid: { left: 18, right: 48, top: 12, bottom: 18, containLabel: true },
      xAxis: { type: "value", min: 0, max: maximum, axisLabel: { color: "#61708d", formatter: function (value) { return formatValue(value, chart.format); } }, splitLine: { show: false } },
      yAxis: { type: "category", inverse: true, data: items.map(function (item) { return String(item.label || ""); }), axisLine: { show: false }, axisTick: { show: false } },
      series: [{ type: "bar", showBackground: true, backgroundStyle: { color: "#e6edf8", borderRadius: 7 }, barWidth: 14, itemStyle: { color: colors[0], borderRadius: 7 }, label: { show: true, position: "right", formatter: function (item) { return formatValue(item.value, chart.format); } }, data: items.map(function (item) { return number(item.value); }) }]
    });
  }

  function optionFor(chart) {
    var type = chart.type || "bar_chart";
    if (type === "line") type = "line_chart";
    if (type === "bar") type = "bar_chart";
    if (type === "donut") type = "pie_chart";
    if (type === "heatmap") type = "heatmap_table";
    if (type === "line_chart") return lineOption(chart);
    if (type === "pie_chart") return pieOption(chart);
    if (type === "gauge") return gaugeOption(chart);
    if (type === "funnel") return funnelOption(chart);
    if (type === "scatter_plot") return scatterOption(chart);
    if (type === "treemap") return treemapOption(chart);
    if (type === "heatmap_table") return heatmapOption(chart);
    if (type === "progress_bar") return progressOption(chart);
    if (type === "bar_chart") return barOption(chart);
    return null;
  }

  function heightFor(chart) {
    var type = chart.type || "bar_chart";
    if (type === "bar" || type === "bar_chart" || type === "progress_bar") return Math.max(240, Math.min(620, 90 + (chart.items || []).length * 34));
    if (type === "heatmap" || type === "heatmap_table") return Math.max(300, Math.min(640, 120 + (chart.rows || []).length * 38));
    if (type === "scatter_plot" || type === "treemap") return 390;
    if (type === "line" || type === "line_chart") return 340;
    return 320;
  }

  (report.charts || []).forEach(function (chart, index) {
    var host = document.querySelector('[data-echart-index="' + index + '"]');
    if (!host) return;
    var option = optionFor(chart);
    if (!option) return;
    var fallback = host.innerHTML;
    var instance = null;
    try {
      host.style.height = heightFor(chart) + "px";
      host.classList.add("echart-live");
      host.innerHTML = "";
      instance = window.echarts.init(host, null, { renderer: "canvas" });
      instance.setOption(option);
      instances.push(instance);
    } catch (_error) {
      if (instance) instance.dispose();
      host.classList.remove("echart-live");
      host.style.height = "";
      host.innerHTML = fallback;
    }
  });

  var resizeTimer;
  window.addEventListener("resize", function () {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(function () {
      instances.forEach(function (instance) { instance.resize(); });
    }, 80);
  });
  window.addEventListener("beforeprint", function () {
    instances.forEach(function (instance) { instance.resize(); });
  });
})();
