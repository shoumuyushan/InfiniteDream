"""Script parser — language detection and duration estimation."""

from __future__ import annotations

import re

from infinite_dream.models.project import Script


class ScriptParser:
    """Parse raw script text, detect language, and estimate duration."""

    # Chinese characters Unicode range
    _CJK_RE = re.compile(
        r"[\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6df"
        r"\U0002a700-\U0002b73f\U0002b740-\U0002b81f\U0002b820-\U0002ceaf]"
    )

    # Approximate reading speeds
    _ZH_CHARS_PER_MIN = 250
    _EN_WORDS_PER_MIN = 150

    def parse(self, raw_text: str, title: str = "") -> Script:
        """Parse raw script text into a Script object.

        * Detects language (zh / en) based on CJK character ratio.
        * Estimates narration duration in seconds.
        """
        text = raw_text.strip()
        if not text:
            return Script(title=title, content=text, language="zh", estimated_duration_sec=0)

        language = self._detect_language(text)
        duration = self._estimate_duration(text, language)

        return Script(
            title=title or self._infer_title(text),
            content=text,
            language=language,
            estimated_duration_sec=duration,
        )

    # ── Internal helpers ──────────────────────────

    def _detect_language(self, text: str) -> str:
        """Return 'zh' if the text is predominantly Chinese, else 'en'."""
        cjk_count = len(self._CJK_RE.findall(text))
        # Count non-whitespace non-punctuation chars as total
        alpha_count = sum(1 for ch in text if ch.isalpha())
        if alpha_count == 0:
            return "zh"
        ratio = cjk_count / alpha_count
        return "zh" if ratio > 0.3 else "en"

    def _estimate_duration(self, text: str, language: str) -> int:
        """Estimate narration duration in seconds."""
        if language == "zh":
            # Count CJK characters
            char_count = len(self._CJK_RE.findall(text))
            if char_count == 0:
                char_count = len(text.replace(" ", ""))
            minutes = char_count / self._ZH_CHARS_PER_MIN
        else:
            word_count = len(text.split())
            minutes = word_count / self._EN_WORDS_PER_MIN

        return max(1, round(minutes * 60))

    @staticmethod
    def _infer_title(text: str) -> str:
        """Use the first non-empty line as a fallback title."""
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped[:60]
        return "Untitled"
