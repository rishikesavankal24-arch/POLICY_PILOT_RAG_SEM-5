from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TARGET_CHARS = 2200
MAX_CHARS = 3500
MIN_CHARS = 120

CHUNKS_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "processed"
    / "chunks"
)


# ---------------------------------------------------------------------------
# Structural patterns
# ---------------------------------------------------------------------------

CHAPTER_PATTERN = re.compile(
    r"^\s*CHAPTER\s+[IVXLCDM0-9]+\b(?:\s+.*)?$",
    re.IGNORECASE,
)

ANNEX_PATTERN = re.compile(
    r"^\s*Annex\b.*$",
    re.IGNORECASE,
)

APPENDIX_PATTERN = re.compile(
    r"^\s*Appendix\b.*$",
    re.IGNORECASE,
)

NUMBERED_SECTION_PATTERN = re.compile(
    r"(?<![\w.])"
    r"(?P<number>\d{1,3}[A-Z]?)"
    r"\.\s+"
)

SUBCLAUSE_PATTERN = re.compile(
    r"(?<!\w)"
    r"\((?P<label>[a-z]|[ivxlcdm]+)\)"
    r"\s+",
    re.IGNORECASE,
)

PENDING_HEADING_PATTERN = re.compile(
    r"^\s*(?:"
    r"Applicability|"
    r"Definitions|"
    r"Scope|"
    r"Objective|"
    r"Purpose|"
    r"Background|"
    r"Interpretation|"
    r"Exceptions?|"
    r"Notes?"
    r")\s*:?\s*$",
    re.IGNORECASE,
)

TABLE_HEADER_PATTERN = re.compile(
    r"\bSl\.\s*No\.\s*(?:\||).*?\bSubject\b",
    re.IGNORECASE,
)

CONTENTS_MARKER_PATTERN = re.compile(r"\bContents\b", re.IGNORECASE)

