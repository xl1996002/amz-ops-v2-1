# Listing 实操场记（实测坑总表）

> 从原 `amazon-listing-copy-fourth-edition` 技能合并而来。全部条目都带实测出处，不是推测。
> 遇到本文没写的情况：先按「不编造」处理（标待确认），别套用相近案例的数字。

## 一、通用常见坑

- 描述两版手写必然不一致 → 只存段落数组，HTML 版由 `p` 包裹生成。
- 改 Title 会连锁影响 Highlights（零重复约束）→ 改完必须重跑校验。
- 「6 months plus」这类长尾词难整句塞入 → 用词组合覆盖，在核对表标注「词组合覆盖」。
- `foldable` 是大词但不属于本品（固定框）→ 不埋，改打 `footrest` 等真实差异词。
- **按落点改写时最容易升级成绝对断言**：`supports up to 150 kg` 被改成 `won't bend under any weight`、`has a sealed base` 被改成 `no leak ever`。改写只允许换落点，不允许抬高强度 → 一律退回带条件的原表述，且已由 `check_listing.py` 的 `ABSOLUTE_BANNED` 自动拦。

## 二、Sorftime 取数口径坑（2026-10-28 实测）

- `category_products` 对**同一父体的多个子 ASIN 返回相同销量**，直接求和会翻倍 → 先按 `parent_asin` 去重再算份额。
- 该接口的 `delivery_type` 恒为 null、`days_on_shelf` 缺字段、`peak_season` 恒为 `--` → 上架节奏/履约方式分析别用它，改用 `product_detail`。
- `product_detail` 的 `profit` / `profit_rate` 可能返回「利润=售价、利润率 100%」（佣金与配送费为 0），**不可采信**，不得据此反推毛利率、出价或利润结论。
- `product_detail` 的 `monthly_sales_volume` 与 `yearly_sales_volume` 常差 2 倍以上（当期估算 vs 滚动累计）→ 销量结论按区间表述，并提示以客户后台为准。
- `product_customers_say` 的 site 枚举**不含 GB**；`product_reviews` 在 GB 站点可能返回 No reviews found → VOC 改用类目口碑/关键词意图替代。
- `keyword_detail` 对部分长尾词（如 `folding gymnastics mat`）返回 No data → 改用 `keyword_extends` 取月搜与推荐 CPC。
- 父级节点的 `conversion_rate` 常为 0（无数据）；取最贴近的子节点，并标明口径。
- `product_traffic_terms` 只返回真实有曝光的词（常见仅 5–10 条），是判断「有没有开广告、词覆盖够不够」的快捷体检口径。
- **`product_traffic_terms` 返回「No relevant data」**不等于没数据可挖，但通常意味着这条链接近 3 页没有可反查的曝光词（也可能是采集缺口）。写法：「未返回可反查的曝光词」，**不要断言**「没有广告」或「没有流量」。新链接（100 天上下、月销个位数）几乎必现此情况。

## 三、变体与校验坑（2026-11-02 B0HPB3SQRJ 实测）

- **有颜色变体时，「颜色/饰面」是全字段禁忌**：不只是 Title，Highlights / 五点 / 描述 / Search Terms 都是父体共享字段，写 `bamboo`、`solid wood`、`wood-effect` 会让其余颜色子体接到错配流量。先用 `product_variations` 确认变体维度，再决定能不能写材质描述。
- 颜色变体存在 ≠ 材质可写。例：7 个 Colour Name（Pink/Black/Blue…）说明桌面是同一块板做不同饰面，「Bamboo」是颜色名不是材质，只能写中性表述（`60 x 45 cm top`）。
- **变体维度填错字段很常见**：曾见层数（Single Layer / Double Layer）被填进 `Colour` 字段。父体共享字段一律不写层数；后台建议把属性迁到 `Style` 主题。
- **标题选词要看同口径集中度**：`keyword_detail` 的 `share_click_rate`（前 3 页 Top3 点击占比）与 `category_keywords` 的 `search_result_top3_pages_top3_product_sales_share`（销量占比）**不是同一指标，不能互相比较**。跨词比较必须取同一字段。
- Title Case 校验要放行**单位与乘号**（`cm` `mm` `kg` `x` `in` 等），否则 `60 x 45 cm` 会误报失败。
- 「长尾词 80% 覆盖」的脚本判定要含**词组合覆盖**：整句难嵌入时，只要各组成词分散命中即可算覆盖，且应忽略 `that/for/and/the/of` 等虚词，否则会假性不达标（例：`camping tables that fold up` 只因缺 `that` 被判未覆盖）。
- 新链接（0 评论、无类目）常有 `product_detail` 返回 `category: ["",""]` → 类目要靠 `category_name_search` 反查，不能依赖 ASIN 自带节点。
- **两个脚本的覆盖口径不同**：`check_listing.py` 按**整句短语**判长尾覆盖；项目 `_check*.js` 认**词组合覆盖**。同一批词前者可能 4/4、后者 10/10。为过 Python 闸门，`long_tail` 列表只放能整句覆盖的词，其余在 `keyword_notes` 说明。

