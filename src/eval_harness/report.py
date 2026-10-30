"""Cấu trúc kết quả chấm điểm — xem specs/003-eval-harness/spec.md."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TypeBreakdown:
    correct: int = 0
    incorrect: int = 0
    abstained: int = 0

    def record(self, outcome: str) -> None:
        if outcome == "correct":
            self.correct += 1
        elif outcome == "incorrect":
            self.incorrect += 1
        else:
            self.abstained += 1

    @property
    def total(self) -> int:
        return self.correct + self.incorrect + self.abstained

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


@dataclass
class EvalReport:
    total_score: int
    total_questions: int
    correct: int
    incorrect: int
    abstained: int
    accuracy: float
    by_type: dict[str, TypeBreakdown] = field(default_factory=dict)
    by_business: dict[str, TypeBreakdown] = field(default_factory=dict)
    malformed_count: int = 0
    extra_ids_ignored: int = 0


def format_report(report: EvalReport) -> str:
    lines = [
        f"Tổng điểm: {report.total_score} / {report.total_questions}",
        f"Đúng: {report.correct}  Sai: {report.incorrect}  Bỏ trống: {report.abstained}",
        f"Accuracy: {report.accuracy:.4f}",
        f"Dòng hỏng: {report.malformed_count}  Id lạ bị bỏ qua: {report.extra_ids_ignored}",
        "",
        "Theo type:",
    ]
    for type_name, bd in sorted(report.by_type.items()):
        lines.append(f"  {type_name}: {bd.correct}/{bd.total} ({bd.accuracy:.2%})")
    lines.append("")
    lines.append("Theo business:")
    for business_id, bd in sorted(report.by_business.items()):
        lines.append(f"  {business_id}: {bd.correct}/{bd.total} ({bd.accuracy:.2%})")
    return "\n".join(lines)
