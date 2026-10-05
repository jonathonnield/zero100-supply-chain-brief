#!/usr/bin/env python3
"""Build a daily Zero100-relevant supply-chain technology brief from public RSS."""

import datetime as dt
import os
import re
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

import feedparser
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

AZ = ZoneInfo("America/Phoenix")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIEFS = os.path.join(ROOT, "briefs")

FEEDS = [
    ("Supply Chain Dive", "https://www.supplychaindive.com/feeds/news/"),
    ("FreightWaves", "https://www.freightwaves.com/news/feed"),
    ("The Loadstar", "https://theloadstar.com/feed/"),
    ("Port Technology", "https://www.porttechnology.org/feed/"),
    ("Logistics Management", "https://www.logisticsmgmt.com/rss"),
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
]

KEYWORDS = {
    "agentic": 3, "artificial intelligence": 2, " ai ": 2, "automation": 2, "robot": 2,
    "warehouse": 2, "3pl": 2, "freight": 2, "visibility": 2, "digital twin": 3,
    "control tower": 3, "scope 3": 3, "port": 1, "container": 1, "eta": 1,
    "semiconductor": 2, "data center": 2, "acquisition": 2, "software": 1,
    "last-mile": 2, "autonomous": 2, "iot": 2, "inventory": 1, "procurement": 1,
}

NAVY = colors.HexColor("#0E1C2F")
TEAL = colors.HexColor("#1F6F6A")
INK = colors.HexColor("#1C2430")
MUTED = colors.HexColor("#5C6773")
LINE = colors.HexColor("#D5D0C6")
ROW = colors.HexColor("#F7F5F1")


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_time(entry):
    for key in ("published", "updated"):
        raw = entry.get(key)
        if not raw:
            continue
        try:
            stamp = parsedate_to_datetime(raw)
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=dt.timezone.utc)
            return stamp.astimezone(dt.timezone.utc)
        except (TypeError, ValueError, IndexError):
            pass
    return None


def engagement(title, summary):
    blob = f" {title} {summary} ".lower()
    hits = sum(weight for word, weight in KEYWORDS.items() if word in blob)
    score = 4 + min(hits, 6)
    if any(w in blob for w in ("acquisition", "merger", "billion")):
        score += 1
    if any(w in blob for w in ("agentic", "digital twin", "control tower", "scope 3")):
        score += 1
    return max(1, min(10, score))


def band(score):
    if score >= 8:
        return "High"
    if score >= 6:
        return "Medium"
    return "Watch"


def collect():
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(hours=24)
    items = []
    errors = []
    for source, url in FEEDS:
        try:
            parsed = feedparser.parse(url)
        except Exception as exc:
            errors.append(f"{source}: {exc}")
            continue
        if getattr(parsed, "bozo", False) and not parsed.entries:
            errors.append(f"{source}: feed unavailable")
            continue
        for entry in parsed.entries[:25]:
            stamp = parse_time(entry)
            if stamp is None or stamp < cutoff:
                continue
            title = clean(entry.get("title"))
            summary = clean(entry.get("summary", ""))[:500]
            link = entry.get("link", "")
            if not title:
                continue
            items.append({
                "source": source,
                "title": title,
                "summary": summary,
                "link": link,
                "stamp": stamp,
                "score": engagement(title, summary),
            })
    items.sort(key=lambda row: (row["score"], row["stamp"]), reverse=True)
    seen = set()
    unique = []
    for row in items:
        key = row["title"].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique[:12], errors


