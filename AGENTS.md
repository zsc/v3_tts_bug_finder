下面我先把“高概率撞出代表性、严重性 bug”的思路系统化，然后给出一份可以直接丢给 `gemini-cli/codex` 去实现的 **Python + HTML demo SPEC**（含模块拆分、接口、搜索策略、去重/新颖性、LLM 提示词、UI/接口）。

---

## 一、问题抽象与判定口径（先把“bug”定义清楚）

你这个 “TTS bug finder” 本质是一个 **文本 → 语音(TTS) → 转写(ASR) → 对齐评估** 的 fuzzing / adversarial search 系统。
我们要找的是：

* **输入文本合理**（能作为 TTS 朗读内容：新闻句子、对话、播报、说明书、含数字口播等）
* **输出错误夸张**（ASR 转写与原文差距巨大，且最好是“关键内容错”）
* **代表性强**（能归到明确类别：数字口播错、外文拼读错、多音字错、停顿/断句错、Unicode/符号错、截断等）
* **后续发现要新颖**（不要只是换个数字重复撞同一种错）

### 1) 基础差异指标（可自动化）

对 `ref=text` 与 `hyp=asr(text->tts->asr)`：

* **CER（中文）**：字符级编辑距离 / ref 长度
* **WER（英文/空格语言）**：词级编辑距离 / ref 词数
* **长度比**：`len(hyp)/len(ref)`（截断、爆长、重复都很敏感）
* **diff 结构特征**：替换/插入/删除比例、最长连续删除段长度（常对应“中间整段没读/没识别”）

### 2) “严重性”不要只看 CER：引入关键内容错（更代表性）

即使 CER 不夸张，**数字/否定/专名**错也很严重；反过来 CER 很高但只是标点/语气词错，代表性可能差。

建议额外计算：

* **数字一致性**：从 ref/hyp 抽取所有数字（含中文数字、一二三、两、十百千、点、百分号、单位），比较集合/序列差异
* **否定翻转**：检测“不/没/无/非/未/别/不要/不能/无需”等关键否定词是否丢失/新增（这类错很“致命”）
* **专名/缩写**：英文大写串（GPU/USB/HTTP）、品牌/人名地名（可简单用规则 + 可选 LLM 标注）
* **截断/重复**：ASR 输出相对 ref 极短（可能 TTS 崩、ASR VAD 截）或出现明显循环片段（TTS 重复播放、韵律崩）

### 3) 收录条件（可配置阈值）

一个候选样本被收录为 “bug case” 的最小条件（示例）：

* `plausibility_score >= 0.7`（输入合理性评分，规则+LLM）
* 且满足以下之一：

  * `CER >= 0.35`（中文）或 `WER >= 0.40`（英文）
  * 或 `critical_error_score >= 0.8`（数字错、否定错、专名错、截断/重复）
* 且 **不与已有样本重复**（后面讲去重/新颖性）

---

## 二、哪些输入“高概率撞出 bug”（先给出种子类型）

下面这些类别通常对 TTS/ASR 组合都很“脆”，而且每类都能产出大量不重复的新颖样本。

### A. 多音字/异读字 + 语境诱导

典型：行、重、长、还、为、便、薄、朝、藏、乐、单、解、曾、区、仇 等
策略：给出**强语境**让正确读音很确定，但 TTS 容易读错，ASR 再进一步偏。

示例模板（合理口播）：

* “客服说明：**银行**的**行**长今天不在。”（行：háng/xíng）
* “这段视频**重**新上传，不要**重**复下载。”（重：chóng/zhòng）

### B. 绕口令/近音密集（小错很容易被放大）

* “四是四，十是十，十四是十四，四十是四十。”
* “吃葡萄不吐葡萄皮，不吃葡萄倒吐葡萄皮。”

这些很容易导致 **音素级错误→词级错位→整句崩**。

### C. 数字口播（日期/金额/版本号/小数/单位/范围）

这是最“致命”的代表性 bug 来源之一：

* 金额：`¥1,234,567.89` / “一百二十三万四千…”
* 日期：`2026-02-20 13:05`
* 版本号：`v1.0.0-beta+exp.sha.5114f85`
* 比例/范围：“3–5 次/天”、“±0.5℃”、“0.03%”

