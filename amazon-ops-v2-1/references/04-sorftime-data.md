# 取数手册：Sorftime MCP 调用参数、字段口径与实测陷阱

> 这是第 1 步「取数与诊断」的工具层参考。**每个数字都必须能追到下面某一次调用**，追不到就不写。

---

## 一、七个工具，各管一段

| # | 工具 | 入参 | 拿什么 | 用在哪一步 |
|---|---|---|---|---|
| 1 | `product_detail` | `asin`, `amz_site` | 品类路径、价格、评分、评论数、月销、上架日、变体数、卖家、配送方式、尺寸重量 | 锁身份 |
| 2 | `product_content` | `asin`, `amz_site` | 标题、五点、描述、A+、视频有无 | 内容资产基线 |
| 3 | `product_traffic_terms` | `asin`, `amz_site`, `page` | 该 ASIN **实际吃到**的词 + 自然位 + 搜索量 + 点击份额 | 自然位现状 |
| 4 | `category_report` | `node_id`, `amz_site` | Top100 月销量/销售额/均价/极值/CVR/退货率/在架天数/三层集中度 | 类目大盘 |
| 5 | `category_keywords` | `node_id`, `amz_site`, `page` | 类目 Top 词表（宽度） | 词表全集 |
| 6 | `keyword_detail` | `keyword`, `keyword_support_site` | 月搜索、ABA 周排名、建议 CPC、旺季月份 | 单词价值 |
| 7 | `keyword_search_results` | `keyword`, `keyword_support_site`, `page`, `position_type` | 自然位/广告位的商品列表（价格、品牌、评分、月销、份额） | 竞品结构 |
| 8 | `product_variations` | `asin`, `amz_site` | 子体：价格、属性、库存、销量 | 变体价区间 |
| 9 | `keyword_trend` | `keyword`, `type=2`(月), `keyword_support_site` | `search_volume_trend` 扁平数组 [yyyyMM, 月搜索量, ...]，最长数年 | 旺季与季节性系数 |

> **`keyword_trend` 的 MCP 坑**：参数 `type` 语义与 API 相反——MCP 里 `2`=月度、`1`=周度（工具会自动映射）；月度用 `type=2`。返回是**扁平字符串数组**，偶数位=yyyyMM、奇数位=该月搜索量，必须两两配对解析，最后一个月若未结束要剔除。

**参数坑**：
- `amz_site` 与 `keyword_support_site` 是两个不同参数名，别混用；英国站是 **`GB`**，不是 `UK`。
- `keyword_search_results` 的 `position_type`：`0`=全部、`1`=仅自然位、`2`=仅广告位。**默认就是 1**，但显式写上更安全。
- `category_report` / `category_keywords` 的 `node_id` 必须从 `product_detail` 的类目路径里取最末级小类，不要用大类。

**三个词源的交叉分工**（不能只看一个）：
```
category_keywords  → 这个类目「有哪些词」（宽度）
keyword_detail     → 每个词「值多少钱、多难打」（CPC + ABA 排名）
product_traffic_terms → 这个 ASIN「已经在吃什么词、排第几」（现状）
```

---

## 二、八个实测数据陷阱（每条都踩过）

### 1. `profit` / `profit_rate` 不可信 —— 直接弃用
返回过「利润 34.14、利润率 85.37%」，但那是**成本按 0 计算**、只扣了佣金的结果。

→ **绝不引用这两个字段**。需要利润口径时用 `售价 × 佣金率` 反推，成本部分让用户给到岸价，拿不到就写成假设并标注。

### 2. `package_size_cm` / `weight_g` 经常为空
竞品链接上大量返回 `null`。

→ 尺寸与重量**只能来自产品实拍或供应商数据**。为空时不要用标题里的数字替代（标题常写错），标「待确认」。

### 3. `monthly_sales_volume` 是**父体级**
同一父体下的子变体会返回**完全相同的月销量**。

→ **绝不能把子变体的销量相加**，会翻倍。算份额时先按 `parent_asin` 去重。
→ 变量分析时只说「该父体月销 X」，不要说「这个颜色卖 X」。

### 4. `product_variations` 里子体 `SalesAmount` 常为 `-1`
`-1` 是**缺失**，不是「0 销量」。

→ 别用 `-1` 参与排序或求和；写「该子体销量未返回」。

