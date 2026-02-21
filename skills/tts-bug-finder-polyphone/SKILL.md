---
name: tts-bug-finder-polyphone
description: 多音字/古文专项：跑中文 polyphone fuzz（纯汉字）并生成单文件 HTML 报告（macOS say 或 Qwen3-TTS 0.6B → whisper）。
metadata:
  short-description: Polyphone fuzz + HTML report
---

# TTS Bug Finder：多音字 / 古文专项（纯汉字）

当你想聚焦 **纯汉字** 的多音字/古文读音问题（避免数字/英文/符号把信号搅乱），并希望输出一个**单文件 HTML**（可播放 WAV、GT/ASR 并排、可搜索）时，用这个技能。

## 经验教训（开发过程中踩坑总结）

- **繁简体不是错**：Whisper 经常输出繁体；不应当把“只是繁体”当作 bug。解决：默认开启 `--t2s`（OpenCC 繁→简归一化）。
- **CER/WER 要“可解释”**：早期直接按字符算 CER，会被标点/省略号/NFKC 形变严重干扰（例如 `……` 会 NFKC 成 `......`）。解决：CER tokenization 忽略大多数标点，只保留“夹在字母数字之间”的少量符号（避免把 URL/版本号拆烂）。
- **长度比（截断）要按 token 算**：用原始字符串长度算 `len_ratio` 会被标点/空白/NFKC 扰动误判“截断”。解决：`len_ratio` 基于对齐 token 长度（中文按 CER token，英文按 WER token）。
- **否定词要先做繁简归一化**：不开 `--t2s` 时，`別/沒/無` 等无法被否定词规则命中，导致“否定翻转”漏检；因此建议 `--t2s` 常开。
- **去重不够用时，语义过滤必须上 LLM**：文本相似度/签名相似度只能挡住近重复，挡不住“语义等价但写法不同”。解决：`--kimi` 做两道闸：
  - GT/ASR 语义等价 → 直接 reject
  - 相对已有模式不新颖 → 标 duplicate
- **长期跑必须可持续**：不持久化 seen/不从历史 accepted 继续变异，跑几轮就会“干涸”。解决：`--persist-seen` + `--bootstrap-from-accepted`。
- **报告单文件很方便，但会变大**：`--bundle-audio` 会把 WAV base64 内嵌进 HTML，几百条样本就能到几十 MB；长期跑要注意体积。
- **Qwen3-TTS 更“重”**：模型加载/推理慢，建议 `--concurrency 1`，并用 `QWEN3_TTS_DEVICE` 指定 `mps/cuda`（可用时）。

## 一轮跑法（推荐参数）

### macOS `say` → `whisper`

```bash
PYTHONUNBUFFERED=1 python -m tts_bug_finder run \
  --db artifacts_polyphone_say/bugs.sqlite \
  --artifacts artifacts_polyphone_say \
  --tts macos_say \
  --asr whisper_cli \
  --concurrency 2 \
  --time-limit-sec 300 \
  --budget 1000000 \
  --budget-accepted 1000000 \
  --max-depth 4 \
  --t2s \
  --seed-tags polyphone,guwen \
  --only-hanzi \
  --min-cer 0.25 \
  --bootstrap-from-accepted \
  --persist-seen \
  --kimi

python -m tts_bug_finder report \
  --db artifacts_polyphone_say/bugs.sqlite \
  --out artifacts_polyphone_say/report.html \
  --status accepted \
  --bundle-audio
```

### Qwen3-TTS 0.6B（`--tts qwen3_tts`）→ `whisper`

更慢；建议 `--concurrency 1`、把 `--time-limit-sec` 适当调大：

