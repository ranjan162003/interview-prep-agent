"""Build the notebook's PDF "revision book" with ReportLab.

Layout: cover → contents → one chapter per topic (subtopic sections, key points first,
then each item in full) → a final "Weak spots" chapter with every mistake in one place.
`notes_only` keeps just titles and key points: a short cheat sheet for the night before.

ReportLab's built-in fonts cover Western European text (cp1252); the few symbols models
like to use outside that (arrows, ≤, ✓) are swapped for plain equivalents.
"""
from __future__ import annotations

import io
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)

from app.db.orm_models import LearningItemRow
from app.learning.item_status import LearningItemKind, LearningStatus
from app.schemas.track_schemas import SubtopicLocation

KIND_LABELS = {
    LearningItemKind.CONCEPT.value: "Concept",
    LearningItemKind.QUIZ_QUESTION.value: "Quiz",
    LearningItemKind.CODING_PROBLEM.value: "Coding problem",
    LearningItemKind.SECURITY_LAB.value: "Security lab",
    LearningItemKind.MOCK_QUESTION.value: "Mock interview",
}
SINGULAR_LABELS = {"Quiz": "quiz question", "Mock interview": "mock interview question"}
PLURAL_LABELS = {"Quiz": "quiz questions", "Mock interview": "mock interview questions"}
CODE_LINE_WIDTH = 92
ACCENT = colors.HexColor("#4f46e5")
MUTED = colors.HexColor("#5b6178")
WEAK = colors.HexColor("#b42318")

_SYMBOLS = {
    "→": "->", "←": "<-", "⇒": "=>", "↔": "<->", "≤": "<=", "≥": ">=", "≠": "!=", "≈": "~",
    "✓": "[yes]", "✔": "[yes]", "✗": "[no]", "✘": "[no]", "×": "x", "−": "-", "∞": "infinity",
    "√": "sqrt", "∑": "sum", "π": "pi", "λ": "lambda", "Θ": "Theta", "Ω": "Omega", " ": " ",
}


@dataclass
class NotebookPdfOptions:
    track_name: str
    date_from: date | None
    date_to: date | None
    notes_only: bool
    generated_on: date


def clean(text: str) -> str:
    """Make text safe for ReportLab's standard fonts."""
    for symbol, plain in _SYMBOLS.items():
        text = text.replace(symbol, plain)
    return text.encode("cp1252", errors="replace").decode("cp1252")


def inline(text: str) -> str:
    """Markdown inline (**bold**, *italic*, `code`) → ReportLab paragraph markup."""
    text = escape(clean(text))
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", text)
    return text