数字非常容易产生：

* 读法不一致（1.2 读成 12）
* 小数点丢失
* 单位错读（m/s、km/h、℃）
* 断句导致数字分裂

### D. 中英混读 / 缩写 / 专有名词（拼读策略不稳定）

* “请把日志发到 `ops-alert@company.com`，主题写 **CPU 过热**。”
* “我们用 **A/B 测试**对比 iOS 17.4 和 Android 15。”
* “模型是 GPT-4o-mini / GPT-5.2 Pro（示例）。”

TTS 可能会：

* 把缩写按字母读/按词读乱跳
* email/url/symbol 崩掉
* 连读导致 ASR 大段错

### E. 标点/引号/括号/省略号/破折号 + 长句

* “他说：‘我**不是**不愿意——只是现在不方便……’”
* “请朗读以下条款（含括号内容）：……”
  这类很容易触发：
* 停顿/VAD 截断
* 引号内容丢失
* 破折号导致节奏异常

### F. Unicode/全角半角/零宽字符/相似字形（输入“看起来合理”，但系统处理容易翻车）

* 全角数字：`１２３４`
* 零宽空格：`我\u200b们`
* 类似字形：拉丁 a vs 西里尔 а（肉眼几乎一样）
* 不间断空格 NBSP

这类更偏“工程 bug”，代表性也强（文本预处理、tokenizer、正则、normalize）。

### G. 重复/口吃/拟声词（容易触发 TTS 重复或 ASR 错位）

* “我我我觉得…这个…嗯…有点不太对。”
* “哈哈哈哈哈……别笑了。”
  可用于诱导 **重复播放/重复识别** 的严重错误。

### H. 很短的指令句 vs 很长的段落（边界条件）

* 超短：“好。”、“嗯？”（ASR 极易漂）
* 超长：播报一整段（容易截断、内存/时长上限、VAD）

---

## 三、核心搜索策略：快速找到“严重且新颖”的样本

### 总体流水线（推荐做成 4 阶段）

1. **Seed 扫描（广度）**：先跑高风险种子库，快速拿到第一批高分样本和“错误模式画像”
2. **规则变异（速度快）**：对“高产 seed”做结构化变异（数字/符号/同音/标点/中英混排）
3. **LLM 放大（从小错变大错）**：对“接近阈值但很有代表性”的样本，让 LLM 生成一批“同类但更难/更严重/更自然”的改写
4. **去重与聚类（保证新颖性）**：按“错误签名”聚类，只保留每簇最严重+最代表性的 1~N 个

### 1) 评分函数（用于排序和探索）

建议一个总分 `score`（0~100）：

* `base = 60 * CER_or_WER`
* `critical = 25 * critical_error_score`（数字/否定/专名/截断/重复）
* `bonus = 10 * novelty_bonus`（越不像已有簇越加分）
* `penalty = 20 * duplication_penalty`（疑似重复扣分）
* `score = clamp(base + critical + bonus - penalty, 0, 100)`

这样系统会倾向产出“严重 + 关键内容错 + 新颖”的样本。

### 2) “LLM 放大”怎么做才有效（关键点）

LLM 不要瞎改，应该 **根据已观测到的错** 来放大：

* 输入给 LLM：`ref_text`、`hyp_asr`、diff 摘要、系统标签（比如检测到“数字错 + 断句异常”）
* 让 LLM 输出多个候选：

  * 保持语义自然（像播报/客服/说明）
  * 复用导致错误的“脆弱点”（比如某个多音字/某种数字格式）
  * 但在内容上引入变化（避免重复收录）
  * 尽量让错落在“关键槽位”（金额、日期、否定、地址、型号、剂量等）

### 3) 去重与新颖性（必须做，否则会全是绕口令变体）

建议同时做三种去重：

* **文本近重复**：对 ref 做 normalize（去多空格、统一全半角、去标点可选），算相似度（rapidfuzz / difflib / char-3gram cosine）
* **输出近重复**：hyp 相似度
* **错误签名重复**：从对齐中抽取 top-k 替换对（比如 “四十→十四”、“GPU→鸡皮尤” 这种），再加上类别标签（numbers/mixed_lang/polyphone/truncation…）

