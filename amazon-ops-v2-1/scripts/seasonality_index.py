#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
季节性系数生成器（技能自带，无第三方依赖）。

口径（用户 2026-11-27 确认）：
  用 keyword_trend(type=2, 月度) 返回的 search_volume_trend 扁平数组
  [yyyyMM, value, yyyyMM, value, ...]：
    1. 取最近 N 个完整月（默认 12，避开未结束的当月）
    2. 在窗口内找月搜索量最大值 max
    3. 每月系数 = 该月搜索量 / max，四舍五入保留 1 位小数
    4. 最高月系数 = 1.0（若多个月并列最大，全部 1.0）
  系数只用于「旺季与季节性」判断和淡旺季排期，不写进 Listing 文案。

输入 JSON 支持三种形态：
  A) keyword_trend 单词返回： {"data":{"keyword":"x","search_volume_trend":[...]}}
  B) 多个 A 组成的数组：      [ {...A...}, {...A...} ]
  C) 规整数组：               {"keywords":[{"keyword":"x","search_volume_trend":[...]}, ...]}

用法：
  python3 seasonality_index.py --input kw_trends.json --months 12 \
      --output 季节性系数.md --json-report 季节性系数.json
  python3 seasonality_index.py --input kw_trends.json --months 12 --stdout
"""
import argparse
import io
import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from collections import OrderedDict


def parse_args():
    p = argparse.ArgumentParser(description="生成关键词月度季节性系数")
    p.add_argument("--input", required=True, help="关键词月度数据 JSON 路径")
    p.add_argument("--months", type=int, default=12, help="取最近几个完整月（默认 12）")
    p.add_argument("--output", help="Markdown 输出路径")
    p.add_argument("--json-report", help="结构化 JSON 输出路径")
    p.add_argument("--stdout", action="store_true", help="把 Markdown 打到标准输出")
    return p.parse_args()


def load_keywords(path):
    with io.open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict) and "keywords" in raw:
        items = raw["keywords"]
    elif isinstance(raw, list):
        items = raw
    else:
        items = [raw]
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        data = it.get("data", it)
        kw = data.get("keyword") or it.get("keyword") or "(未命名)"
        flat = data.get("search_volume_trend") or it.get("search_volume_trend") or []
        series = OrderedDict()
        for i in range(0, len(flat) - 1, 2):
            period, val = str(flat[i]), flat[i + 1]
            try:
                v = int(float(val))
            except (TypeError, ValueError):
                continue
            if v >= 0:
                series[period] = v
        if series:
            out.append({"keyword": kw, "series": series})
    return out


def coeff(value, peak):
    if peak <= 0:
        return 0.0
    d = (Decimal(value) / Decimal(peak) * Decimal(10)).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    return float(d) / 10.0


def build(keywords, months):
    all_periods = set()
    for k in keywords:
        all_periods.update(k["series"].keys())
    periods = sorted(all_periods)[-months:]  # 最近 N 个完整月
    rows = []
    for k in keywords:
        vals = {p: k["series"].get(p) for p in periods}
        peak = max([v for v in vals.values() if v is not None] or [0])
        peak_months = [p for p, v in vals.items() if v == peak]
        ratios = OrderedDict()
        for p in periods:
            v = vals[p]
            ratios[p] = None if v is None else coeff(v, peak)
        rows.append({
            "keyword": k["keyword"],
            "peak": peak,
            "peak_months": peak_months,
            "coefficients": ratios,
        })
    return periods, rows


def fmt_month(p):
    return p[:4] + "-" + p[4:]


def to_markdown(periods, rows, months):
    lines = [
        "## 季节性系数（最近 %d 个完整月）" % months,
        "",
        "口径：`keyword_trend`(type=2) 月搜索量；窗口内最高月 = 1.0，其余 = 该月量 / 最高月量，四舍五入保留 1 位小数。"
        "数据区间 %s ~ %s。系数用于淡旺季判断，不进 Listing 文案。" % (
            fmt_month(periods[0]), fmt_month(periods[-1])),
        "",
        "| 月份 | " + " | ".join(r["keyword"] for r in rows) + " |",
        "|" + "---|" * (len(rows) + 1),
    ]
    for p in periods:
        cells = []
        for r in rows:
            v = r["coefficients"][p]
            cells.append("—" if v is None else ("%.1f" % v))
        lines.append("| %s | %s |" % (fmt_month(p), " | ".join(cells)))
    lines.append("")
    for r in rows:
        lines.append("- **%s**：峰值月 %s（月搜索 %s），淡季系数最低 %.1f。" % (
            r["keyword"],
            "、".join(fmt_month(p) for p in r["peak_months"]),
            format(r["peak"], ","),
            min([v for v in r["coefficients"].values() if v is not None] or [0]),
        ))
    lines.append("")
    lines.append("> 四舍五入到 1 位小数时，接近峰值的月份可能并列显示 1.0（如 68,056 与 68,013 都取 1.0）；"
                 "峰值绝对值仍以 `peak` 字段为准，系数只表示相对强弱。")
    return "\n".join(lines)


def main():
    args = parse_args()
    keywords = load_keywords(args.input)
    if not keywords:
        print("ERROR: 输入里没有可解析的 search_volume_trend", file=sys.stderr)
        sys.exit(1)
    periods, rows = build(keywords, args.months)
    md = to_markdown(periods, rows, args.months)
    if args.stdout:
        print(md)
    if args.output:
        with io.open(args.output, "w", encoding="utf-8") as f:
            f.write(md + "\n")
    if args.json_report:
        payload = {
            "months": args.months,
            "periods": periods,
            "method": "coef = month_value / window_peak, round to 1 decimal (ROUND_HALF_UP)",
            "keywords": rows,
        }
        with io.open(args.json_report, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    if not (args.stdout or args.output or args.json_report):
        print(md)


if __name__ == "__main__":
    main()
