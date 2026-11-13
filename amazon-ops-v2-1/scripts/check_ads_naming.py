#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广告命名与配置校验器（零依赖，纯标准库）
依据：《广告管理规范V1.0》（references/02-ads-naming-spec.md）

用法:
    python3 check_ads_naming.py ads-plan.html
    python3 check_ads_naming.py ads-plan.html --json-report report.json
    python3 check_ads_naming.py naming.json          # 兼容旧输入（等价 JSON）

输入优先用「单文件广告方案 HTML」——里面 <script id="ads-data" type="application/json">
区块就是校验数据。广告交付物只有一个 HTML，不另出 CSV/JSON。

输入 JSON:

{
  "operator": "Leo",
  "site": "UK",
  "weeks_since_launch": 9,                 // 可选；仅作记录（只做 SP，不再用于闸门判定）
  "portfolios": [
    {"name": "Leo-A0001"}
  ],
  "campaigns": [
    {
      "name": "Leo-A0001A-SP-MT-KT-EX-[LongTail]",
      "portfolio": "Leo-A0001",
      "type": "SP",                        // SP / SD / SB / SBV
      "identifier_kind": "sku",            // 可选：sku / asin，用于校验申报与实际是否一致
      "adgroups": [
        {
          "name": "Leo-A0001A-SP-MT-KT-EX-[LongTail]-[Defend]",
          "tier": "longtail",              // head / mid / longtail，可省略
          "keywords": ["folding gymnastics mat"],
          "asins": [],
          "match": "exact"                 // exact / phrase / broad，可省略
        }
      ]
    }
  ]
}

命名第二段标识符规则（用户 2026-10-28）：有子 SKU 就用子 SKU；没有 SKU 就用子 ASIN。
不带 SKU 的（竞品链接、未建编码、代运营未接 ERP）直接写 ASIN，例如 Leo-B0GTP1LW7S-SP-AT。

广告类型范围（用户 2026-10-28 17:13）：只做 SP。type / 命名里出现 SD、SB、SBV 一律判 ERROR（NON_SP）。