## 四、德语站（DE）落地要点（2026-11-04 B0DT4HNZJ3 实测）

- **德语不适用英文 Title Case**。德语只大写名词，形容词（`höhenverstellbar`）、介词、冠词一律小写才是正确写法。校验脚本要改判为「首词大写 + 无全大写词 + 无特殊符号」，不要硬套首字母全大写。
- **分写搜索是常态**：`foto hintergrund ständer`(3,074) / `hintergrund ständer`(5,136) / `fotohintergrund`(12,280) 是三个独立词，标题里写成 `Foto Hintergrund Ständer … Fotohintergrund` 一串多词可以同时命中，比全用复合词更划算。改写成 `Hintergrundfotografie` 这类复合词会直接丢掉分写词的精确匹配。
- **小数点是逗号**：`2,1 kg`、`78,5 cm`。数值白名单与正则都要按 `\d+(?:[.,]\d+)?` 处理，Highlights 拆分也不能在 `2,1` 的逗号处断开（用 `/,(?!\d)/`）。
- **尺寸是变体维度时要慎重**：父体下若同时挂着 2x2m / 2x3m 两个子体，标题与五点里的 `300 cm`、`2x3 m` 只对其中一个成立；必须明确标注「另一子体需单独改数字」，否则货不对板。
- **DE 类目退货率普遍高于 UK**（Aufhängungen 14.69%）。文案要主动写「不适合什么」——在描述第三段用一句限制换退货率，比多加一个卖点更有价值。
- 老链接常见 **Unicode 花体字**（`𝗩𝗶𝗲𝗹𝘀𝗲𝗶𝘁𝗶𝗴 𝗲𝗶𝗻𝘀𝗲𝘁𝘇𝗯𝗮𝗿`）做伪粗体，属亚马逊样式违规，发现即建议替换成标准字符。

## 五、改写前先证伪原链接的功能声明（2026-11-04 B0FG7B5VLC 实测，重要）

老链接的标题里常写着实物没有的功能。这次一条折叠床桌写着 **"with Drawer"**（实物无抽屉）和 **"Adjustable Height"**（腿高固定、只有面板可调倾角）。两处都是货不对板，且都能直接换来 1 星。

- **做法**：把主图/折叠图下载后**放大裁切**（python PIL：`im.crop(...).resize(..., Image.LANCZOS)`），确认每一处疑似结构件是什么。这次那根金属丝是 5 档倾角的支撑杆，不是抽屉拉手；托盘上的圆孔是杯托，不是储物格。只看缩略图会判断错。
- **校对清单**（逐条对着标题打勾）：drawer / storage / adjustable height / adjustable angle / foldable / 防水等级 / 承重。凡实物不支持的一律从新文案删除，并在报告「未闭合项」里单列。
- 校验脚本里加两条固定检查：`无「高度可调」表述`、`无「抽屉/储物格」表述`，正则扫 `adjustable height|height adjustable|drawer|storage compartment`。
- **同一父体两个子体结构可能不同**（例：单层＝顶板＋1 篮，双层＝2 个独立篮）→ 父体共享字段只能写共性，结构差异交给子体与图片。

## 六、尺寸图数字自相矛盾时怎么办

案例：尺寸图同时标了整体 `73`、面板 `37`、间隔 `18`、托板 `32`，但 37+18+32=87 ≠ 73。

