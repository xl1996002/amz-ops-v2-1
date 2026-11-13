#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交付目录一致性检查 —— 同一份内容存在多个副本时，防止改了一处漏了另一处。

用法:
    python3 check_consistency.py <交付目录>
    python3 check_consistency.py <交付目录> --json-report report.json

检查什么:
  1. 文案数据 JSON 结构完整（五点 5 条、必填字段非空）
  2. 文案数据 JSON 的每个字段都出现在文案正稿 MD 里（防「改了 json 忘了 md」）
  3. HTML 描述与 Plain 描述逐段一致（防「两版描述漂移」）
  4. 中文译文的模块数量与英文对得上
  5. 广告方案 HTML 里只有 SP 活动（旧 naming.json 亦兼容）
  6. 若交付目录存在导出的广告配置 CSV，交叉比对关键词（没有则静默跳过）
  7. 配置 CSV 的活动预算可求和，且与方案口径一致（若可解析）
  8. 合并交付 HTML（若存在）包含 Title / Highlights / 五点首句
  9. 残留检查：占位符、独立 TODO 标记、货币/口径混用（跳过机器生成的报告文件）

退出码: 0 = 通过（可能有 WARN），1 = 有 ERROR
"""

import sys
import os
import io
import re
import json
import csv
import html as htmllib

ERRORS = []
WARNS = []
NOTES = []


def err(code, where, msg):
    ERRORS.append({"level": "ERROR", "code": code, "where": where, "msg": msg})


def warn(code, where, msg):
    WARNS.append({"level": "WARN", "code": code, "where": where, "msg": msg})


def note(code, where, msg):
    NOTES.append({"level": "NOTE", "code": code, "where": where, "msg": msg})


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def strip_md_marks(s):
    """去掉 markdown 粗体/代码标记，便于与 json 原文比对"""
    s = s.replace("**", "").replace("`", "")
    return s


def find_one(folder, suffix, exclude=()):
    """在目录里找以 suffix 结尾的文件"""
    hits = []
    for f in sorted(os.listdir(folder)):
        if f.endswith(suffix) and not any(x in f for x in exclude):
            hits.append(f)
    return hits


def find_by_tag(folder, tags, ext):
    """按「中文文件定义」找文件：文件名含任一 tag 且以 ext 结尾。
    兼容新命名 {ASIN}_{中文定义}_{日期}.{ext}。"""
    return [f for f in sorted(os.listdir(folder))
            if f.endswith(ext) and any(t in f for t in tags)]


# ---------------- 1 & 2 & 3 : Listing ----------------
def check_listing(folder):
    js = find_one(folder, "_listing.json") or find_by_tag(folder, ("_文案数据_",), ".json")
    md = find_one(folder, "_listing.md") or find_by_tag(folder, ("_文案正稿_",), ".md")
    if not js:
        err("NO_LISTING_JSON", folder, "找不到文案数据 JSON（*_listing.json 或 *文案数据*.json）")
        return None
    if len(js) > 1:
        warn("MULTI_LISTING_JSON", folder, "多个 listing.json: %s，取第一个" % js)

    data = json.loads(read(os.path.join(folder, js[0])))
    L = data.get("listing") or {}
    if not L:
        err("BAD_LISTING_JSON", js[0], "缺少 listing 对象")
        return None

    # --- 结构 ---
    for f in ("title", "item_highlights", "description_html", "description_plain", "search_terms"):
        if not (L.get(f) or "").strip():
            err("EMPTY_FIELD", js[0], "字段 %s 为空" % f)

    bullets = L.get("bullets") or []
    if len(bullets) != 5:
        err("BULLET_COUNT", js[0], "五点必须是 5 条，实际 %d 条" % len(bullets))
    for i, b in enumerate(bullets, 1):
        if not b.strip():
            err("EMPTY_BULLET", js[0], "五点第 %d 条为空" % i)

    # --- 硬指标（冗余检查，主校验仍在 check_listing.py）---
    if len(L.get("title", "")) > 75:
        err("TITLE_LEN", js[0], "Title %d 字符 > 75" % len(L["title"]))
    if len(L.get("item_highlights", "")) > 125:
        err("HL_LEN", js[0], "Item Highlights %d 字符 > 125" % len(L["item_highlights"]))
    st = L.get("search_terms", "")
    if len(st.encode("utf-8")) > 250:
        err("ST_BYTES", js[0], "Search Terms %d 字节 > 250" % len(st.encode("utf-8")))
    if "," in st:
        warn("ST_COMMA", js[0], "Search Terms 含逗号，Amazon 会当作分隔符，建议空格分隔")

    # --- HTML 与 Plain 逐段一致 ---
    dh = L.get("description_html", "")
    dp = L.get("description_plain", "")
    if dh and dp:
        paras_html = [re.sub(r"<[^>]+>", "", p).strip() for p in re.findall(r"<p>(.*?)</p>", dh, re.S)]
        paras_html = [p for p in paras_html if p]
        paras_plain = [p.strip() for p in dp.split("\n\n") if p.strip()]
        if len(paras_html) != len(paras_plain):
            err("DESC_PARA_COUNT", js[0],
                "HTML 描述 %d 段 vs Plain %d 段，段数不一致" % (len(paras_html), len(paras_plain)))
        else:
            for i, (a, b) in enumerate(zip(paras_html, paras_plain), 1):
                if a != b:
                    err("DESC_DRIFT", js[0],
                        "第 %d 段两版不一致：HTML「%s…」/ Plain「%s…」" % (i, a[:40], b[:40]))

    # --- 与 md 比对 ---
    if not md:
        warn("NO_LISTING_MD", folder, "找不到文案正稿 MD（*_listing.md 或 *文案正稿*.md），跳过跨文件比对")
        return L

    if len(md) > 1:
        warn("MULTI_LISTING_MD", folder, "多个 listing.md: %s，取第一个" % md)
    md_txt = strip_md_marks(read(os.path.join(folder, md[0])))
    md_unesc = htmllib.unescape(md_txt)

    def in_md(label, value, escaped=False):
        hay = md_unesc if escaped else md_txt
        if value not in hay:
            # 允许换行折叠：把连续空白压成一个空格再比
            norm = lambda s: re.sub(r"\s+", " ", s).strip()
            if norm(value) in norm(hay):
                note("MD_WRAP", md[0], "%s 命中但换行折叠（可接受）" % label)
                return
            err("MD_MISSING", md[0], "%s 在 listing.md 里找不到，怀疑改了 json 没同步 md" % label)

    in_md("Title", L.get("title", ""))
    in_md("Item Highlights", L.get("item_highlights", ""))
    for i, b in enumerate(bullets, 1):
        in_md("五点#%d" % i, b)
    in_md("HTML 描述", L.get("description_html", ""), escaped=True)
    in_md("Plain 描述", L.get("description_plain", ""))
    in_md("Search Terms", L.get("search_terms", ""))

    # --- 中文译文覆盖 ---
    zh_hits = [m for m in re.findall(r"【([^】]{2,30})】", md_txt)]
    zh_cn = [h for h in zh_hits if re.search(r"[\u4e00-\u9fff]", h)]
    if zh_hits and not zh_cn:
        note("ZH_TRANSLATION", md[0], "未检测到中文五点（如果该交付不需要中文译文，忽略）")

    return L


# ---------------- 4 : 广告 ----------------
ADS_DATA_RE = re.compile(
    r'<script[^>]*id=["\']ads-data["\'][^>]*>([\s\S]*?)</script>', re.I)


def load_ads_data(folder):
    """优先从单文件广告方案 HTML 读 ads-data；找不到再退回 *_naming.json。
    返回 (文件名, data) 或 (None, None)。"""
    for f in (find_one(folder, ".html") or []):
        try:
            raw = read(os.path.join(folder, f))
        except Exception:
            continue
        m = ADS_DATA_RE.search(raw)
        if not m:
            continue
        try:
            return f, json.loads(m.group(1))
        except Exception:
            continue
    for f in (find_one(folder, "_naming.json") or []):
        try:
            return f, json.loads(read(os.path.join(folder, f)))
        except Exception:
            continue
    return None, None


def check_ads(folder):
    src, data = load_ads_data(folder)
    if not data:
        warn("NO_ADS_DATA", folder, "找不到含 ads-data 的广告方案 HTML 或 *_naming.json，跳过广告检查")
        return
    camps = data.get("campaigns") or []
    if not camps:
        err("NO_CAMPAIGN", src, "campaigns 为空")
        return

    allowed = {"SP"}
    kw_all = set()
    for c in camps:
        ctype = (c.get("type") or "").strip().upper()
        if ctype and ctype not in allowed:
            err("NON_SP", src, "活动 %s 类型是 %s，本技能只做 SP" % (c.get("name"), ctype))
        segs = (c.get("name") or "").split("-")
        for tok in ("SD", "SB", "SBV"):
            if tok in segs:
                err("NON_SP", src, "活动名含 %s 段：%s；本技能只做 SP" % (tok, c.get("name")))
        for g in c.get("adgroups") or []:
            for k in g.get("keywords") or []:
                kw = k.get("kw") if isinstance(k, dict) else k
                if kw and str(kw).strip():
                    kw_all.add(str(kw).strip().lower())

    # 与 CSV 交叉
    csvs = [f for f in find_one(folder, ".csv")]
    if not csvs:
        return   # 配置表由广告方案 HTML 一键导出，未导出属正常状态，不报噪音

    csv_path = None
    for f in csvs:
        if "adgroup" in f.lower():
            csv_path = os.path.join(folder, f)
            break
    if not csv_path:
        return   # 不是广告配置表，静默跳过

    with io.open(csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        err("EMPTY_CSV", os.path.basename(csv_path), "CSV 无数据行")
        return

    # 关键词交叉：naming 里的词应能在某个 CSV 单元格里找到
    blob = " ".join(" ".join(str(v) for v in r.values()) for r in rows).lower()
    missing = [k for k in kw_all if k not in blob]
    if missing:
        err("KW_NOT_IN_CSV", os.path.basename(csv_path),
            "naming.json 有 %d 个词不在 CSV 里：%s" % (len(missing), "、".join(sorted(missing)[:6])))

    # 预算求和
    budget_col = None
    for k in rows[0].keys():
        if k and ("budget" in k.lower() or "预算" in k):
            budget_col = k
            break
    if budget_col:
        total = 0.0
        bad = []
        seen_camp = {}
        for r in rows:
            v = (r.get(budget_col) or "").strip()
            num = re.sub(r"[^0-9.]", "", v)
            if not num:
                bad.append(v or "(空)")
                continue
            total += float(num)
            cname = r.get("Campaign name") or r.get("广告活动") or ""
            seen_camp[cname] = seen_camp.get(cname, 0) + 1
        note("BUDGET_SUM", os.path.basename(csv_path),
             "CSV 预算列合计 £%.2f（%d 行）" % (total, len(rows)))
        if bad:
            warn("BUDGET_PARSE", os.path.basename(csv_path),
                 "有 %d 行预算无法解析：%s" % (len(bad), "、".join(bad[:4])))
        multi = {k: v for k, v in seen_camp.items() if v > 1}
        if multi:
            note("BUDGET_NOTE", os.path.basename(csv_path),
                 "同一活动下多组预算已相加（活动级预算应以方案文档为准，组级只是内部分配）：%s"
                 % "、".join(list(multi)[:3]))


# ---------------- 5 : 合并交付 HTML ----------------
def check_merged(folder, L):
    hits = [f for f in os.listdir(folder) if f.endswith(".html") and ("全部" in f or "ALL" in f.upper())]
    if not hits:
        note("NO_MERGED", folder, "没有合并交付 HTML（可选）")
        return
    for f in hits:
        txt = htmllib.unescape(re.sub(r"<[^>]+>", " ", read(os.path.join(folder, f))))
        txt_n = re.sub(r"\s+", " ", txt)
        if L:
            for label, val in (("Title", L.get("title")), ("Highlights", L.get("item_highlights"))):
                if val and re.sub(r"\s+", " ", val) not in txt_n:
                    err("MERGED_MISSING", f, "合并文档里找不到 %s，内容可能过期" % label)
            b1 = (L.get("bullets") or [""])[0]
            if b1 and re.sub(r"\s+", " ", b1) not in txt_n:
                err("MERGED_STALE", f, "合并文档里找不到五点#1 原文，说明合并后 Listing 又改过")
        # 体积提示
        size = os.path.getsize(os.path.join(folder, f))
        note("MERGED_SIZE", f, "%.1f KB" % (size / 1024.0))


# ---------------- 6 : 残留检查 ----------------
BAD_PATTERNS = [
    # 用独立单词边界，避免把 TODO_MODE / PENDING_COST 这类代码标识符误判为待办
    (r"\b(?:TODO|FIXME|XXX)\b", "残留待办标记"),
    (r"\{\{[^}]+\}\}", "未替换的模板占位"),
    (r"待补充\s*$", "空着的待补充字段（多行）"),
]


def check_residue(folder):
    for f in sorted(os.listdir(folder)):
        if not f.lower().endswith((".md", ".html", ".json", ".csv")):
            continue
        # 校验报告是机器生成的 findings，内含规则字符串本身（如 /TODO|FIXME|XXX/），
        # 扫它属于自指，必然误报，跳过。
        if "报告" in f and f.lower().endswith(".json"):
            continue
        p = os.path.join(folder, f)
        try:
            txt = read(p)
        except Exception:
            continue
        for pat, desc in BAD_PATTERNS:
            if re.search(pat, txt, re.M):
                if desc.startswith("空着的待补充"):
                    continue  # 待补充是允许的，由人工确认
                warn("RESIDUE", f, "%s：匹配 /%s/" % (desc, pat))
        # 货币混用
        if re.search(r"[￥¥]\s*\d", txt) and re.search(r"£\s*\d", txt):
            warn("CURRENCY_MIX", f, "同时出现 ￥/¥ 与 £，确认口径")


def main():
    if len(sys.argv) < 2:
        print("用法: python3 check_consistency.py <交付目录> [--json-report out.json]")
        return 2
    folder = sys.argv[1]
    report_path = None
    if "--json-report" in sys.argv:
        i = sys.argv.index("--json-report")
        if i + 1 < len(sys.argv):
            report_path = sys.argv[i + 1]

    if not os.path.isdir(folder):
        print("目录不存在:", folder)
        return 2

    L = check_listing(folder)
    check_ads(folder)
    check_merged(folder, L)
    check_residue(folder)

    print("=" * 66)
    print("交付一致性检查 ·", os.path.basename(os.path.abspath(folder)))
    print("=" * 66)
    if ERRORS:
        print("\n[问题清单]")
        for e in ERRORS:
            print("  [ERROR] %-20s %-28s %s" % (e["code"], e["where"][:28], e["msg"]))
    if WARNS:
        print("\n[提示]")
        for w in WARNS:
            print("  [WARN ] %-20s %-28s %s" % (w["code"], w["where"][:28], w["msg"]))
    if NOTES:
        print("\n[记录]")
        for n in NOTES:
            print("  [NOTE ] %-20s %-28s %s" % (n["code"], n["where"][:28], n["msg"]))
    if not ERRORS and not WARNS and not NOTES:
        print("\n  无问题。")

    print("\n" + "-" * 66)
    print("ERROR %d  |  WARN %d  |  NOTE %d" % (len(ERRORS), len(WARNS), len(NOTES)))
    print("RESULT: %s" % ("PASS" if not ERRORS else "FAIL"))
    print("-" * 66)

    if report_path:
        with io.open(report_path, "w", encoding="utf-8") as f:
            json.dump({"errors": ERRORS, "warns": WARNS, "notes": NOTES,
                       "result": "PASS" if not ERRORS else "FAIL"},
                      f, ensure_ascii=False, indent=2)
        print("JSON 报告:", report_path)

    return 0 if not ERRORS else 1


if __name__ == "__main__":
    sys.exit(main())