```bash
PYTHONUNBUFFERED=1 python -m tts_bug_finder run \
  --db artifacts_polyphone_qwen3/bugs.sqlite \
  --artifacts artifacts_polyphone_qwen3 \
  --tts qwen3_tts \
  --asr whisper_cli \
  --concurrency 1 \
  --time-limit-sec 420 \
  --budget 1000000 \
  --budget-accepted 1000000 \
  --max-depth 3 \
  --t2s \
  --seed-tags polyphone,guwen \
  --only-hanzi \
  --min-cer 0.25 \
  --bootstrap-from-accepted \
  --persist-seen \
  --kimi

python -m tts_bug_finder report \
  --db artifacts_polyphone_qwen3/bugs.sqlite \
  --out artifacts_polyphone_qwen3/report.html \
  --status accepted \
  --bundle-audio
```

### 合并报告（两个 DB → 一个 HTML）

```bash
python -m tts_bug_finder report \
  --db artifacts_polyphone_say/bugs.sqlite artifacts_polyphone_qwen3/bugs.sqlite \
  --out artifacts_polyphone/report.html \
  --status accepted \
  --bundle-audio
```

## 长期跑（循环脚本）

这个仓库自带 `scripts/long_run_macos_whisper.sh`：每轮跑 `run`，然后自动重建 HTML 报告。

```bash
chmod +x scripts/long_run_macos_whisper.sh
TTS_KIND=macos_say SEED_TAGS=polyphone,guwen ONLY_HANZI=1 MIN_CER=0.25 ./scripts/long_run_macos_whisper.sh
```

切换到 Qwen3-TTS：

```bash
TTS_KIND=qwen3_tts CONCURRENCY=1 SEED_TAGS=polyphone,guwen ONLY_HANZI=1 MIN_CER=0.25 ./scripts/long_run_macos_whisper.sh
```

## 关键开关（你可能会改的）

- `--seed-tags polyphone,guwen`：初始队列只选带这些 tags 的 seed（只古文：`--seed-tags guwen`；只现代口语多音字：`--seed-tags polyphone`）。
- `--only-hanzi`：队列文本若含数字/拉丁字母会被过滤（更像“纯汉字”读音问题）。
- `--min-cer`：多音字问题经常不是“整段崩”，适当降低（例如 `0.25`），并依赖 `--kimi` 做语义过滤。
- `--max-depth`：变异深度。古文/多音字专项可以比默认更深一点（`3~4`），但会更慢、也更容易跑出重复。
- `--t2s`：繁→简归一化（依赖 `opencc-python-reimplemented`；已在 `pyproject.toml` 里声明）。
- `qwen3_tts` 依赖：当前 Python 环境需能 import `qwen_tts`、`torch`、`soundfile`。
- `QWEN3_TTS_*` 环境变量：
  - `QWEN3_TTS_DEVICE=auto|mps|cuda|cpu`
  - `QWEN3_TTS_SPEAKER=Vivian`
  - `QWEN3_TTS_MODEL=Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice`
  - `QWEN3_TTS_LANGUAGE=Chinese`
  - `QWEN3_TTS_INSTRUCT=...`（可空）

## 实验记录（本地 artifacts，未入 git）

下面是我们在 2026-02-20 ~ 2026-02-21 做过的几轮代表性实验，方便快速复现/回看：

- **全量种子（say→whisper，多轮累计）**：合并报告 `artifacts_report/report_real.html`
- **polyphone/古文专项（say→whisper）**：`artifacts_polyphone_say/bugs.sqlite` → `artifacts_polyphone_say/report.html`
  - 例：`解衣欲卧，忽闻风起。` → `解疑遇我,呼吻封棋`（古文 + 多音字/近音导致整句崩）
  - 例：`长者赐，不敢辞。` → `长着刺,不敢刺`（字形/近音混淆，关键字被替换）
- **polyphone/古文专项（qwen3_tts→whisper）**：`artifacts_polyphone_qwen3/bugs.sqlite` → `artifacts_polyphone_qwen3/report.html`
  - 例：`敌众我寡，愿降不愿战；天降大任于斯人也。` →（ASR 输出出现长段无关内容/乱码，CER 极高）
- **polyphone 两链路合并报告**：`artifacts_polyphone/report.html`

如需把“所有有趣例子”塞进一个 HTML，可用 `report --db ...` 合并多个 DB（见上面的合并示例）。
