---
name: tts-bug-finder-indextts2
description: 用 IndexTTS2（本地推理，多进程挤满 GPU）+ Whisper CLI（GPU，指定本地 large-v3-turbo.pt）持续挖掘 TTS bug；用 kimi 做语义等价/新颖性过滤；并将 accepted 样本打包成一个可下载目录（index.html + wav）。
metadata:
  short-description: IndexTTS2 fuzz + GPU whisper + HTML/WAV bundle
---

# IndexTTS2 TTS Bug Finder（Whisper GPU + 并行 TTS + 可下载打包）

当你要在本机镜像里 **持续找 IndexTTS2 的“有趣”TTS bug**（典型是数字/否定/型号/古文多音字/Unicode 等触发点），并且希望 **GPU 利用率高**、**不重复下载模型**、以及能把样本整理成 **一个目录便于下载（HTML + WAV）** 时，用这个技能。

## Quick Start（两条最常用命令）

### 1) 高产：数字/中英混合/Unicode/标点

```bash
cd /root/autodl-tmp/v3_tts_bug_finder

# Whisper：强制用本地权重文件（不要走在线下载）
export WHISPER_MODEL=/root/autodl-tmp/whisper/large-v3-turbo.pt
export WHISPER_MODEL_DIR=/root/autodl-tmp/whisper
export WHISPER_DEVICE=cuda
export WHISPER_FP16=1

# IndexTTS2：多进程挤 GPU + 离线 + 省显存（禁用 QwenEmotion）
export INDEXTTS2_REPO_DIR=/root/index-tts
export INDEXTTS2_MODEL_DIR=/root/index-tts/checkpoints
export INDEXTTS2_DEVICE=cuda:0
export INDEXTTS2_WORKERS=3
export INDEXTTS2_DISABLE_QWEN_EMO=1
export INDEXTTS2_OFFLINE=1

PYTHONUNBUFFERED=1 python -m tts_bug_finder run \
  --db artifacts_indextts2_live/bugs.sqlite \
  --artifacts artifacts_indextts2_live \
  --tts indextts2 \
  --asr whisper_cli \
  --budget 400 \
  --budget-accepted 40 \
  --time-limit-sec 1800 \
  --concurrency 24 \
  --tts-concurrency 12 \
  --asr-concurrency 1 \
  --max-depth 3 \
  --seed-tags numbers,mixed_lang,unicode,punctuation \
  --t2s \
  --bootstrap-from-accepted \
  --persist-seen \
  --kimi \
  --kimi-timeout-sec 40 \
  --min-cer 0.25 \
  --min-critical 0.6
```

### 2) 纯汉字：古文/多音字（更干净的信号）

```bash
cd /root/autodl-tmp/v3_tts_bug_finder

PYTHONUNBUFFERED=1 python -m tts_bug_finder run \
  --db artifacts_indextts2_polyphone/bugs.sqlite \
  --artifacts artifacts_indextts2_polyphone \
  --tts indextts2 \
  --asr whisper_cli \
  --budget 600 \
  --budget-accepted 60 \
  --time-limit-sec 1800 \
  --concurrency 24 \
  --tts-concurrency 12 \
  --asr-concurrency 1 \
  --max-depth 3 \
  --seed-tags polyphone,guwen \
  --only-hanzi \
  --t2s \
  --bootstrap-from-accepted \
  --persist-seen \
  --kimi \
  --kimi-timeout-sec 40 \
  --min-cer 0.25 \
  --min-critical 0.6
```

## 经验教训（最关键的坑）

- **不要重新下载模型**：
  - 本镜像 HF cache 是完整的：`/root/index-tts/checkpoints/hf_cache`。
  - IndexTTS2 的 `infer_v2.py` 在 import 时会把 `HF_HUB_CACHE` 设成相对路径 `./checkpoints/hf_cache`；因此**必须在 worker 里 `chdir /root/index-tts` 再 import**，否则容易“找不到/想下载/缓存落错地方”。（本仓库的 `indextts2` adapter 已处理）
  - 默认开离线：`INDEXTTS2_OFFLINE=1`（会设置 `HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE`）。