INTRODUCTION_MARKER_PATTERN = re.compile(
    r"(?<![\w.])1\s+INTRODUCTION\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def reconstruct_embedded_structure(lines: List[str]) -> List[str]:
    """Restore table row boundaries when extraction flattened the same tables."""

    if len(lines) < 20:
        return lines

    anchor_index = max(range(len(lines)), key=lambda i: len(lines[i]))
    anchor = lines[anchor_index]

    if len(anchor) < 100_000:
        return lines

    # Only table-related secondary lines are candidates for reinsertion.
    # This avoids reintroducing duplicated TOC/navigation blocks.
    candidate_indices = []

    for i, line in enumerate(lines):
        if i == anchor_index:
            continue

        if "|" in line:
            candidate_indices.append(i)

    if not candidate_indices:
        return lines

    # Include an immediately adjacent non-table line as a table header or
    # footnote when it is part of the same extracted table block.
    expanded = set(candidate_indices)

    for i in candidate_indices:
        if i - 1 >= 0 and i - 1 != anchor_index:
            expanded.add(i - 1)

        if i + 1 < len(lines) and i + 1 != anchor_index:
            expanded.add(i + 1)

    candidate_indices = sorted(expanded)

    cursor = 0
    replacements = []

    for i in candidate_indices:
        line = lines[i]

        flat = re.sub(
            r"\s*\|\s*",
            " ",
            line,
        ).strip()

        if not flat:
            continue

        position = anchor.find(
            flat,
            cursor,
        )

        if position < 0:
            return lines

        replacements.append(
            (
                position,
                position + len(flat),
                line,
            )
        )

        cursor = position + len(flat)

    rebuilt = anchor

    for start, end, line in reversed(replacements):
        rebuilt = (
            rebuilt[:start]
            + line
            + "\n"
            + rebuilt[end:]
        )

    unmatched = [
        line
        for i, line in enumerate(lines)
        if i != anchor_index
        and i not in candidate_indices
        and line
        and line not in {anchor}
        and not (
            len(line) < 200
            and line in rebuilt
        )
    ]

    # The dominant line is the authoritative source for non-table content;
    # secondary lines that were not part of table extraction are normally
    # duplicated TOC/navigation representations. Keep only genuinely unique
    # unmatched content.
    return unmatched + [rebuilt]


def clean_text(text: str) -> str:
    """
    Normalize extraction artifacts while preserving the available
    document text.

    RBI HTML extraction can flatten an entire notification into one
    physical line, so this function deliberately does NOT require
    newline boundaries.
    """

    text = text.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    # Known extraction artifact in the recovery-agent document.
    text = text.replace(
        "persistently 1 calling",
        "persistently calling",
    )

    raw_lines = text.split("\n")

    raw_lines = reconstruct_embedded_structure(
        raw_lines
    )

    text = "\n".join(raw_lines)

    text = remove_contents_navigation(text)

    raw_lines = text.split("\n")

    cleaned_lines: List[str] = []

    for raw_line in raw_lines:
        line = re.sub(
            r"[ \t]+",
            " ",
            raw_line,
        ).strip()

        if line:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


# ---------------------------------------------------------------------------
# Navigation and chapter structure
# ---------------------------------------------------------------------------

def remove_contents_navigation(text: str) -> str:
    """
    Remove a flattened table-of-contents block while preserving the
    official document header and the substantive policy body.
    """

    contents = CONTENTS_MARKER_PATTERN.search(text)

    if not contents:
        return text

    introduction = INTRODUCTION_MARKER_PATTERN.search(
        text,
        contents.end(),
    )

    if not introduction:
        return text

    header = text[:contents.start()].rstrip()

    body = text[introduction.start():].lstrip()

    if not header:
        return text

    return f"{header}\n{body}"


def find_real_chapter_boundaries(
    text: str,
) -> List[re.Match[str]]:
    """
    Find substantive chapter headings after the document's actual
    introduction, ignoring chapter names appearing in the TOC.
    """

    introduction = INTRODUCTION_MARKER_PATTERN.search(
        text
    )

    search_start = (
        introduction.start()
        if introduction
        else 0
    )

    matches: List[re.Match[str]] = []

    pattern = re.compile(
        r"(?<!\w)CHAPTER\s+"
        r"(?P<number>[IVXLCDM0-9]+)\b",
        re.IGNORECASE,
    )

    for match in pattern.finditer(
        text,
        search_start,
    ):
        after = text[match.end():]

        paragraph = re.search(
            r"(?<![\w.])\d{1,3}[A-Z]?\.\s+",
            after,
        )

        # Use the first numbered provision as the natural end of the heading.
        # Some chapters begin with Part I/II labels, so a paragraph marker is
        # preferred but not required for boundary recognition.
        heading_tail = (
            after[:paragraph.start()].strip()
            if paragraph
            else after[:200].strip()
        )

        # Real chapter headings are short, heading-like text. References such
        # as "Chapter IV of the PML Act, 2002. ..." occur inside provisions and
        # therefore fail these heading checks.
        if not heading_tail or len(heading_tail) > 150:
            continue

        if re.search(
            r"[.;,:]",
            heading_tail,
        ):
            continue

        # Do not reject ordinary words such as "under" or "in": they can
        # legitimately occur in chapter titles. Punctuation and length are
        # the safer signals for distinguishing prose references.
        matches.append(match)

    return matches


def extract_chapter_label(
    text: str,
    match: re.Match[str],
    next_boundary: Optional[int] = None,
) -> str:
    """
    Extract the chapter heading text without consuming its first paragraph.
    """

    limit = (
        next_boundary
        if next_boundary is not None
        else len(text)
    )

    after = text[
        match.end():limit
    ]

    paragraph = re.search(
        r"(?<![\w.])\d{1,3}[A-Z]?\.\s+",
        after,
    )

    end = (
        match.end() + paragraph.start()
        if paragraph
        else limit
    )

    heading = normalize_inline_spacing(
        text[match.start():end]
    )

    # KYC Chapter VI is followed inline by "Part I - ..."; that is a
    # subordinate structure, not part of the chapter title.
    heading = re.sub(
        r"\s+Part\s+[IVXLCDM0-9]+\s*-.*$",
        "",
        heading,
        flags=re.IGNORECASE,
    ).strip()

    return heading


# ---------------------------------------------------------------------------
# Basic structure helpers
# ---------------------------------------------------------------------------

def is_chapter(line: str) -> bool:
    return bool(
        CHAPTER_PATTERN.match(line)
    )


def is_annex(line: str) -> bool:
    return bool(
        ANNEX_PATTERN.match(line)
    )


def is_appendix(line: str) -> bool:
    return bool(
        APPENDIX_PATTERN.match(line)
    )


def is_heading(line: str) -> bool:
    return (
        is_chapter(line)
        or is_annex(line)
        or is_appendix(line)
        or bool(
            PENDING_HEADING_PATTERN.match(line)
        )
    )


def normalize_inline_spacing(
    text: str,
) -> str:
    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\s+\.",
        ".",
        text,
    )

    return text.strip()


