import re
from typing import NamedTuple, Optional


class CompiledKeyword(NamedTuple):
    raw: str
    is_regex: bool
    pattern: Optional[re.Pattern]


def compile_keywords(keywords: list[str]) -> list[CompiledKeyword]:
    compiled = []
    for kw in keywords:
        if kw.startswith("re:"):
            regex_src = kw[3:]
            try:
                pattern = re.compile(regex_src, re.IGNORECASE)
                compiled.append(CompiledKeyword(raw=kw, is_regex=True, pattern=pattern))
            except re.error as e:
                raise ValueError(f"Invalid regex keyword '{kw}': {e}") from e
        else:
            compiled.append(CompiledKeyword(raw=kw, is_regex=False, pattern=None))
    return compiled


def find_matches(text: str, compiled: list[CompiledKeyword]) -> list[str]:
    if not text:
        return []
    text_lower = text.lower()
    matched = []
    for kw in compiled:
        if kw.is_regex:
            if kw.pattern.search(text):
                matched.append(kw.raw)
        else:
            if kw.raw.lower() in text_lower:
                matched.append(kw.raw)
    return matched
