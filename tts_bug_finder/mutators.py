from __future__ import annotations

import random
import re
import unicodedata

from .types import MutationCandidate


_DIGIT_TO_ZH = {
    "0": "零",
    "1": "一",
    "2": "二",
    "3": "三",
    "4": "四",
    "5": "五",
    "6": "六",
    "7": "七",
    "8": "八",
    "9": "九",
}

_UNITS = ["℃", "m/s", "km/h", "GB", "MB", "ms", "s", "次/天", "ml", "%", "元", "km"]

_ABBREV = ["CPU", "GPU", "HTTP", "USB", "DNS", "TLS", "JSON", "K8s", "iOS", "Android"]

_EMAILS = ["ops-alert@company.com", "support@company.com", "oncall@company.com"]
_URLS = ["https://example.com/reset?token=abc123", "https://status.example.com/incidents/12345"]

_POLYPHONE_TEMPLATES = [
    "客服说明：银行的行长今天不在，请稍后再来。",
    "行业动态：这家银行的行长发布了新计划。",
    "请按指示行走，别在大厅里逆行。",
    "我们今天行程很紧，先去银行再去车站。",
    "请把行李放到行李架上，别挡住通道。",
    "视频重新上传，不要重复下载。",
    "他说：重做一遍也没关系，但别重复提交。",
    "长辈提醒：长大后要自立，不要好高骛远。",
]


def mutate_numbers(text: str, rng: random.Random) -> list[MutationCandidate]:
    out: list[MutationCandidate] = []
    norm = unicodedata.normalize("NFKC", text)
    digit_spans = list(re.finditer(r"\d[\d,.:/\\-]*\d|\d", norm))
    if digit_spans:
        m = digit_spans[0]
        token = m.group(0)
        digits_only = re.sub(r"\D", "", token)
        if digits_only:
            zh_per_digit = "".join(_DIGIT_TO_ZH.get(ch, ch) for ch in digits_only)
            out.append(
                MutationCandidate(
                    text=norm[: m.start()] + zh_per_digit + norm[m.end() :],
                    mutation_trace=f"numbers:digits_to_zh({token}->{zh_per_digit})",
                    tags=("numbers",),
                )
            )
            fullwidth = token.translate(str.maketrans("0123456789", "０１２３４５６７８９"))
            out.append(
                MutationCandidate(
                    text=norm[: m.start()] + fullwidth + norm[m.end() :],
                    mutation_trace=f"numbers:fullwidth({token}->{fullwidth})",
                    tags=("numbers", "unicode"),
                )
            )

        unit = rng.choice(_UNITS)
        out.append(
            MutationCandidate(
                text=f"{norm}（阈值 {token}{unit}）",
                mutation_trace=f"numbers:append_unit({unit})",
                tags=("numbers",),
            )
        )

        if digits_only:
            if len(digits_only) >= 2:
                dec = digits_only[0] + "." + digits_only[1:]
            else:
                dec = digits_only + ".0"
            out.append(
                MutationCandidate(
                    text=norm[: m.start()] + dec + norm[m.end() :],
                    mutation_trace=f"numbers:inject_decimal({token}->{dec})",
                    tags=("numbers",),
                )
            )
    else:
        sample = rng.choice(["2026-02-20 13:05", "¥1,234,567.89", "0.03%", "3–5 次/天", "v1.0.0-beta"])
        out.append(
            MutationCandidate(
                text=f"{norm}（补充：{sample}）",
                mutation_trace="numbers:append_sample",
                tags=("numbers",),
            )
        )

    version = f"v{rng.randint(0,3)}.{rng.randint(0,9)}.{rng.randint(0,9)}-beta+exp.sha.{rng.randint(10**7,10**8-1):x}"
    out.append(
        MutationCandidate(
            text=f"{norm}（版本号：{version}）",
            mutation_trace="numbers:append_version",
            tags=("numbers", "mixed_lang"),
        )
    )

    return out[:10]


def mutate_punct(text: str, rng: random.Random) -> list[MutationCandidate]:
    out: list[MutationCandidate] = []
    norm = text
    out.append(
        MutationCandidate(
            text=f"提示：{norm}",
            mutation_trace="punct:prefix_hint",
            tags=("punctuation",),
        )
    )
    out.append(
        MutationCandidate(
            text=norm.replace("，", "；", 1) if "，" in norm else norm.replace(",", "—", 1),
            mutation_trace="punct:swap_comma",
            tags=("punctuation",),
        )
    )
    out.append(
        MutationCandidate(
            text=f"“{norm}”",
            mutation_trace="punct:add_quotes",
            tags=("punctuation",),
        )
    )
    out.append(
        MutationCandidate(
            text=f"{norm}……请确认。",
            mutation_trace="punct:add_ellipsis",
            tags=("punctuation",),
        )
    )
    out.append(
        MutationCandidate(
            text=f"{norm}（括号里也要读出来）",
            mutation_trace="punct:add_parentheses",
            tags=("punctuation",),
        )
    )
    rng.shuffle(out)
    return out[:10]