退出码: 0 = 无 ERROR；1 = 存在 ERROR；2 = 输入错误
"""

import argparse
import json
import re
import sys

# 规范 §5.3 的 25 条缩写（原文未定义 PT，故不在表内 → 出现即提示）
ABBREV = {
    "SP", "AT", "MT", "KT", "BR", "PH", "EX", "PAT", "CAT", "IP",
    "SD", "PC", "AUDT", "CT", "AA", "VR", "PR",
    "SB", "SBV", "PD", "SS", "AS", "NLP", "VRC", "VRP",
}
AD_TYPES = {"SP", "SD", "SB", "SBV"}
# 本技能只做 SP（用户 2026-10-28 17:13）；其余类型用于识别后判错，不是允许项
ALLOWED_TYPES = {"SP"}

# 组内关键词上限（规范 §5.6）—— 这是最大限制，不是最优值
KW_LIMIT = {"head": 5, "mid": 10, "longtail": 50}
KW_LABEL = {"head": "大词", "mid": "中词", "longtail": "长尾词"}

ASCII_RE = re.compile(r"^[\x20-\x7E]+$")
NON_ASCII_RE = re.compile(r"[^\x20-\x7E]")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")

# 第二段标识符：有 SKU 用 SKU，没有 SKU 用 ASIN（用户 2026-10-28 口径）
ASIN_RE = re.compile(r"^B0[A-Z0-9]{8}$")
SKU_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._]*$")
PLACEHOLDER_RE = re.compile(
    r"^[<{\[].*[>}\]]$|^(X{4,}|TBD|TODO|PLACEHOLDER|SKU|ASIN|SUBASIN|SUBSKU)$", re.I)

# 单文件广告方案 HTML 里的数据区块
ADS_DATA_RE = re.compile(
    r'<script[^>]*id=["\']ads-data["\'][^>]*>([\s\S]*?)</script>', re.I)


def load_input(path):
    """读 .html 时从 <script id="ads-data"> 抽 JSON；其余按 JSON 解析。"""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    if path.lower().endswith((".html", ".htm")):
        m = ADS_DATA_RE.search(raw)
        if not m:
            raise ValueError('HTML 里找不到 <script id="ads-data" type="application/json"> 区块')
        return json.loads(m.group(1))
    return json.loads(raw)


def classify_identifier(token):
    """返回 (kind, note)：kind ∈ asin / sku / placeholder / unknown"""
    if not token:
        return "unknown", "缺失"
    if PLACEHOLDER_RE.match(token):
        return "placeholder", "占位符，交付前必须换成真实编号"
    if ASIN_RE.match(token):
        return "asin", "ASIN 形态"
    if SKU_RE.match(token) and len(token) >= 3 and not token.isdigit():
        return "sku", "SKU 形态"
    return "unknown", "既不像 ASIN（B0XXXXXXXX）也不像 SKU"


class Report:
    def __init__(self):
        self.issues = []
        self.metrics = []

    def err(self, code, scope, msg):
        self.issues.append(("ERROR", code, scope, msg))

    def warn(self, code, scope, msg):
        self.issues.append(("WARN", code, scope, msg))

    def note(self, code, scope, msg):
        self.issues.append(("INFO", code, scope, msg))

    def metric(self, name, value, limit=None, ok=None):
        self.metrics.append((name, value, limit, ok))

    def counts(self):
        e = sum(1 for i in self.issues if i[0] == "ERROR")
        w = sum(1 for i in self.issues if i[0] == "WARN")
        return e, w


def check_ascii(name, scope, rep):
    """规范 §二：所有命名中都只能使用英文，不可以出现中文。"""
    if not name:
        rep.err("NAME_EMPTY", scope, "名称为空")
        return False
    bad = NON_ASCII_RE.findall(name)
    if not bad:
        return True
    uniq = sorted(set(bad))
    shown = " ".join(repr(c) for c in uniq[:8])
    hint = []
    if CJK_RE.search(name):
        hint.append("含中文 → 自定义内容需转英文")
    if "【" in name or "】" in name:
        hint.append("含 CJK 括号【】→ 改成 ASCII 的 [ ]")
    rep.err("NON_ASCII", scope,
            "出现非 ASCII 字符 %s%s" % (shown, ("；" + "；".join(hint)) if hint else ""))
    return False


def split_segments(name):
    """按第一个 [ 切开：返回 (主体段 list, 标签段 list)"""
    idx = name.find("[")
    if idx == -1:
        return [s for s in name.split("-") if s], []
    head = name[:idx].rstrip("-")
    tail = name[idx:]
    tags = re.findall(r"\[[^\]]*\]", tail)
    return [s for s in head.split("-") if s], tags


def check_campaign(camp, operator, rep, portfolios):
    name = (camp.get("name") or "").strip()
    scope = "活动 " + (name or "<空>")
    if not check_ascii(name, scope, rep):
        return

    segments, tags = split_segments(name)

    # 运营英文名前缀
    if operator:
        if not name.startswith(operator + "-"):
            rep.err("PREFIX", scope,
                    "活动名未以「%s-」开头（规范 §5.2：英文名-子SKU/子ASIN-投放形式缩写-[自定义]）" % operator)
        rep.metric("活动名段数", len(segments), ">=4", len(segments) >= 4)
    else:
        rep.warn("NO_OPERATOR", scope, "未提供 operator，跳过前缀校验")

    # 第二段标识符：有 SKU 用 SKU，没有 SKU 用 ASIN（用户 2026-10-28 口径）
    ident = segments[1] if len(segments) > 1 else ""
    kind, kind_note = classify_identifier(ident)
    rep.metric("标识符 %s" % (ident or "<空>"),
               {"asin": "ASIN", "sku": "SKU", "placeholder": "占位符", "unknown": "无法判定"}[kind],
               "SKU 优先/无则 ASIN", kind in ("sku", "asin"))
    if kind == "placeholder":
        rep.warn("IDENT_PLACEHOLDER", scope,
                 "标识符「%s」是占位符，交付前必须换成真实 SKU，无 SKU 则用子 ASIN" % ident)
    elif kind == "unknown":
        rep.warn("IDENT_UNKNOWN", scope,
                 "标识符「%s」%s；命名规则要求子 SKU，没有 SKU 就用子 ASIN" % (ident, kind_note))
    else:
        want = (camp.get("identifier_kind") or "").strip().lower()
        if want in ("sku", "asin") and want != kind:
            rep.warn("IDENT_MISMATCH", scope,
                     "申报标识符类型为 %s，但命名里「%s」是 %s 形态" % (want.upper(), ident, kind.upper()))

    # 广告类型
    ctype = (camp.get("type") or "").strip().upper()
    if ctype and ctype not in AD_TYPES:
        rep.err("TYPE", scope, "广告类型「%s」不在 SP/SD/SB/SBV 之内" % ctype)
    type_pos = next((i for i, s in enumerate(segments) if s in AD_TYPES), -1)
    if type_pos == -1:
        rep.err("NO_TYPE", scope,
                "找不到广告类型缩写（SP/SD/SB/SBV），命名不符合 §5.2")
        return
    if ctype and segments[type_pos] != ctype:
        rep.warn("TYPE_MISMATCH", scope,
                 "命名里的类型「%s」与字段 type「%s」不一致" % (segments[type_pos], ctype))

    # 只做 SP（用户 2026-10-28 17:13 口径）：SD / SB / SBV 一律判 ERROR
    if segments[type_pos] not in ALLOWED_TYPES:
        rep.err("NON_SP", scope,
                "广告类型是「%s」，本技能只做 SP（商品广告）；SD / SB / SBV 一律不建"
                % segments[type_pos])

    # 投放形式缩写 3-5 段（规范：“一般分为 3-5 段”）
    target_segs = segments[type_pos:]
    rep.metric("投放形式段数", len(target_segs), "3-5", 3 <= len(target_segs) <= 5)
    if len(target_segs) < 3:
        rep.warn("SEG_SHORT", scope,
                 "投放形式仅 %d 段（%s）；规范称「一般 3-5 段」，SP-AT / SD-AT 这类简写在常用组合里存在，确认是否可接受"
                 % (len(target_segs), "-".join(target_segs)))
    if len(target_segs) > 5:
        rep.err("SEG_LONG", scope,
                "投放形式 %d 段超过 5 段上限（%s）" % (len(target_segs), "-".join(target_segs)))

    unknown = [s for s in target_segs if s not in ABBREV]
    if unknown:
        rep.warn("ABBREV", scope,
                 "缩写不在 §5.3 表内：%s（原文未定义则照写，不要自行解释）" % ", ".join(unknown))

    # 自定义标签必须是 ASCII 方括号
    if "【" in name or "】" in name:
        rep.err("BRACKET", scope, "自定义内容须用 ASCII 的 [ ]，不能用【】")
    for t in tags:
        inner = t[1:-1]
        if CJK_RE.search(inner):
            rep.err("TAG_CJK", scope, "自定义标签含中文：%s" % t)

    # 组合归属
    pid = (camp.get("portfolio") or "").strip()
    if pid:
        if pid not in portfolios:
            rep.err("PORTFOLIO_MISSING", scope, "引用的广告组合「%s」不在 portfolios 列表内" % pid)
    else:
        rep.warn("NO_PORTFOLIO", scope, "未指定所属广告组合")

    # 16 周闸门：只做 SP 的口径下不再判定（SD/SB 已被 NON_SP 拦下），此处不报警

    # 广告组
    groups = camp.get("adgroups") or []
    if not groups:
        rep.warn("NO_ADGROUP", scope, "该活动没有广告组")
    rep.metric("广告组数", len(groups), "一般 1", len(groups) == 1)
    if len(groups) > 1:
        rep.note("MULTI_GROUP", scope,
                 "%d 个广告组：规范要求「一般一个活动一个组」，多组时须在投放形式后加自定义说明" % len(groups))

    seen = set()
    for g in groups:
        gname = (g.get("name") or "").strip()
        gs = "组 " + (gname or "<空>")
        if not check_ascii(gname, gs, rep):
            continue
        if gname in seen:
            rep.err("DUP_GROUP", gs, "广告组名重复")
        seen.add(gname)
        if not gname.startswith(name):
            rep.err("GROUP_PREFIX", gs,
                    "组名未以活动名「%s」开头（规范 §5.5：组名 = 活动名-[自定义分类]）" % name)
        else:
            suffix = gname[len(name):]
            if suffix and not re.fullmatch(r"(-\[[^\]]*\])+", suffix):
                rep.warn("GROUP_SUFFIX", gs,
                         "活动名之后的多余部分「%s」不是 -[自定义分类] 形式" % suffix)

        tier = (g.get("tier") or "").strip().lower()
        is_auto = (camp.get("targeting") or "").strip().lower() == "auto"
        kws = [k for k in (g.get("keywords") or []) if str(k).strip()]
        asins = [a for a in (g.get("asins") or []) if str(a).strip()]
        if tier:
            lim = KW_LIMIT.get(tier)
            if lim is None:
                rep.warn("TIER", gs, "tier「%s」无效，应为 head / mid / longtail" % tier)
            else:
                rep.metric("关键词数(%s)" % KW_LABEL[tier], len(kws), lim, len(kws) <= lim)
                if len(kws) > lim:
                    rep.err("KW_LIMIT", gs,
                            "%s %d 个超过上限 %d（规范 §5.6）" % (KW_LABEL[tier], len(kws), lim))
                elif len(kws) == lim and lim > 5:
                    rep.warn("KW_AT_LIMIT", gs,
                             "已顶到 %s 上限 %d 个；原文注明这是最大限制、不是最优，越少越好管" % (KW_LABEL[tier], lim))
        elif is_auto:
            pass  # 自动投放组没有关键词，不判 tier
        else:
            rep.warn("NO_TIER", gs, "未提供 tier，无法判定关键词上限（head/mid/longtail）")
        if not kws and not asins and not is_auto:
            rep.warn("EMPTY_TARGET", gs, "既无关键词也无定向 ASIN")
        for a in asins:
            if not re.fullmatch(r"B0[A-Z0-9]{8}", str(a).strip()):
                rep.warn("ASIN_FMT", gs, "定向值「%s」不像标准 ASIN（应形如 B0XXXXXXXX）" % a)
        mt = (g.get("match") or "").strip().lower()
        if mt and mt not in ("exact", "phrase", "broad"):
            rep.warn("MATCH", gs, "match「%s」应为 exact / phrase / broad" % mt)


def render(data, rep):
    out = ["=" * 70, "广告命名与配置校验    运营: %s   站点: %s"
           % (data.get("operator") or "-", data.get("site") or "-"), "=" * 70]
    if rep.metrics:
        out.append("\n[指标]")
        for name, val, limit, ok in rep.metrics:
            mark = " " if ok is None else ("OK " if ok else "!! ")
            lim = "" if limit in (None, "") else "  (限 %s)" % limit
            out.append("  %s%-20s %s%s" % (mark, name, val, lim))
    if rep.issues:
        out.append("\n[问题清单]")
        order = {"ERROR": 0, "WARN": 1, "INFO": 2}
        for lv, code, scope, msg in sorted(rep.issues, key=lambda x: order[x[0]]):
            out.append("  [%s] %-16s %s\n        %s" % (lv, code, scope, msg))
    else:
        out.append("\n[问题清单]\n  无")
    e, w = rep.counts()
    out += ["\n" + "-" * 70, "ERROR %d  |  WARN %d" % (e, w),
            "RESULT: %s" % ("PASS" if e == 0 else "FAIL"), "-" * 70]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="广告命名与配置校验")
    ap.add_argument("input")
    ap.add_argument("--json-report")
    args = ap.parse_args()

    try:
        data = load_input(args.input)
    except Exception as e:
        sys.stderr.write("读取输入失败: %s\n" % e)
        return 2

    ports = [p.get("name") for p in (data.get("portfolios") or []) if p.get("name")]
    campaigns = data.get("campaigns") or []
    if not campaigns:
        sys.stderr.write("输入中缺少 campaigns\n")
        return 2

    rep = Report()
    op = (data.get("operator") or "").strip()

    # 组合名本身也要纯 ASCII + 运营名前缀
    seen_p = set()
    for p in ports:
        if not check_ascii(p, "组合 " + p, rep):
            continue
        if p in seen_p:
            rep.err("DUP_PORTFOLIO", "组合 " + p, "广告组合名重复")
        seen_p.add(p)
        if op and not p.startswith(op + "-"):
            rep.err("PREFIX", "组合 " + p, "组合名未以「%s-」开头（规范 §5.1）" % op)

    seen_c = set()
    for camp in campaigns:
        name = (camp.get("name") or "").strip()
        if name in seen_c:
            rep.err("DUP_CAMPAIGN", "活动 " + name, "活动名重复")
        seen_c.add(name)
        if "weeks_since_launch" not in camp and data.get("weeks_since_launch") is not None:
            camp["weeks_since_launch"] = data["weeks_since_launch"]
        check_campaign(camp, op, rep, set(ports))

    print(render(data, rep))

    if args.json_report:
        with open(args.json_report, "w", encoding="utf-8") as f:
            json.dump({
                "operator": op,
                "metrics": [{"name": n, "value": v, "limit": l, "pass": o}
                            for n, v, l, o in rep.metrics],
                "issues": [{"level": lv, "code": c, "scope": s, "message": m}
                           for lv, c, s, m in rep.issues],
                "result": "PASS" if rep.counts()[0] == 0 else "FAIL",
            }, f, ensure_ascii=False, indent=2)
        print("JSON 报告: %s" % args.json_report)

    return 0 if rep.counts()[0] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