# ---------------------------------------------------------------------------
# Annex detection
# ---------------------------------------------------------------------------

def find_real_annex_boundaries(
    text: str,
) -> List[re.Match[str]]:
    """Find actual Annex headings and ignore ordinary references/TOC runs."""

    annex_pattern = re.compile(
        r"(?<!\w)\bAnnex\b"
        r"(?:\s+(?P<label>[IVXLCDM]+))?",
        re.IGNORECASE,
    )

    annexes: List[re.Match[str]] = []

    for match in annex_pattern.finditer(text):
        after = text[
            match.end():match.end() + 100
        ].lstrip()

        if after.startswith(
            (".", ",", ";", ":")
        ):
            continue

        if re.match(
            r"(?:Annex|Appendix)\b",
            after,
            re.IGNORECASE,
        ):
            continue

        if re.match(
            r"(?:of|this|the|will|shall|is|under|and)\b",
            after,
            re.IGNORECASE,
        ):
            continue

        annexes.append(match)

    appendix_pattern = re.compile(
        r"(?<!\w)\bAppendix\b",
        re.IGNORECASE,
    )

    appendices = []

    for match in appendix_pattern.finditer(
        text
    ):
        after = text[
            match.end():match.end() + 100
        ].lstrip()

        if re.match(
            r"(?:Annex|Appendix)\b",
            after,
            re.IGNORECASE,
        ):
            continue

        if re.match(
            r"(?:of|this|the|will|shall|is|under|and)\b",
            after,
            re.IGNORECASE,
        ):
            continue

        appendices.append(match)

    # The KYC extraction contains a TOC Appendix before the real Annexes.
    # Treat an Appendix as a structural boundary only after Annex material
    # has begun; this also keeps ordinary references out of the split.
    if annexes:
        first_annex = annexes[0]

        later_appendices = [
            m
            for m in appendices
            if m.start() > first_annex.start()
        ]

        if later_appendices:
            boundaries = (
                annexes
                + [later_appendices[0]]
            )

            return sorted(
                boundaries,
                key=lambda m: m.start(),
            )

        return annexes

    if appendices:
        return [appendices[0]]

    table_pattern = re.compile(
        r"(?<!\w)Sl\.\s*No\.\s*\|"
        r"\s*Circular\s+No\.\s*\|"
        r"\s*Date\s*\|"
        r"\s*Subject",
        re.IGNORECASE,
    )

    table_match = table_pattern.search(
        text
    )

    return (
        [table_match]
        if table_match
        else []
    )


def find_real_annex_boundary(
    text: str,
) -> Optional[re.Match[str]]:
    """Backward-compatible single-boundary helper."""

    boundaries = find_real_annex_boundaries(
        text
    )

    return (
        boundaries[0]
        if boundaries
        else None
    )


# ---------------------------------------------------------------------------
# Numbered policy parsing
# ---------------------------------------------------------------------------

