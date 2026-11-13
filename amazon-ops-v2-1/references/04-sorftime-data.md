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
