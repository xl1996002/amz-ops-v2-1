# amazon-ops-v2-1 安装说明（换机部署）

版本：V2.1 ｜ 打包日期：2026-11-13 ｜ 自包含，零第三方依赖

## 1. 环境要求

| 项目 | 要求 | 说明 |
|---|---|---|
| WorkBuddy | 支持 Agent Skills | 技能目录能自动加载即可 |
| Python | 3.8+，**不需要 pip 装任何包** | 三个校验脚本只用标准库（sys / os / io / re / json / csv / argparse） |
| Sorftime MCP 连接器 | 取数必需 | 不接也能写文案，但第 1 步的类目/关键词/竞品数据取不到，只能人工给数据 |
| 浏览器 | 任意现代浏览器 | 打开 `assets/rewrite-checklist.html` 逐项打勾用 |

## 2. 安装（三步）

**第一步：放技能目录**

解压后得到 `amazon-ops-v2-1/` 整个文件夹，直接放进：

- Windows：`C:\Users\<你的用户名>\.workbuddy\skills\`
- macOS / Linux：`~/.workbuddy/skills/`

放完应该是 `.../skills/amazon-ops-v2-1/SKILL.md` 这个层级，**不要多套一层目录**（不要出现 `amazon-ops-v2-1/amazon-ops-v2-1/SKILL.md`）。

**第二步：重启 WorkBuddy**

技能列表在启动时扫描，重启后左侧技能面板里会出现 `amazon-ops-v2-1`（显示名 Amazon-ops-v2.1）。

**第三步：验证安装**

打开终端，`cd` 进技能目录，跑两条自测，都出现 `RESULT: PASS` 即安装正确：

```bash
python3 scripts/check_listing.py assets/selftest-listing.json
python3 scripts/check_ads_naming.py assets/selftest-ads.json
```

Windows 下如果 `python3` 不可用，把命令里的 `python3` 换成 `python` 或 `py -3` 即可。

## 3. 目录结构

```
amazon-ops-v2-1/
├── SKILL.md                      主流程（九步 + 铁律 + 输出范围）
├── INSTALL.md                    本文件
├── references/
│   ├── 01-listing-spec.md        《第四版》Listing 全套规范
│   ├── 02-ads-naming-spec.md     《广告管理规范V1.0》命名与结构
│   ├── 03-prompt-workflow.md     六步提示词流程
│   ├── 04-sorftime-data.md       Sorftime 字段口径与数据陷阱
│   ├── 05-visual-callout-spec.md 图示详情 / 引线标注规范
│   ├── 06-copy-placement.md      卖点表达落点（四步法 / 三种句式 / 四问自检）
│   └── 07-field-notes.md         实操场记（十节，含踩过的坑）
├── scripts/
│   ├── check_listing.py          Listing 机检（含 ABSOLUTE_BANNED 禁用词）
│   ├── check_ads_naming.py       广告命名校验（仅 SP）
│   └── check_consistency.py      多副本一致性校验
└── assets/
    ├── rewrite-checklist.html    卖点改写检查清单（浏览器打开即用）
    ├── listing-output-template.md
    ├── ads-plan-template.html
    ├── ads-structure-template.html
    ├── full-delivery-template.html
    ├── callout-layout-template.svg
    ├── adgroup-config-fields.csv
    └── selftest-listing.json / selftest-ads.json
```

## 4. 包里**没有**的东西（刻意不打进来）

| 缺的东西 | 影响 | 怎么办 |
|---|---|---|
| 三份原始 Word 规范（第四版 / 广告管理规范V1.0 / 广告提示词草稿） | 只是规范原文，技能里已有转换后的 md，不影响执行 | 需要留档就从原机器拷 docx |
| 项目数据（事实库、ERP、`_API流水线`） | 技能不依赖；自己带 ASIN 和数据即可 | 需要历史产物就单独拷项目目录 |
| Sorftime 账号与密钥 | 无 | 新机器上重新连 Sorftime MCP 连接器，**不要把密钥写进技能或对话** |

`references/07-field-notes.md` 里出现的 `D:\亚马逊运营模型\...` 是原项目机的路径备注，换机后按提示改成自己机器的路径或直接忽略，不影响技能运行。

## 5. 用法速查

触发词：「跑全套」「按第四版规范写页面」「重写亚马逊链接」「要能直接复制的 listing」「做 A+ 图和文案」。

默认产出：数据诊断 → 13 段 Listing 文案 → **可复制页**（每字段一个复制按钮，五点每条一个）→ 作图提示词（主副图 + A+ 合并成一份 MD）→ 合并单文件交付。

**广告方案默认不输出**，只有明确说「要广告方案 / 广告部分 / 广告结构」时才出，且只做 SP。