def mutate_mixed_lang(text: str, rng: random.Random) -> list[MutationCandidate]:
    out: list[MutationCandidate] = []
    norm = text
    out.append(
        MutationCandidate(
            text=f"{norm}（错误码：{rng.choice(['HTTP 500', 'HTTP 502', 'E_CONN_RESET'])}）",
            mutation_trace="mixed:append_error_code",
            tags=("mixed_lang",),
        )
    )
    out.append(
        MutationCandidate(
            text=f"{norm} 请发送到 {rng.choice(_EMAILS)}。",
            mutation_trace="mixed:append_email",
            tags=("mixed_lang",),
        )
    )
    out.append(
        MutationCandidate(
            text=f"{norm} 参考链接：{rng.choice(_URLS)}。",
            mutation_trace="mixed:append_url",
            tags=("mixed_lang",),
        )
    )
    abbrev = rng.choice(_ABBREV)
    out.append(
        MutationCandidate(
            text=f"{norm}（重点关注 {abbrev} 指标）",
            mutation_trace="mixed:append_abbrev",
            tags=("mixed_lang",),
        )
    )
    rng.shuffle(out)
    return out[:10]


def mutate_repetition(text: str, rng: random.Random) -> list[MutationCandidate]:
    out: list[MutationCandidate] = []
    norm = text
    if norm:
        first = norm[0]
        out.append(
            MutationCandidate(
                text=f"{first}{first}{norm[1:]}",
                mutation_trace="repeat:stutter_first_char",
                tags=("stutter_laugh",),
            )
        )
    out.append(
        MutationCandidate(
            text=norm.replace("。", "……嗯……。", 1) if "。" in norm else f"{norm}……嗯……",
            mutation_trace="repeat:insert_filler",
            tags=("stutter_laugh",),
        )
    )
    out.append(
        MutationCandidate(
            text=f"{norm} 哈哈哈……别笑了。",
            mutation_trace="repeat:append_laugh",
            tags=("stutter_laugh",),
        )
    )
    phrase = rng.choice(["请确认", "不要泄露", "马上处理", "再说一遍"])
    out.append(
        MutationCandidate(
            text=f"{norm} {phrase}，{phrase}。",
            mutation_trace="repeat:repeat_phrase",
            tags=("repetition",),
        )
    )
    rng.shuffle(out)
    return out[:10]


def mutate_unicode(text: str, rng: random.Random) -> list[MutationCandidate]:
    out: list[MutationCandidate] = []
    norm = unicodedata.normalize("NFKC", text)
    out.append(
        MutationCandidate(
            text=norm.translate(str.maketrans("0123456789", "０１２３４５６７８９")),
            mutation_trace="unicode:fullwidth_digits",
            tags=("unicode",),
        )
    )
    out.append(
        MutationCandidate(
            text=norm.replace(" ", "\u00A0"),
            mutation_trace="unicode:nbsp_spaces",
            tags=("unicode",),
        )
    )
    if len(norm) >= 2:
        pos = rng.randint(1, min(8, len(norm) - 1))
        out.append(
            MutationCandidate(
                text=norm[:pos] + "\u200b" + norm[pos:],
                mutation_trace=f"unicode:insert_zwsp(pos={pos})",
                tags=("unicode",),
            )
        )
    out.append(
        MutationCandidate(
            text=norm.replace("-", "—"),
            mutation_trace="unicode:hyphen_to_emdash",
            tags=("unicode", "punctuation"),
        )
    )
    rng.shuffle(out)
    return out[:10]


def mutate_polyphone_context(text: str, rng: random.Random) -> list[MutationCandidate]:
    _ = rng
    if not any(ch in text for ch in ("行", "重", "长", "还", "乐", "朝", "藏", "单", "解", "薄")):
        return []
    out: list[MutationCandidate] = []
    for i, t in enumerate(_POLYPHONE_TEMPLATES[:10], start=1):
        out.append(
            MutationCandidate(
                text=t,
                mutation_trace=f"polyphone:template_{i:02d}",
                tags=("polyphone",),
            )
        )
    return out


def mutate_all(text: str, tags: tuple[str, ...], rng: random.Random) -> list[MutationCandidate]:
    out: list[MutationCandidate] = []
    out.extend(mutate_numbers(text, rng))
    out.extend(mutate_punct(text, rng))
    out.extend(mutate_mixed_lang(text, rng))
    out.extend(mutate_repetition(text, rng))
    out.extend(mutate_unicode(text, rng))
    if "polyphone" in tags or any(ch in text for ch in ("行", "重", "长", "还", "乐", "朝", "藏")):
        out.extend(mutate_polyphone_context(text, rng))

    seen: set[str] = set()
    deduped: list[MutationCandidate] = []
    for c in out:
        key = unicodedata.normalize("NFKC", c.text).strip()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)
    return deduped[:30]