- **原则**：文案只写**总数**（73cm / 折叠 55×32cm / 腿高 25cm / 最高 40cm），不写会互相矛盾的拆分项；把口径冲突写进「待确认」，让工厂复核。
- 这样即使拆分口径错，也不会有任何一个数字是编造的，风险最低。
- **图与后台两套口径也常见**（例：尺寸图 40×25×23，后台 44.5×29.5×27，双层还与单层同值）→ 全文不写尺寸数字，改由图片与 A+ 承载，后台字段标 `conflict` 待工厂复核。

## 七、API / CLI 口径（2026-11-04 落地）

- 流水线骨架（项目机可选，换机可缺省）：`D:/亚马逊运营模型/_API流水线/`；核心约束是**38/39 项校验层必须留在本地，不交给模型**——换机上没有这条流水线时，用技能自带的 `scripts/check_listing.py` 跑同一套闸门。
- **两段式**：阶段一跑到 `patchListingsItem?mode=VALIDATION_PREVIEW` 就落盘待批准；阶段二要在 run 目录放 `APPROVED` 才能 `--commit`。定时任务绝不直接回写。
- **ACCEPTED ≠ 上线**：提交后必须 `getListingsItem` 回读，比对线上标题与 spec、检查 ERROR issues。Brand Registry 字段所有权 / Style Guide 改写 / 另一个定时 feed 都可能静默回滚。
- SP-API 只推文本属性（item_name / bullet_point / product_description / generic_keyword），**A+ 与图片是另外的流程**；变体商品 patch 父体 SKU，尺寸变体要按子体分别改。
- **Amazon domain：UK/GB = 2，DE = 3，US = 1**。调用模板 `sorftime api <Endpoint> '<json>' --domain N --profile <name>`，Endpoint 严格 PascalCase。
- `ProductRequest` 一次返回五点、后台属性、`productInfo`、子体属性、图片、品牌/价格/星级/类目/变体数；最多 10 个 ASIN 逗号分隔。
- 返回 `{requestleft, requestconsumed, code, message, data}`，**`code===0` 才是成功**；错误码 `400`=非认证 IP、`401`=接口未开放、`500/501/502`=限额。单 profile QPM ≤ 200。
- **金额单位是当地货币最小单位（便士），要 /100**。`property` 是「该产品当前已填属性」，不是「该类目必填字段清单」，更不能照抄竞品值。
- **MCP 工具 → CLI 端点**：`product_detail`→`ProductRequest`；`product_variations`→`ProductVariationHistory`；`product_reviews`→`ProductReviewsQuery`；`product_traffic_terms`→`ASINRequestKeywordv2`；`category_keywords`→`CategoryRequestKeyword`（参数 `nodeid` 小写 d）；`keyword_extends`→`KeywordExtends`。
- **字段名与单位全变**：MCP 的 `price/star_rating/review_count/monthly_sales_volume/main_image/description` → CLI 的 `salesPrice/ratings/ratingsCount/listingSalesVolumeOfMonth/photo/Description`；CLI 与 MCP 切换后**必须跑一次 `--inspect-facts` 实测核对**。
- Windows CLI 两大坑：① `shell:true` 会吃掉 JSON 双引号 → 改单引号 JSON5（内容含 `'` 先转义）；② CLI 字段名大小写不同（`Category`/`BsrCategory` 首字母大写），`nodeId` 要从 `BsrCategory[0][1]` 取数字节点。
- 凭证：SK 只在用户本机 `sorftime add <profile> <api-key>` 配置，Agent 只调 `--profile`，**不接触密钥**。

## 八、后台字段与模板（2026-11-04 落地）

- `_刊登信息模板/`：字段字典单一源 → 56 字段 Excel + 同源 JSON。**截图字段是类目特定的**，不能推广到别的类目。
- **三层字段名分开存**：本地稳定列名 / 后台 UI 标签 / 平台 API 属性名。第三层按小写下划线猜的一律标 `unverified`，回填前用 `getDefinitionsProductType` 核。后台 UI 的 `Generic Keywords` 就是 Search Terms。
- **后台属性别手填，去 `product_content.product_info` 拿**：MCP 直接返回 30+ 个 key:value（Model Name / Model Number / Manufacturer / Material / Country of Origin / Is Assembly Required / Item Weight 等）。
- **字段值要带状态**：`confirmed / todo / not_applicable / conflict`。「非空」不等于「可回填」；同一产品里后台属性、`product_info` 与既有文案的尺寸常互相矛盾 → 标 `conflict` 让回填脚本跳过，绝不挑一个顺眼的用。