当 `text_sim > 0.85` 或 `signature_sim > 0.8` 就视为重复，不收录；
但仍可用于“探索”，只是不会进最终 bug list。

---

## 四、可交付 SPEC（给 gemini-cli/codex 实现 Python+HTML demo）

下面是一份“直接照做”的 SPEC。你可以原样丢给代码模型实现。

---

# SPEC：TTS Bug Finder（Python + HTML Demo）

## 0. 目标

构建一个可运行的 demo，用于自动搜索能导致 **TTS→ASR 严重失配** 的输入文本，并以“严重性 + 代表性 + 新颖性”为核心进行收录、去重、聚类和展示。

### 核心输出

* 一组 **Bug Cases**（每个含：输入文本、TTS 音频、ASR 输出、diff 高亮、严重性评分、类别标签、关键错误摘要）
* 一个 **Web UI**：可搜索/过滤/播放/对比/导出
* 一个 **CLI Runner**：可设定预算（条数/时间）、并发、阈值、模型适配器

## 1. 运行形态

* Python 3.11+
* 本地服务：`http://localhost:8000`
* CLI：

  * `python -m tts_bug_finder run --config config.yaml --budget 500 --concurrency 8`
  * `python -m tts_bug_finder serve --db artifacts/bugs.sqlite --port 8000`
  * `python -m tts_bug_finder export --format jsonl --out artifacts/export.jsonl`

## 2. 适配器接口（TTS / ASR / LLM）

实现“可插拔”，demo 至少提供 DummyAdapter（不连外部服务）+ 一个 HTTP API Adapter 模板。

### 2.1 TTS Adapter

```python
class TTSAdapter(Protocol):
    name: str
    def synthesize(self, text: str, *, voice: str | None = None) -> bytes:
        """Return audio bytes (wav preferred). Raise on error."""
```

### 2.2 ASR Adapter

```python
class ASRAdapter(Protocol):
    name: str
    def transcribe(self, audio_bytes: bytes, *, language: str | None = None) -> str:
        """Return transcript string. Raise on error."""
```

### 2.3 LLM Adapter

```python
class LLMAdapter(Protocol):
    name: str
    def generate_json(self, prompt: str, schema: dict, *, temperature: float=0.7) -> dict:
        """Return JSON that conforms to schema."""
```

> 说明：LLM 必须走 “JSON schema 输出”，避免解析崩。

## 3. 数据模型与存储

### 3.1 BugCase（SQLite）

字段建议：

* `id` (uuid)
* `created_at`
* `seed_id`（来源种子/模板）
* `ref_text`
* `hyp_text`
* `audio_path_wav`
* `audio_path_mp3`（可选，便于浏览器播放）
* `duration_sec`
* `lang_guess`（zh/en/mixed）
* `cer`, `wer`, `len_ratio`
* `critical_error_score`
* `score_total`
* `tags`（JSON list: ["numbers","mixed_lang","polyphone","truncation"...]）
* `signature`（JSON：错误签名）
* `cluster_id`（聚类结果）
* `llm_summary`（一句话：错在哪里、为什么严重、代表什么类别）
* `status`（candidate/accepted/rejected/duplicate）

### 3.2 工件目录结构

```
artifacts/
  audio/
    <id>.wav
    <id>.mp3
  bugs.sqlite
  logs/
  exports/
```

## 4. 文本合理性（Plausibility）判定

必须实现 `plausibility_score(text) -> float`：

* 规则分（0~1）：

  * 长度在 [5, 300] 加分；极端短/极端长扣分
  * 控制字符/大量乱码扣分
  * “字符种类比例”异常（比如 90% 都是同一个字）扣分
* 可选 LLM 分（0~1）：

  * Prompt：判断是否像真实人会拿去让 TTS 朗读（播报/对话/说明/公告），输出 0~1
* 最终：`0.7*rule + 0.3*llm`（LLM 不可用时仅规则）

## 5. 指标计算与严重性评分

### 5.1 文字对齐

* 中文：按字符序列对齐
* 英文：按空格分词（简单即可）
* 输出：

  * 编辑距离
  * diff spans（用于 HTML 高亮）

### 5.2 CER/WER

* `CER = edit_distance(chars(ref), chars(hyp)) / max(1, len(chars(ref)))`
* `WER = edit_distance(words(ref), words(hyp)) / max(1, len(words(ref)))`