def write_markdown(path, when, items, errors):
    lines = [
        f"# Zero100 supply-chain technology brief \u2014 {when.strftime('%d %B %Y')}",
        "",
        f"Window: last 24 hours ending {when.strftime('%H:%M')} America/Phoenix. Scope: global.",
        "Engagement score is the chance a customer might want a Zero100 conversation, not a stock call.",
        "",
        "| Score | Signal | Source |",
        "| --- | --- | --- |",
    ]
    if not items:
        lines.append("| \u2014 | No feed items cleared the 24-hour filter. | \u2014 |")
    for row in items:
        lines.append(
            f"| {row['score']}/10 {band(row['score'])} | {row['title']} | {row['source']} |"
        )
    lines.append("")
    for row in items:
        lines.append(f"## {row['title']} \u2014 {row['score']}/10")
        lines.append("")
        lines.append(f"{row['source']} \u00b7 {row['stamp'].astimezone(AZ).strftime('%d %b %Y %H:%M %Z')}")
        lines.append("")
        if row["summary"]:
            lines.append(row["summary"])
            lines.append("")
        if row["link"]:
            lines.append(row["link"])
            lines.append("")
        lines.append(
            "Why a customer might call: score reflects technology novelty, capital or operating-model stakes, "
            "and fit with AI execution, 3PL data, automation, or network design."
        )
        lines.append("")
    if errors:
        lines.append("## Feed notes")
        lines.append("")
        for err in errors:
            lines.append(f"- {err}")
    lines.append("")
    lines.append("Independent scan. Not Zero100 research or advice.")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def write_pdf(path, when, items, errors):
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName="Times-Roman", fontSize=9.5, leading=12.4, textColor=INK)
    small = ParagraphStyle("small", parent=body, fontSize=8, textColor=MUTED, leading=10.4)
    cell = ParagraphStyle("cell", parent=body, fontSize=8, leading=10.2)
    cellb = ParagraphStyle("cellb", parent=cell, fontName="Times-Bold", textColor=NAVY)
    title = ParagraphStyle("title", parent=body, fontName="Times-Bold", fontSize=16, leading=19, textColor=NAVY)

    def header_footer(canvas, doc):
        canvas.saveState()
        w, h = letter
        canvas.setFillColor(NAVY)
        canvas.rect(0, h - 28, w, 28, fill=1, stroke=0)
        canvas.setFillColor(TEAL)
        canvas.rect(0, h - 31, w, 3, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Times-Bold", 8)
        canvas.drawString(0.7 * inch, h - 18, "ZERO100  |  CUSTOMER RELEVANCE BRIEF")
        canvas.setFont("Times-Roman", 8)
        canvas.drawRightString(w - 0.7 * inch, h - 18, when.strftime("%d %B %Y") + "  \u00b7  Global")
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, w, 24, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Times-Roman", 7.5)
        canvas.drawString(0.7 * inch, 10, "Independent scan. Not Zero100 research or advice.")
        canvas.drawRightString(w - 0.7 * inch, 10, f"Page {doc.page}")
        canvas.restoreState()

    story = [
        Paragraph("DAILY SUPPLY CHAIN TECHNOLOGY SCAN", ParagraphStyle("k", parent=body, textColor=TEAL, fontName="Times-Bold", fontSize=8.5)),
        Paragraph("Emerging logistics technology, last 24 hours", title),
        Paragraph(
            f"Window ending {when.strftime('%H:%M')} America/Phoenix. Scope: global. "
            "Score is the estimated chance a CSCO or COO would want a Zero100 conversation on the topic.",
            small,
        ),
        Spacer(1, 8),
    ]
    header = [
        Paragraph('<font color="white"><b>Score</b></font>', cellb),
        Paragraph('<font color="white"><b>Signal</b></font>', cellb),
        Paragraph('<font color="white"><b>Source</b></font>', cellb),
    ]
    data = [header]
    if not items:
        data.append([
            Paragraph("\u2014", cell),
            Paragraph("No feed items cleared the 24-hour filter.", cell),
            Paragraph("\u2014", cell),
        ])
    for row in items:
        data.append([
            Paragraph(f"<b>{row['score']}/10</b> {band(row['score'])}", cellb),
            Paragraph(row["title"], cell),
            Paragraph(row["source"], cell),
        ])
    table = Table(data, colWidths=[1.15 * inch, 4.35 * inch, 1.6 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    story.append(Spacer(1, 10))
    for row in items:
        story.append(Paragraph(f"{row['title']} \u00b7 {row['score']}/10 {band(row['score'])}", ParagraphStyle("h", parent=body, fontName="Times-Bold", fontSize=11, textColor=NAVY, spaceBefore=8)))
        story.append(Paragraph(f"{row['source']} \u00b7 {row['stamp'].astimezone(AZ).strftime('%d %b %Y %H:%M %Z')}", small))
        if row["summary"]:
            story.append(Paragraph(row["summary"], body))
        story.append(Paragraph(
            "Why a customer might call: the score weights technology novelty, capital or operating-model stakes, and fit with AI execution, 3PL data, automation, or network design.",
            body,
        ))
    if errors:
        story.append(Paragraph("Feed notes: " + "; ".join(errors), small))
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=0.68 * inch, rightMargin=0.68 * inch, topMargin=0.62 * inch, bottomMargin=0.48 * inch)
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)


def main():
    os.makedirs(BRIEFS, exist_ok=True)
    when = dt.datetime.now(AZ)
    items, errors = collect()
    stamp = when.strftime("%Y-%m-%d")
    write_markdown(os.path.join(BRIEFS, f"{stamp}.md"), when, items, errors)
    write_pdf(os.path.join(BRIEFS, f"{stamp}.pdf"), when, items, errors)
    print(f"Wrote {len(items)} items to briefs/{stamp}.pdf")


if __name__ == "__main__":
    main()
