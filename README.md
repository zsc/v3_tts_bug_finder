# TTS Bug Finder（命令行 demo）

这个仓库实现了一个用于自动搜索 **TTS→ASR 严重失配**样本的 CLI 工具（先按 `AGENTS.md` 做命令行实现）：

`text → TTS → ASR → 对齐/指标 → 评分 → 去重/新颖性 → SQLite → 单文件 HTML 报告`

## 你能得到什么

- `bugs.sqlite`：每条样本包含 `GT(ref)`、`ASR(hyp)`、CER/WER、关键错误（数字/否定/截断/重复）、tags、聚类/签名、音频路径等
- `report.html`：单文件 HTML（内嵌 WAV，可播放），side-by-side 显示 `WAV + GT + ASR`，支持搜索/展开折叠
- 支持长期跑：用 `--persist-seen` + `--bootstrap-from-accepted` 避免“越跑越没新东西”

## 依赖与前提

- Python 3.11+
- 离线/自测：`--tts dummy --asr dummy`（不依赖外部服务）
- 真链路 ASR：需要本机可用的 `whisper` CLI（如 `pip install openai-whisper` 后会有 `whisper` 命令）
- 可选：`kimi` CLI（用于“语义等价过滤 + 新颖性判断”）
- `--t2s`（繁体→简体归一化）：依赖 `opencc-python-reimplemented`（已在 `pyproject.toml` 里声明）
- `--tts qwen3_tts`：需要当前 Python 环境可 import `qwen_tts`、`torch`、`soundfile`

## 快速开始（离线 dummy）

```bash
python -m tts_bug_finder run --budget 300 --concurrency 8
python -m tts_bug_finder export --out artifacts/exports/accepted.jsonl
python -m tts_bug_finder report --db artifacts/bugs.sqlite --out artifacts/report.html --status accepted --bundle-audio
```

## 真链路（macOS `say` → `whisper`）

```bash
python -m tts_bug_finder run --tts macos_say --asr whisper_cli --budget 120 --budget-accepted 20 --concurrency 2
python -m tts_bug_finder report --db artifacts/bugs.sqlite --out artifacts/report.html --status accepted --bundle-audio
```

## 真链路（Qwen3-TTS 0.6B → `whisper`）

```bash
# 进程内常驻模型（比直接起外部 cli 更适合长期跑）
python -m tts_bug_finder run --tts qwen3_tts --asr whisper_cli --budget 30 --concurrency 1
```

可用环境变量配置：

- `QWEN3_TTS_DEVICE=auto|mps|cuda|cpu`
- `QWEN3_TTS_SPEAKER=Vivian`
- `QWEN3_TTS_MODEL=Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice`
- `QWEN3_TTS_LANGUAGE=Chinese`
- `QWEN3_TTS_INSTRUCT=...`（可空）

## 多音字 / 古文专项（纯汉字）

只跑多音字与古文 seed，并强制队列文本不含数字/拉丁字母（尽量隔离“纯汉字多音字问题”）：

```bash
python -m tts_bug_finder run \
  --db artifacts_polyphone/bugs.sqlite \
  --artifacts artifacts_polyphone \
  --tts macos_say \
  --asr whisper_cli \
  --concurrency 2 \
  --time-limit-sec 300 \
  --seed-tags polyphone,guwen \
  --only-hanzi \
  --min-cer 0.25 \
  --max-depth 4 \
  --t2s \
  --persist-seen \
  --bootstrap-from-accepted \
  --kimi

python -m tts_bug_finder report \
  --db artifacts_polyphone/bugs.sqlite \
  --out artifacts_polyphone/report.html \
  --status accepted \
  --bundle-audio
```

## 关键开关说明

- `--kimi`：用外部 `kimi` CLI 做两件事：
  - 过滤 GT/ASR “语义等价”（允许繁简体/标点差异/口语改写；不允许关键事实变化）
  - 判断新样本相对已有 accepted 模式是否“有新颖性”（不是两两比较，而是把已有模式放进上下文）
- `--t2s`：Whisper 经常出繁体；开启后会做繁简体归一化，避免把“只是繁体”当 bug
- `--seed-tags`：只选带某些 tags 的种子作为初始队列（例如 `polyphone,guwen`）
- `--only-hanzi`：只保留“无数字/无拉丁字母”的队列文本
- `--persist-seen`：把已评估过的文本写入 `seen_texts`，跨轮次避免重复评估
- `--bootstrap-from-accepted`：每轮从历史 accepted 的 cluster 代表里再做变异，保证长期跑仍能探索新例子

## 生成一个“所有有趣例子都在里面”的 HTML

`report` 支持一次合并多个 DB：

```bash
python -m tts_bug_finder report \
  --db artifacts_real/bugs.sqlite artifacts_real_more2/bugs.sqlite artifacts_polyphone/bugs.sqlite \
  --out artifacts_report/report.html \
  --status accepted \
  --bundle-audio
```

提示：`--status accepted,duplicate` 可把 duplicate 也一起放进报告里。

## 长期跑（循环脚本）

```bash
chmod +x scripts/long_run_macos_whisper.sh
./scripts/long_run_macos_whisper.sh
```

脚本通过环境变量控制（示例：多音字/古文专项）：

```bash
TTS_KIND=macos_say SEED_TAGS=polyphone,guwen ONLY_HANZI=1 MIN_CER=0.25 ./scripts/long_run_macos_whisper.sh
```

切换 Qwen3-TTS：

```bash
TTS_KIND=qwen3_tts CONCURRENCY=1 SEED_TAGS=polyphone,guwen ONLY_HANZI=1 MIN_CER=0.25 ./scripts/long_run_macos_whisper.sh
```

## 输出目录结构（默认）

```
artifacts/
  audio/
  bugs.sqlite
  exports/
  logs/
  report.html
```

## 运行测试

```bash
python -m unittest discover -s tests -p 'test_*.py' -q
```