### 5.3 关键错误评分 `critical_error_score`（0~1）

至少实现：

* `numbers_mismatch`: 抽取数字 token（包含中文数字与阿拉伯数字、版本号片段），比较差异
* `negation_flip`: 检测否定词集合差异（ref 有 hyp 无 or hyp 有 ref 无）
* `truncation`: `len_ratio < 0.6` 或 ASR 输出为空
* `repetition`: hyp 出现重复 n-gram（例如 5-gram 重复次数 > 阈值）

汇总成：
`critical_error_score = clamp(max(numbers, negation, truncation, repetition, ...), 0, 1)`

### 5.4 总分 `score_total`

如前：`score_total = 60*cer_or_wer + 25*critical + 10*novelty - 20*dup_penalty`

## 6. 种子库（Seeds）

必须内置一个 `seeds.py`，按类别给出模板与实例（每类至少 20 条，且可参数化生成）。

类别与生成要点（至少包含）：

* `polyphone_zh`：多音字语境句
* `tongue_twister_zh`：绕口令/近音密集
* `numbers_broadcast`：日期时间/金额/版本号/单位/范围
* `mixed_lang`：中英混排/缩写/email/url
* `punctuation_heavy`：引号/括号/破折号/省略号
* `unicode_tricky`：全角半角/零宽/相似字形（必须保证“看上去合理”）
* `stutter_laugh`：口吃/哈哈/拟声词
* `boundary_short_long`：极短/极长边界

每个 seed 要带元数据：

```json
{
  "seed_id": "numbers_broadcast_001",
  "text": "...",
  "tags": ["numbers","broadcast"]
}
```

## 7. 规则变异器（Mutators）

实现一组快速变异器 `mutate(text)->list[text]`，每个 mutator 输出 3~10 个候选：

* `mutate_numbers`: 数字在“阿拉伯↔中文”、加小数/单位/范围、加版本号片段
* `mutate_punct`: 插入/替换引号括号破折号省略号，改变断句位置
* `mutate_mixed_lang`: 插入缩写/email/url/型号串
* `mutate_repetition`: 插入口吃片段、重复短语但控制多样性
* `mutate_unicode`: 全半角切换、插入 NBSP、零宽空格（谨慎，仍要“可读”）
* `mutate_polyphone_context`: 给含多音字的句子换语境（银行/行业/行走）

变异必须带上 `mutation_trace`（便于 debug 与展示）。

## 8. LLM 生成与放大（核心）

在 runner 中，当发现：

* `score_total` 接近阈值（比如 40~60）
* 或者 `critical_error_score` 高但 CER 不够
  就触发 LLM 放大：

### 8.1 LLM 输入

* ref_text
* hyp_text
* tags（系统检测）
* diff 概要（前 200 字符）
* 要求：生成 N=8 条新文本，每条自然、不同、不重复，且倾向放大同类错误

### 8.2 LLM 输出 JSON schema（示例）

```json
{
  "type": "object",
  "properties": {
    "candidates": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "text": {"type": "string"},
          "why_likely_break": {"type": "string"},
          "expected_tags": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["text"]
      }
    }
  },
  "required": ["candidates"]
}
```

### 8.3 LLM 生成 prompt（可直接用）

（实现时注意：不要输出多余文本，强制 JSON）

* System:

  * “你是语音系统鲁棒性测试专家……输出必须是 JSON……不要解释……”
* User:

  * 给 ref/hyp + 规则检测 tags
  * 约束：

    * 每条文本像真实要朗读的内容（公告/播报/客服/说明/对话）
    * 不要只是机械重复同一句
    * 尽量让关键槽位包含易错点（数字、否定、型号、地址、金额等）
    * 每条 20~120 字

## 9. 去重与聚类（保证新颖性）

### 9.1 文本 normalize

* NFKC（可选）
* 统一空白
* 可选：去标点版用于相似度比较（保留数字和字母）

### 9.2 相似度

至少实现：

* `text_sim = rapidfuzz.ratio(norm_ref_a, norm_ref_b)/100`
* `hyp_sim = rapidfuzz.ratio(norm_hyp_a, norm_hyp_b)/100`

