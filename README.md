# 导入说明（先看这个）

**压缩包**：`amazon-ops-v2-1_V2.1_20261113.zip`（103 KB，22 个文件）
**内容**：整套 `amazon-ops-v2-1` 技能，自包含，零第三方依赖

## 三步装好

1. **解压** → 得到 `amazon-ops-v2-1/` 文件夹
2. **放进去** → `C:\Users\<你的用户名>\.workbuddy\skills\`（Mac/Linux 是 `~/.workbuddy/skills/`）
   - 放完必须是 `...\skills\amazon-ops-v2-1\SKILL.md` 这个层级，**别多套一层**
3. **重启 WorkBuddy** → 技能面板出现 `amazon-ops-v2-1`（显示名 Amazon-ops-v2.1）即成功

检验（终端进技能目录跑）：

```bash
python3 scripts/check_listing.py assets/selftest-listing.json
python3 scripts/check_ads_naming.py assets/selftest-ads.json
```

两条都出 `RESULT: PASS` 就是装对了。Windows 若 `python3` 不认，换 `python` 或 `py -3`。

## 新电脑还需要自己配一件事

**Sorftime MCP 连接器**——技能靠它取 Amazon 类目、关键词、竞品数据。不接也写得动文案，但第 1 步的数据诊断会缺料，得人工把数据给它。

⚠️ 密钥重新在你自己的机器上配，别写进技能文件、别贴进对话。

## 包里没有的（刻意不打）

- 三份原始 Word 规范 → 已转成 `references/01~03` 的 md，够用；要留档再从旧机器拷 docx
- 项目数据（事实库 / ERP / `_API流水线`）→ 技能不依赖，需要历史产物单独拷
- `references/07-field-notes.md` 里的 `D:\亚马逊运营模型\...` 是旧机器路径备注，改掉或忽略都不影响运行

## 用法

说「跑全套」「重写亚马逊链接」「要能直接复制的 listing」即可。

默认产出：数据诊断 → 13 段文案 → 可复制页（五点每条一个按钮）→ 作图提示词（主副图 + A+ 合并一份 MD）→ 合并单文件。

**广告方案默认不出**，明确要「广告方案 / 广告部分 / 广告结构」才出，且只做 SP。

---

详细说明见包内 `amazon-ops-v2-1/INSTALL.md`。