class _Styles:
    def __init__(self) -> None:
        base = getSampleStyleSheet()
        body = ParagraphStyle("Body", parent=base["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13.5, spaceAfter=4)
        self.body = body
        self.muted = ParagraphStyle("Muted", parent=body, textColor=MUTED, fontSize=8.5)
        self.bullet = ParagraphStyle("Bullet", parent=body, leftIndent=12, bulletIndent=2, spaceAfter=2)
        self.label = ParagraphStyle("Label", parent=body, fontName="Helvetica-Bold", fontSize=9, textColor=ACCENT, spaceBefore=6, spaceAfter=2)
        self.md_heading = ParagraphStyle("MdHeading", parent=body, fontName="Helvetica-Bold", fontSize=10, spaceBefore=6)
        self.code = ParagraphStyle("Code", parent=body, fontName="Courier", fontSize=7.8, leading=10, leftIndent=6,
                                   backColor=colors.HexColor("#f3f4f8"), borderPadding=4, spaceBefore=3, spaceAfter=6)
        self.chapter = ParagraphStyle("Chapter", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=18, textColor=ACCENT, spaceAfter=8)
        self.section = ParagraphStyle("Section", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13, spaceBefore=10, spaceAfter=4)
        self.item_title = ParagraphStyle("ItemTitle", parent=body, fontName="Helvetica-Bold", fontSize=10.5, spaceBefore=8, spaceAfter=1)
        self.cover_title = ParagraphStyle("CoverTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=28, leading=34, alignment=TA_CENTER, textColor=ACCENT)
        self.cover_sub = ParagraphStyle("CoverSub", parent=body, fontSize=12, leading=18, alignment=TA_CENTER, textColor=MUTED)


def markdown_flowables(text: str, styles: _Styles) -> list:
    """The small Markdown subset the agents write: ### headings, bullets, ``` code, paragraphs."""
    flowables: list = []
    paragraph: list[str] = []
    code: list[str] | None = None

    def flush_paragraph() -> None:
        if paragraph:
            flowables.append(Paragraph(inline(" ".join(paragraph)), styles.body))
            paragraph.clear()

    for line in text.replace("\r\n", "\n").split("\n"):
        if line.strip().startswith("```"):
            if code is None:
                flush_paragraph()
                code = []
            else:
                flowables.append(Preformatted(clean("\n".join(code)), styles.code, maxLineLength=CODE_LINE_WIDTH))
                code = None
            continue
        if code is not None:
            code.append(line)
            continue
        stripped = line.strip()
        heading = re.match(r"^#{1,6}\s+(.*)$", stripped)
        bullet = re.match(r"^(?:[-*•]|\d+[.)])\s+(.*)$", stripped)
        if not stripped:
            flush_paragraph()
        elif heading:
            flush_paragraph()
            flowables.append(Paragraph(inline(heading.group(1)), styles.md_heading))
        elif bullet:
            flush_paragraph()
            flowables.append(Paragraph(inline(bullet.group(1)), styles.bullet, bulletText="•"))
        else:
            paragraph.append(stripped)
    flush_paragraph()
    if code:
        flowables.append(Preformatted(clean("\n".join(code)), styles.code, maxLineLength=CODE_LINE_WIDTH))
    return flowables


def _bullets(points: list[str], styles: _Styles) -> list:
    return [Paragraph(inline(p), styles.bullet, bulletText="•") for p in points if p]


def _label(text: str, styles: _Styles) -> Paragraph:
    return Paragraph(escape(text), styles.label)


def _code(text: str, styles: _Styles) -> Preformatted:
    return Preformatted(clean(text.rstrip()), styles.code, maxLineLength=CODE_LINE_WIDTH)


def _item_header(item: LearningItemRow, styles: _Styles) -> list:
    meta = [KIND_LABELS.get(item.kind, item.kind), item.created_at.strftime("%d %b %Y")]
    if item.is_review:
        meta.append("review")
    if item.attempts:
        meta.append(f"score {round(item.attempts[-1].score)}%")
    if item.status == LearningStatus.WEAK:
        meta.append("needs review")
    return [
        Paragraph(inline(item.title), styles.item_title),
        Paragraph(escape(" · ".join(meta)), styles.muted),
    ]


def _item_details(item: LearningItemRow, styles: _Styles) -> list:
    content = item.content
    last = item.attempts[-1] if item.attempts else None
    grade = (last.grade or {}) if last else {}
    out: list = []

    if item.kind == LearningItemKind.CONCEPT:
        out += markdown_flowables(str(content.get("lesson_markdown", "")), styles)
        out += [_label("Explain-back question", styles), Paragraph(inline(str(content.get("explain_prompt", ""))), styles.body)]
        if last:
            out += [_label(f"Your answer ({round(last.score)}%)", styles), *markdown_flowables(last.answer_text, styles)]
            if grade.get("missed_points"):
                out += [_label("You missed", styles), *_bullets(grade["missed_points"], styles)]
        if item.reference_answer:
            out += [_label("Model answer", styles), *markdown_flowables(item.reference_answer, styles)]
        if item.chat_messages:
            out.append(_label("Your questions to the teacher", styles))
            for message in item.chat_messages:
                if message.role == "user":
                    out.append(Paragraph(f"<b>Q:</b> {inline(message.content)}", styles.body))
                else:
                    out += markdown_flowables(message.content, styles)

    elif item.kind == LearningItemKind.QUIZ_QUESTION:
        options = content.get("options", [])
        correct = content.get("correct_index")
        chosen = last.selected_index if last else None
        for index, option in enumerate(options):
            marks = (" (correct)" if index == correct else "") + (" (your answer)" if index == chosen else "")
            out.append(Paragraph(f"{chr(65 + index)}. {inline(option)}<b>{escape(marks)}</b>", styles.bullet))
        if content.get("explanation"):
            out += [_label("Why", styles), Paragraph(inline(content["explanation"]), styles.body)]

    elif item.kind == LearningItemKind.CODING_PROBLEM:
        out += markdown_flowables(str(content.get("statement_markdown", "")), styles)
        if last:
            out += [_label(f"Your final code ({grade.get('passed', '?')}/{grade.get('total', '?')} tests)", styles), _code(last.answer_text, styles)]
            review = grade.get("review") or {}
            if review:
                out.append(Paragraph(
                    inline(f"Complexity: time {review.get('time_complexity', '?')}, space {review.get('space_complexity', '?')}. {review.get('complexity_comment', '')}"),
                    styles.body,
                ))
                if review.get("edge_cases_missed"):
                    out += [_label("Edge cases missed", styles), *_bullets(review["edge_cases_missed"], styles)]
        if item.reference_answer:
            out += [
                _label(f"Reference solution (time {content.get('time_complexity', '?')}, space {content.get('space_complexity', '?')})", styles),
                _code(item.reference_answer, styles),
            ]

    elif item.kind == LearningItemKind.SECURITY_LAB:
        out += markdown_flowables(str(content.get("scenario_markdown", "")), styles)
        out += [_label(f"Evidence ({content.get('artifact_type', 'artifact')})", styles), _code(str(content.get("artifact", "")), styles)]
        answers = last.answer_text.split("\n\n") if last else []
        for number, task in enumerate(content.get("tasks", []), start=1):
            out.append(Paragraph(f"<b>Task {number}:</b> {inline(task.get('question', ''))}", styles.body))
            if number <= len(answers):
                out.append(Paragraph(f"<i>You:</i> {inline(answers[number - 1])}", styles.bullet))
            out.append(Paragraph(f"<i>Expected:</i> {inline(task.get('expected_answer', ''))}", styles.bullet))
        if item.reference_answer:
            out += [_label("Walkthrough", styles), *markdown_flowables(item.reference_answer, styles)]

    elif item.kind == LearningItemKind.MOCK_QUESTION:
        if last:
            out += [_label(f"Your interview ({round(last.score)}%)", styles), *markdown_flowables(last.answer_text, styles)]
            if grade.get("improved_answer"):
                out += [_label("A stronger answer", styles), *markdown_flowables(grade["improved_answer"], styles)]
        elif item.reference_answer:
            out += [_label("Model answer", styles), *markdown_flowables(item.reference_answer, styles)]
    return out


def build_notebook_pdf(items: list[LearningItemRow], syllabus: list[SubtopicLocation], options: NotebookPdfOptions) -> bytes:
    styles = _Styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"PrepPilot revision book: {options.track_name}", author="PrepPilot",
    )

    by_subtopic: dict[str, list[LearningItemRow]] = defaultdict(list)
    for item in items:
        by_subtopic[item.subtopic_id].append(item)
    topics: dict[str, tuple[str, list[SubtopicLocation]]] = {}
    for location in syllabus:
        if by_subtopic.get(location.subtopic.id):
            topics.setdefault(location.topic.id, (location.topic.name, []))[1].append(location)

    story: list = []
    # ---- cover ----
    span = _date_span(options)
    kinds = defaultdict(int)
    for item in items:
        kinds[KIND_LABELS.get(item.kind, item.kind)] += 1
    story += [
        Spacer(1, 60 * mm),
        Paragraph("PrepPilot", styles.cover_sub),
        Paragraph("Revision notes" if options.notes_only else "Revision book", styles.cover_title),
        Spacer(1, 6 * mm),
        Paragraph(escape(f"{options.track_name} · {span}"), styles.cover_sub),
        Paragraph(escape(", ".join(_count_label(count, label) for label, count in kinds.items()) or "Nothing learnt yet"), styles.cover_sub),
        Paragraph(escape(f"Generated {options.generated_on.strftime('%d %B %Y')}"), styles.cover_sub),
        PageBreak(),
    ]

    if not items:
        story.append(Paragraph("No items match these filters yet. Practise a little, then export again.", styles.body))
        doc.build(story)
        return buffer.getvalue()

    # ---- contents ----
    story.append(Paragraph("Contents", styles.chapter))
    for number, (name, locations) in enumerate(topics.values(), start=1):
        count = sum(len(by_subtopic[loc.subtopic.id]) for loc in locations)
        story.append(Paragraph(f"{number}. {inline(name)} <font color='#5b6178'>({count} items)</font>", styles.body))
    weak_items = [item for item in items if item.status == LearningStatus.WEAK]
    if weak_items:
        story.append(Paragraph(f"{len(topics) + 1}. Weak spots <font color='#5b6178'>({len(weak_items)} items)</font>", styles.body))
    story.append(PageBreak())

    # ---- chapters ----
    for number, (name, locations) in enumerate(topics.values(), start=1):
        story.append(Paragraph(f"{number}. {inline(name)}", styles.chapter))
        for location in locations:
            subtopic_items = by_subtopic[location.subtopic.id]
            story.append(Paragraph(inline(location.subtopic.name), styles.section))
            key_points = [p for item in subtopic_items for p in item.key_points]
            if key_points:
                story.append(KeepTogether([_label("Key points", styles), *_bullets(key_points, styles)]))
            if options.notes_only:
                continue
            for item in subtopic_items:
                story += _item_header(item, styles)
                story += _item_details(item, styles)
        story.append(PageBreak())

    # ---- weak spots ----
    if weak_items:
        story.append(Paragraph(f"{len(topics) + 1}. Weak spots", styles.chapter))
        story.append(Paragraph("Everything you scored low on, in one place. Revise these first.", styles.muted))
        for item in weak_items:
            story += _item_header(item, styles)
            grade = (item.attempts[-1].grade or {}) if item.attempts else {}
            missed = grade.get("missed_points") or [m for t in grade.get("tasks", []) for m in t.get("missed", [])]
            if missed:
                story += [_label("What you missed", styles), *_bullets(missed, styles)]
            story += _bullets(item.key_points, styles)

    doc.build(story, onFirstPage=lambda *_: None, onLaterPages=_page_footer(options))
    return buffer.getvalue()


def _count_label(count: int, label: str) -> str:
    if count == 1:
        return f"1 {SINGULAR_LABELS.get(label, label.lower())}"
    return f"{count} {PLURAL_LABELS.get(label, label.lower() + 's')}"


def _date_span(options: NotebookPdfOptions) -> str:
    if options.date_from and options.date_to:
        return f"{options.date_from:%d %b %Y} to {options.date_to:%d %b %Y}"
    if options.date_from:
        return f"since {options.date_from:%d %b %Y}"
    if options.date_to:
        return f"up to {options.date_to:%d %b %Y}"
    return "everything learnt to date"


def _page_footer(options: NotebookPdfOptions):
    def draw(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 10 * mm, clean(f"PrepPilot · {options.track_name}"))
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    return draw
