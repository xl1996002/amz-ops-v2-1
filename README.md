# Amazon Ops v2.1 技能包

说「跑全套」「重写亚马逊链接」「要能直接复制的 listing」即可。

**默认产出**：数据诊断（含季节性系数表）→ 13 段文案 → 可复制页（五点每条一个按钮）→ 作图提示词（主副图 + A+ 合并一份 MD）→ 合并单文件。

**广告方案默认不出**，明确要「广告方案 / 广告部分 / 广告结构」才出，且只做 SP。

## 导入

1. 下载/克隆本仓库，把 `amazon-ops-v2-1/` 整个文件夹放到 `C:\Users\<用户名>\.workbuddy\skills\` 下。
2. 层级必须是 `...\skills\amazon-ops-v2-1\SKILL.md`，不要多套一层。
3. 重启 WorkBuddy，技能面板出现 `Amazon-ops-v2.1` 即成功。

技能自带零依赖 Python 脚本（仅标准库），无需 `pip install`；Sorftime 取数需要在新机器上自行连接 Sorftime MCP，密钥不要写进仓库。

## 装什么

- **推荐**：直接用 `amazon-ops-v2-1/` 目录——已与本机最新版逐字节同步（2026-11-27，含季节性系数脚本）。
- 根目录的 `amazon-ops-v2-1_V2.1_20261113.zip` 是 **11-13 的历史存档**，不含 11-27 新增的季节性系数功能，不要用来导入。

## 2026-11-27 更新：季节性系数

数据诊断第四节必须输出归一化系数表：`keyword_trend(type=2)` 取最近 12 个完整月，最高月 = 1.0，其余 = 该月搜索量 ÷ 峰值四舍五入保留 1 位小数。

- 算法与红线：`references/04-sorftime-data.md` 的「二·补」
- 复算脚本：`scripts/seasonality_index.py`（无第三方依赖）
- 自测样例：`assets/selftest-seasonality.json`

系数只用于淡旺季判断，**不写进 Listing 文案**。

## 自测

```bash
cd amazon-ops-v2-1
python3 scripts/check_listing.py assets/selftest-listing.json
python3 scripts/check_ads_naming.py assets/selftest-ads.json
python3 scripts/seasonality_index.py --input assets/selftest-seasonality.json --months 6 --stdout
```

三个都应 PASS / 输出 1.0/0.8/0.5/0.3/0.2/0.1。