## 九、ERP 与产品库（2026-11-05 起）

- 做完一条链接自动登记：`node 登记产品.js` 扫描 `Listing_*/_spec*.js`、`输入/<ASIN>/`、`输出/template_*` 重建 `索引/products.index.json`；SKU 映射在 `索引/sku-map.csv`（seller_sku 需从后台抄）。
- 查询：`node 索引/查SKU.js <SKU/ASIN/前缀/标题词> [--fields|--ready|--pending|--copy|--json]`。统计口径：**可回填 = status confirmed/filled 且值非「待查/待确认/N/A」**。
- 简易 ERP：`node _刊登信息模板/erp/server.js` → http://127.0.0.1:8787。编辑存 `索引/编辑/<ASIN>.json`，原始产物永不改写；编辑层内容未经校验，正式用前 `--gen-only --spec <导出文件>` 复验。
- 坑：① HTTP POST 分支必须 method-aware；② 字段 ID 含 `.`（如 `copy.bullet_1_h`）不能用 `querySelector('#…')`，要 `getElementById`；③ HTTP 服务必须每请求兜异常（catch 回 500 + `uncaughtException` / `unhandledRejection`），否则一条缺 spec 的产品就能让 Node 进程退出、全员断线；④ SESSIONS 已持久化到 `erp/logs/sessions.json`，重启不踢人；⑤ 改 `server.js` 必须重启（`_test/restart_check.js`），只改 `index.html` 刷新即可。
- 只补跑失败平台：`node 跑平台.js --asin <ASIN> --platform temu,tiktok --site GB --ticket <T...>`（逗号列表已支持）。

## 十、脚本实现坑

- **Write 工具写单引号字符串时 `\\'` 会语法错**（被解析成「反斜杠 + 结束引号」）。写正则一律用双引号字符串，例如 `new RegExp("won[\u2019']?t", "g")`。
- 用模板字符串生成校验代码（如批量补丁脚本）时，`\\'` 输出为 `\'`，是合法的——与上面直写文件的情况不同，别混淆。
- `_check*.js` 的批量补丁锚点用行首正则（`^\s*add\(\d+,\s*'全文无品牌名`），兼容单行与跨行的 `add(...)`。

## 十一、Listing 校验坑（2026-11-08 实测）

- **`check_listing.py` 的 `has_phrase` 会做单复数归一**（`_singular` 去词尾 s）：`shelves`→`shelve`、`shelfs`→`shelf`。Search Terms 里放拼写/语序变体时极易被判与 Item Highlights 重复（`DUP_IH_ST`）：`floating shelfs` 归一后 = `floating shelf`（IH 有）、`shelve` 归一后命中 IH 的 `Shelves`、`floating wall shelf` 同理。
- **相邻词会拼出新短语**：ST 写 `shelf for wall shelves wall`，中间的 `wall shelves` 连续出现，又撞回 IH 的 `Wall Shelves`。排 ST 要按滑窗查相邻词，不能只看单个词。
- **实践口径**：品类词的拼写变体收益有限、撞词风险高，ST 只留 2–4 个真正不与前台冲突的语序变体即可，不为凑 250 字节硬塞。B0HK7PS2RT 最终 ST 仅 `wall shelving shelf for wall`（28 字节）仍 PASS。
- **变体维度决定关键词可用性**：颜色/尺寸若是变体主题，含该属性的高搜索量词（如 `gold wall art` 6,277、`white shelves` 19,189）**不得进文案**（同父体其他子体共用 Listing），只能在诊断里写明排除原因。
- **场景词以 `product_content.property` 的 Room type 为准**：只列 Bedroom / Entryway / Living Room / Vanity 时，`bathroom shelves`(36,131)、`kitchen shelves`(19,187) 这类大词一律不用，哪怕搜索量高。