def find_numbered_sections(
    text: str,
) -> List[re.Match[str]]:
    """Find policy paragraph markers, excluding ordinary numeric references."""

    reference_prefix = re.compile(
        r"(?:paragraph|para|section|rule|"
        r"clause|page|item|table)\s*$",
        re.IGNORECASE,
    )

    matches: List[re.Match[str]] = []

    for match in NUMBERED_SECTION_PATTERN.finditer(
        text
    ):
        prefix = text[
            max(0, match.start() - 30):
            match.start()
        ]

        if reference_prefix.search(prefix):
            continue

        matches.append(match)

    return matches


def _split_numbered_segment(
    text: str,
    chapter: Optional[str],
) -> List[Dict[str, Optional[str]]]:
    """Split one chapter/non-chapter segment into policy paragraphs."""

    text = text.strip()

    if not text:
        return []

    matches = find_numbered_sections(
        text
    )

    if not matches:
        return [
            {
                "chapter": chapter,
                "section": None,
                "text": text,
            }
        ]

    units: List[
        Dict[str, Optional[str]]
    ] = []

    prefix = text[
        :matches[0].start()
    ].strip()

    if prefix:
        units.append(
            {
                "chapter": chapter,
                "section": None,
                "text": prefix,
            }
        )

    for index, match in enumerate(
        matches
    ):
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        )

        body = text[
            match.end():end
        ].strip()

        if body:
            units.append(
                {
                    "chapter": chapter,
                    "section": (
                        f"Paragraph "
                        f"{match.group('number')}"
                    ),
                    "text": body,
                }
            )

    return units


def split_main_policy_body(
    text: str,
) -> List[Dict[str, Optional[str]]]:
    """
    Split the non-Annex policy body into numbered policy paragraphs while
    preserving substantive chapter context.
    """

    text = text.strip()

    if not text:
        return []

    chapters = find_real_chapter_boundaries(
        text
    )

    if not chapters:
        return _split_numbered_segment(
            text,
            None,
        )

    units: List[
        Dict[str, Optional[str]]
    ] = []

    # Material before the first substantive chapter (for example INTRODUCTION
    # and any preliminary text) has no chapter context.
    prefix = text[
        :chapters[0].start()
    ].strip()

    if prefix:
        units.extend(
            _split_numbered_segment(
                prefix,
                None,
            )
        )

    for index, chapter_match in enumerate(
        chapters
    ):
        segment_end = (
            chapters[index + 1].start()
            if index + 1 < len(chapters)
            else len(text)
        )

        chapter_label = extract_chapter_label(
            text,
            chapter_match,
            segment_end,
        )

        segment = text[
            chapter_match.end():segment_end
        ].strip()

        # Remove the chapter heading itself. Because extraction can flatten
        # the heading and first paragraph onto one line, locate the first
        # paragraph marker within this chapter segment.
        first_paragraph = re.search(
            r"(?<![\w.])\d{1,3}[A-Z]?\.\s+",
            segment,
        )

        if first_paragraph:
            segment = segment[
                first_paragraph.start():
            ].strip()

        if segment:
            units.extend(
                _split_numbered_segment(
                    segment,
                    chapter_label,
                )
            )

    return units


# ---------------------------------------------------------------------------
# Main structural parser
# ---------------------------------------------------------------------------

def split_into_policy_units(
    text: str,
) -> List[Dict[str, Optional[str]]]:
    """Convert extracted policy text into structural policy units."""

    text = clean_text(text)

    if not text:
        return []

    annex_boundaries = (
        find_real_annex_boundaries(text)
    )

    main_body = (
        text[
            :annex_boundaries[0].start()
        ].strip()
        if annex_boundaries
        else text
    )

    units = split_main_policy_body(
        main_body
    )

    for index, boundary in enumerate(
        annex_boundaries
    ):
        end = (
            annex_boundaries[index + 1].start()
            if index + 1 < len(annex_boundaries)
            else len(text)
        )

        annex_body = text[
            boundary.start():end
        ].strip()

        if not annex_body:
            continue

        label = (
            boundary.groupdict().get("label")
        )

        if (
            boundary.group(0).lower()
            == "appendix"
        ):
            section = "Appendix"
        else:
            section = (
                f"Annex {label.upper()}"
                if label
                else "Annex"
            )

        units.append(
            {
                "chapter": None,
                "section": section,
                "text": annex_body,
            }
        )

    return units


