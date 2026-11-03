"""Few-shot từ train/ (US3). Chỉ truyền `type` của câu tương tự (train chỉ có đáp án, khác
business → giá trị đáp án dễ gây nhiễu). Độ giống = Jaccard token đã bỏ dấu. Chỉ train/ có
answers.jsonl nên from_train_dir tự chặn nguồn test (FR-009)."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


def _tokens(text: str) -> frozenset[str]:
    decomposed = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return frozenset(re.findall(r"[a-z0-9]+", stripped))


def _load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


_HEADER = "## Câu hỏi tương tự trong bộ huấn luyện (chỉ để tham khảo kiểu đáp án)"


class FewShotPool:
    def __init__(self, items: list[dict]):
        self._items = [{**item, "tokens": _tokens(item["question"])} for item in items]

    @classmethod
    def from_train_dir(cls, train_dir: Path) -> "FewShotPool":
        answers_path = Path(train_dir) / "answers.jsonl"
        if not answers_path.exists():
            raise ValueError(f"Thiếu answers.jsonl trong {train_dir} — few-shot chỉ lấy từ train/")
        types = {a["id"]: a["type"] for a in _load_jsonl(answers_path)}
        items = [
            {"question": q["question"], "type": types[q["id"]]}
            for q in _load_jsonl(Path(train_dir) / "questions.jsonl")
            if q["id"] in types
        ]
        return cls(items)

    def select(self, question: str, k: int, exclude_questions: frozenset[str] = frozenset()) -> list[dict]:
        if k <= 0:
            return []
        query = _tokens(question)
        scored = []
        for item in self._items:
            text = item["question"]
            if text == question or text in exclude_questions or not item["tokens"]:
                continue
            union = query | item["tokens"]
            scored.append((-len(query & item["tokens"]) / len(union), text, item["type"]))
        scored.sort()

        picked, seen = [], set()
        for _, text, type_name in scored:
            if text in seen:
                continue
            seen.add(text)
            picked.append({"question": text, "type": type_name})
            if len(picked) == k:
                break
        return picked

    def format_prompt(
        self, question: str, k: int, exclude_questions: frozenset[str] = frozenset(), max_chars: int | None = None
    ) -> str:
        text = _HEADER
        for example in self.select(question, k, exclude_questions):
            line = f'- "{example["question"]}" → type={example["type"]}'
            candidate = f"{text}\n{line}"
            if max_chars is not None and len(candidate) > max_chars:
                break
            text = candidate
        return "" if text == _HEADER else text