### 9.3 错误签名 signature

从对齐结果抽取：

* top-5 替换对（ref_span -> hyp_span）
* numbers extracted
* negation set diff
* tags

signature 示例：

```json
{
  "top_subs": [["四十","十四"],["行长","行走"]],
  "has_numbers": true,
  "negation_flip": false,
  "tags": ["numbers","polyphone"]
}
```

### 9.4 收录规则

* 若与任意已 accepted case 满足：

  * `text_sim > 0.85` **或**
  * `signature_sim > 0.8`（简单：top_subs 重合度 + tags 重合度）
    则标记为 `duplicate`，不进入展示主列表（可在 UI 里开关显示 duplicates）。

### 9.5 聚类（可简化）

* 基于 tags + top_subs 的 hash 作为 `cluster_id`
* 每个 cluster 默认只展示 top-3 分数最高的 case，其余折叠

## 10. Runner（搜索调度）

### 10.1 并发

* `asyncio` + semaphore 控制并发
* 对同一 text 做缓存（hash -> tts_audio_path + asr_result），避免重复调用模型

### 10.2 调度策略（推荐实现）

* 初始队列：所有 seeds
* 每轮：

  1. 从队列取若干 text
  2. synthesize + transcribe
  3. 打分、去重、入库
  4. 对“高分且新颖”的 text：

     * 规则变异（扩展队列）
  5. 对“接近阈值但很有代表性”的 text：

     * LLM 放大（扩展队列）
* 停止条件：

  * 达到 `budget_accepted`（比如 100 个 accepted）
  * 或达到 `budget_total_eval`（比如评测 5000 条）
  * 或达到 `time_limit_sec`

## 11. Web 服务与 HTML UI

推荐：FastAPI + Jinja2（或纯静态 + JSON API）。

### 11.1 API（最小集）

* `GET /`：列表页
* `GET /case/{id}`：详情页
* `GET /api/cases?status=accepted&tag=numbers&min_score=60&search=...`
* `GET /audio/{id}.mp3`：音频
* `POST /api/run`（可选）：触发后台 run（demo 可不做后台，只做 CLI）

### 11.2 列表页要求

* 过滤：tag、多选；min score；是否显示 duplicates；cluster 折叠
* 每条显示：

  * score、CER/WER、critical_error_score、tags
  * ref_text（截断预览）
  * hyp_text（截断预览）
  * “播放”按钮（audio）
  * “查看详情”

### 11.3 详情页要求

* 音频播放器
* ref vs hyp 的 diff 高亮（删除/替换/新增不同样式）
* 关键错误摘要（数字差异、否定差异、截断提示）
* LLM summary（一句话解释“错在哪里、为何严重、代表何类”）
* 元数据：seed_id、mutation_trace、duration

## 12. 导出

* JSONL：每行一个 case（含音频路径、指标、tags、signature、summary）
* 可选：导出一个静态 HTML 报告包（把音频与页面打包）

## 13. 测试与演示

必须提供：

* `DummyTTSAdapter`：把 text 写入一个“假音频”占位（或用本地 TTS 库可选）
* `DummyASRAdapter`：做一些可控扰动（模拟“数字错/截断/多音字错”），确保 demo 不接外网也能跑通 UI
* 单元测试：

  * CER/WER 正确性
  * numbers/negation 抽取
  * 去重逻辑

---

## 五、额外建议：让“新颖性”更像人工想要的“代表性”

如果你希望 demo 更像“测试工程产出”，建议加一个 **LLM 归因/归类器**（不参与收录，只做解释）：

* 输入：ref/hyp/diff + tags + numbers/negation 结果
* 输出：

  * `root_cause_hypothesis`: 例如 “数字规范化失败 / VAD 截断 / 多音字读错 / 中英混读策略不一致 / Unicode normalize bug”
  * `impact`: “金额错误/日期错误/否定翻转/人名地名错误”
  * `repro_hint`: “把 x 换成 y 更容易复现”

这会让每个 case 更“可读”、更“代表性”。

---

如果你愿意，我也可以在这个 SPEC 基础上，把 **种子库（每类 20~50 条）** 和 **LLM prompts（放大/归类/合理性）** 直接给成可复制的文本块，让 codex 一次性生成完整项目。