### 5. `category_report` 的 `price` 最小值可能为 `0`
会把均价拉低，且 `min=0` 明显是异常数据。

→ 算均价时说明样本口径；`min=0` 要在文档里点出来，不要当成「类目有 0 元商品」。

### 6. `product_reviews` 负面评论经常返回 `No reviews found`
即使该 ASIN 有几十条评论、评分 4.9。

→ 拿不到负面明细时**不要编 VOC**。写「负面评论接口未返回明细」，VOC 部分改用 `product_customers_say` 或直接跳过。

### 7. 上架日期要自己算周数
`launch_date` 给的是日期，判断新品期要换算成周。

```bash
# 用命令算，不要目测
python3 -c "
from datetime import date
d = date(2026,6,2); t = date(2026,10,28)
print('上架周数:', round((t-d).days/7, 1))"
```

### 8. 竞品同形态判定不能只看标题
真实事故：把「KAYMAN £69.99」当成无垫款最高价，实际是 `With Mat, Teal` 子体；EVERYMILE £82.90 是 `Pink-Mat-N` 子体。两者都是**含垫价**，导致定价带上沿判断错了 30 英镑。

→ 判定含垫/不含垫、单件/套装、主体/配件，**必须看 `product_variations` 的属性名**，不能只看标题关键词。标题里没有 `with mat` 不代表该父体不带垫子体。

---

## 二·补、旺季与季节性系数（数据诊断第四节必做，2026-11-27 用户定规）

数据快照与诊断的「四、旺季与季节性」**不能只写一句「旺季在 X 月」**，必须给出归一化后的**季节性系数表**。

**算法**（用户口径：最高月 = 1，其余按比例 0.1 / 0.2 / 0.3…）：

1. 数据来源：`keyword_trend(keyword=主词, type=2, keyword_support_site=站点)` 的 `search_volume_trend`。
2. 取**最近 12 个完整月**（当前未结束的当月剔除）；每个词独立算。
3. 窗口内找月搜索量最大值 `peak`。
4. 每月系数 = `该月搜索量 / peak`，**四舍五入保留 1 位小数**（0.0–1.0）。peak 月 = 1.0。
5. 接近峰值的月份并列显示 1.0 属正常（如 68,056 与 68,013 都取 1.0），峰值绝对值以 `peak` 字段为准。

**输出格式**：一张「月份 × 主词」的系数表 + 每词一句峰值/谷值说明 + 数据区间与来源。

```bash
# 把 keyword_trend 原始返回汇总成 {"keywords":[{keyword, search_volume_trend}, ...]} 后：
python3 scripts/seasonality_index.py --input kw_trends.json --months 12 \
  --output 季节性系数.md --json-report 季节性系数.json
```

**红线**：
- 系数**只用于淡旺季判断与备货/推广排期**，**绝不写进 Listing 文案**（不可变成时效承诺或销量承诺）。
- 主词至少取 3–5 个（核心词 + 场景词各占），单词的系数不能代表整个类目。
- 数据不可得时写「`keyword_trend` 未返回月度数据，季节性系数无法计算」，**不得用类目预测涨幅反推系数**凑数。
- 类目 `category_report` 的 `sales_volume_change_rate_forecast` 是另一口径（销量预测涨跌幅），可与系数表并列陈述，但**不能混算成一个系数**。

---

## 三、取数顺序（省调用次数）

```
product_detail                    ← 先定身份，拿到 node_id 与变体数
  ├─ category_report              ← 类目大盘一次够
  ├─ category_keywords            ← 1-2 页
  ├─ product_content              ← 内容资产
  ├─ product_traffic_terms        ← 1 页够
  └─ product_variations（仅当变体数 > 1）
keyword_detail                    ← 只对入选的 4-8 个重点词调，不要全词表都调
keyword_search_results            ← 核心词前 2 页
  └─ product_detail + product_variations ← 只对「筛完的同形态竞品」调，通常 5-8 个
```

一个 ASIN 的完整分析通常 **15-25 次调用**。超过 30 次说明在无差别抓取，先筛再抓。

---

## 四、每个数字要带出处

写进文档时，用这种格式：

```
主词 high chair CPC £0.82（来源：keyword_detail / GB / 2026-10-29）
类目均价 £64.98（来源：category_report / node 60144031 / Top100）
```

不写来源的数字，事后无法复核，等于没写。