- **GPU 利用率低，通常不是“没用 GPU”，而是 pipeline 没并起来**：
  - IndexTTS2 推理可并行；Whisper 通常是瓶颈且多开容易炸显存。
  - 解决：把并发拆开：`--tts-concurrency` 适当大，`--asr-concurrency` 固定 1，让 TTS 先把 GPU 填满，ASR 顺序慢慢吃。

- **显存被“别的进程”占着会直接限制可开的 worker 数**：
  - 如果有 `api_server.py` 常驻，占用数 GB 显存，会导致 `INDEXTTS2_WORKERS` 开不起来。
  - 推荐：跑 fuzz 时停掉 server，或者把 `INDEXTTS2_WORKERS` 降到 2。

- **QwenEmotion 很吃显存，但在 fuzz 场景基本不需要**：
  - 默认 `INDEXTTS2_DISABLE_QWEN_EMO=1`，会在 worker 内把 `QwenEmotion` 替换成 dummy，避免额外大模型上 GPU。

- **“同音字/繁简体”在中文里很常见，不应该都当 bug**：
  - 规则评分会先筛一遍（数字/否定/截断/重复等更“致命”）。
  - 仍建议开 `--kimi`：语义等价（允许繁简体/标点/口语改写）直接 reject；再做“与已有模式相比是否新颖”过滤，减少重复样本刷屏。

- **日志/DB 的“实时性”**：
  - SQLite 默认在进程退出时 commit；中途你用 `sqlite3` 查不到新增不代表没跑。
  - 观察进度优先看：`artifacts_*/logs/run_*.log` 和 stdout 的 `[ACCEPT]` 行。

- **磁盘空间要留余量**：
  - 每个 accepted 会落盘 WAV；`report --bundle-audio` 会把 WAV base64 内嵌到 HTML，文件会涨得很快。
  - 如果你想“一个目录可下载”，更推荐下面的 **bundle 目录方案**（HTML 引用本地 wav），避免单文件 HTML 过大。

## GPU 参数推荐（经验值）

- 5090 32GB、无其它占用时：`INDEXTTS2_WORKERS=3` 通常安全；若 OOM 先降到 2。
- `--tts-concurrency` 建议 ≈ `INDEXTTS2_WORKERS * 4` 起步（例如 12）。
- `--asr-concurrency=1` 基本是最稳的默认。
- `WHISPER_DEVICE=cuda` + `WHISPER_FP16=1`（不然浪费 GPU）。

## 产物与打包（一个目录直接下载）

### 生成单份报告（单个 run）

```bash
python -m tts_bug_finder report \
  --db artifacts_indextts2_live/bugs.sqlite \
  --out artifacts_indextts2_live/report.html \
  --status accepted \
  --bundle-audio
```

注意：`--bundle-audio` 会把音频塞进 HTML，方便单文件拷走，但体积会变大。

### 生成“目录版”HTML（index.html + wav 同目录，便于下载）

使用本仓库脚本：`scripts/bundle_accepted_html.py`。

```bash
cd /root/autodl-tmp/v3_tts_bug_finder

python scripts/bundle_accepted_html.py \
  --out indextts2_accepted_bundle \
  --title "IndexTTS2 Accepted Bugs (GT vs ASR + WAV)"
```

输出目录结构：
- `indextts2_accepted_bundle/index.html`
- `indextts2_accepted_bundle/*.wav`
- `indextts2_accepted_bundle/cases.jsonl`（manifest）

## 常见“有趣 bug”类型（用于选 seed/tag）

- `numbers`：金额/日期/时间/百分比/科学计数法/公式（如 `2^10`, `1e-3`）、带分隔符的数字（`404/500/502`）被误读成“分之”结构等。
- `mixed_lang`：`config.yaml`、`PAID`、URL、参数名（``--max-retry=3``）被拆读/重写。
- `unicode`：全角、零宽字符、不间断空格、同形异码（西里尔/希腊字母）触发读法漂移。
- `polyphone/guwen`：古文短句+多音字上下文（更容易出现“关键字替换”）。