# ---------------------------------------------------------------------------
# Large-unit splitting
# ---------------------------------------------------------------------------

def split_by_subclauses(
    text: str,
    chapter: Optional[str],
    section: Optional[str],
) -> List[Dict[str, Optional[str]]]:
    """
    Split an oversized policy unit at subclauses where possible.
    """

    matches = []

    for match in SUBCLAUSE_PATTERN.finditer(
        text
    ):
        prefix = text[
            max(0, match.start() - 4):
            match.start()
        ]

        if not re.search(
            r"[:.;]\s*$",
            prefix,
        ):
            continue

        matches.append(match)

    if len(matches) <= 1:
        return split_by_sentences(
            text,
            chapter,
            section,
        )

    parts: List[
        Dict[str, Optional[str]]
    ] = []

    prefix = text[
        :matches[0].start()
    ].strip()

    if prefix:
        parts.append(
            {
                "chapter": chapter,
                "section": section,
                "text": prefix,
            }
        )

    for index, match in enumerate(
        matches
    ):
        start = match.start()

        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        )

        body = text[
            start:end
        ].strip()

        if body:
            parts.append(
                {
                    "chapter": chapter,
                    "section": section,
                    "text": body,
                }
            )

    if len(parts) <= 1:
        return split_by_sentences(
            text,
            chapter,
            section,
        )

    sized_parts: List[
        Dict[str, Optional[str]]
    ] = []

    for part in parts:
        body = part.get("text") or ""

        if len(body) <= MAX_CHARS:
            sized_parts.append(part)
            continue

        sized_parts.extend(
            split_by_sentences(
                body,
                chapter,
                section,
            )
        )

    return sized_parts


def split_by_sentences(
    text: str,
    chapter: Optional[str],
    section: Optional[str],
) -> List[Dict[str, Optional[str]]]:
    """
    Size-based fallback for unusually large policy units.
    """

    if len(text) <= MAX_CHARS:
        return [
            {
                "chapter": chapter,
                "section": section,
                "text": text,
            }
        ]

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text,
    )

    parts: List[
        Dict[str, Optional[str]]
    ] = []

    current: List[str] = []
    current_length = 0

    for sentence in sentences:
        sentence = sentence.strip()

        if not sentence:
            continue

        proposed_length = (
            current_length
            + len(sentence)
            + (1 if current else 0)
        )

        if (
            current
            and proposed_length > TARGET_CHARS
        ):
            parts.append(
                {
                    "chapter": chapter,
                    "section": section,
                    "text": " ".join(current),
                }
            )

            current = []
            current_length = 0

        current.append(sentence)

        current_length += (
            len(sentence)
            + (1 if current_length else 0)
        )

    if current:
        parts.append(
            {
                "chapter": chapter,
                "section": section,
                "text": " ".join(current),
            }
        )

    # Absolute fallback.
    final_parts: List[
        Dict[str, Optional[str]]
    ] = []

    for part in parts:
        body = part["text"]

        if body is None:
            continue

        if len(body) <= MAX_CHARS:
            final_parts.append(part)
            continue

        for start in range(
            0,
            len(body),
            TARGET_CHARS,
        ):
            piece = body[
                start:start + MAX_CHARS
            ].strip()

            if piece:
                final_parts.append(
                    {
                        "chapter": chapter,
                        "section": section,
                        "text": piece,
                    }
                )

    return final_parts


def split_structured_rows(
    text: str,
    chapter: Optional[str],
    section: Optional[str],
) -> List[Dict[str, Optional[str]]]:
    """Pack table rows without splitting a row across chunks."""

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines or not any(
        "|" in line
        for line in lines
    ):
        return split_by_sentences(
            text,
            chapter,
            section,
        )

    parts: List[
        Dict[str, Optional[str]]
    ] = []

    current: List[str] = []
    current_length = 0

    for line in lines:
        proposed = (
            current_length
            + len(line)
            + (1 if current else 0)
        )

        if (
            current
            and proposed > TARGET_CHARS
        ):
            parts.append(
                {
                    "chapter": chapter,
                    "section": section,
                    "text": "\n".join(current),
                }
            )

            current = []
            current_length = 0

        current.append(line)

        current_length += (
            len(line)
            + (1 if current_length else 0)
        )

    if current:
        parts.append(
            {
                "chapter": chapter,
                "section": section,
                "text": "\n".join(current),
            }
        )

    final: List[
        Dict[str, Optional[str]]
    ] = []

    for part in parts:
        body = part["text"] or ""

        if len(body) <= MAX_CHARS:
            final.append(part)
        else:
            final.extend(
                split_by_sentences(
                    body,
                    chapter,
                    section,
                )
            )

    return final


def expand_units(
    units: List[Dict[str, Optional[str]]],
) -> List[Dict[str, Optional[str]]]:
    """Apply size control only after structural units are identified."""

    expanded: List[
        Dict[str, Optional[str]]
    ] = []

    for unit in units:
        text = unit.get("text") or ""
        chapter = unit.get("chapter")
        section = unit.get("section")

        if len(text) <= MAX_CHARS:
            expanded.append(unit)
            continue

        if (
            section == "Appendix"
            or (section or "").startswith("Annex")
        ):
            if "|" in text:
                expanded.extend(
                    split_structured_rows(
                        text,
                        chapter,
                        section,
                    )
                )
                continue

        subparts = split_by_subclauses(
            text,
            chapter,
            section,
        )

        expanded.extend(subparts)

    return expanded


# ---------------------------------------------------------------------------
# Chunk metadata
# ---------------------------------------------------------------------------

def make_chunk_id(
    document_id: str,
    text: str,
    chunk_index: int,
    unit_index: int,
    part_index: int,
) -> str:
    """
    Deterministic position-aware chunk ID.

    The chunk position is included so that distinct chunks with
    identical text do not produce the same primary key.
    """

    normalized = normalize_inline_spacing(
        text
    )

    raw = (
        f"{document_id}|"
        f"{chunk_index}|"
        f"{unit_index}|"
        f"{part_index}|"
        f"{normalized}"
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:16]


def unit_to_chunk(
    unit: Dict[str, Optional[str]],
    document_id: str,
    document: str,
    source: str,
    source_type: str,
    source_url: str,
    chunk_index: int,
    unit_index: int,
    part_index: int,
) -> Dict:
    """
    Convert an internal policy unit into the canonical chunk schema.
    """

    text = normalize_inline_spacing(
        unit.get("text") or ""
    )

    return {
        "chunk_id": make_chunk_id(
            document_id,
            text,
            chunk_index,
            unit_index,
            part_index,
        ),
        "document_id": document_id,
        "document": document,
        "source": source,
        "source_type": source_type,
        "source_url": source_url,
        "chapter": unit.get("chapter"),
        "section": unit.get("section"),
        "page": None,
        "location": None,
        "chunk_index": chunk_index,
        "part_index": part_index,
        "unit_index": unit_index,
        "text": text,
    }


# ---------------------------------------------------------------------------
# Public document-processing API
# ---------------------------------------------------------------------------

def chunk_document(
    text: str,
    document_id: str,
    document: str,
    source: str,
    source_type: str,
    source_url: str,
) -> List[Dict]:
    """
    Main canonical chunking function.

    Pipeline:

        clean text
        -> structural policy units
        -> size control
        -> canonical metadata
        -> deterministic chunk IDs
    """

    units = split_into_policy_units(text)

    units = expand_units(units)

    chunks: List[Dict] = []

    chunk_index = 0

    for unit_index, unit in enumerate(units):
        text_value = (
            unit.get("text") or ""
        ).strip()

        if not text_value:
            continue

        chunk = unit_to_chunk(
            unit=unit,
            document_id=document_id,
            document=document,
            source=source,
            source_type=source_type,
            source_url=source_url,
            chunk_index=chunk_index,
            unit_index=unit_index,
            part_index=0,
        )

        chunks.append(chunk)

        chunk_index += 1

    return chunks