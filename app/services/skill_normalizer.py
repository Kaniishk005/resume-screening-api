"""Deterministic canonical skill extraction with safe phrase boundaries."""

from __future__ import annotations

from dataclasses import dataclass
import re

from app.data.skill_taxonomy import SKILL_TAXONOMY


@dataclass(frozen=True)
class SkillEvidence:
    canonical_skill: str
    matched_text: str
    start: int
    end: int
    section: str | None = None

    def __getitem__(self, key: str):
        """Offer convenient mapping-style access for API/service callers."""

        return getattr(self, key)

    def as_dict(self) -> dict[str, str | int | None]:
        return {
            "canonical_skill": self.canonical_skill,
            "matched_text": self.matched_text,
            "start": self.start,
            "end": self.end,
            "section": self.section,
        }


def normalize_skill_name(skill: str) -> str | None:
    """Return the canonical name for a skill alias, or ``None`` if unknown."""

    cleaned = re.sub(r"\s+", " ", skill.strip().casefold())
    if not cleaned:
        return None
    for canonical, aliases in SKILL_TAXONOMY.items():
        if cleaned == canonical.casefold() or cleaned in {a.casefold() for a in aliases}:
            return canonical
    return None


def _alias_pattern(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias.casefold())
    # Alphanumeric boundaries prevent C in Cloud and Java in JavaScript.  The
    # extra punctuation guard is important for C/C++/C# where + and # are not
    # alphanumeric but are still part of the language token.
    punctuation_guard = r"(?![+#])" if alias.casefold() == "c" else ""
    return re.compile(rf"(?<![a-z0-9]){escaped}{punctuation_guard}(?![a-z0-9])", re.IGNORECASE)


def extract_skill_evidence(text: str, *, section: str | None = None) -> list[SkillEvidence]:
    """Find canonical skills and the exact source text that supported them.

    Overlapping aliases are resolved by preferring the longest alias and then
    the taxonomy order, yielding deterministic, non-duplicated evidence.
    """

    candidates: list[tuple[int, int, int, str, str]] = []
    for taxonomy_index, (canonical, aliases) in enumerate(SKILL_TAXONOMY.items()):
        for alias in aliases:
            for match in _alias_pattern(alias).finditer(text):
                candidates.append((match.start(), match.end(), -len(alias), canonical, match.group()))

    selected: list[tuple[int, int, str, str]] = []
    # Start positions and longest aliases first.  A match occupying the same
    # source span as another alias is only represented once.
    for start, end, _negative_length, canonical, matched in sorted(
        candidates, key=lambda item: (item[0], item[2], item[1], item[3])
    ):
        if any(start < existing_end and end > existing_start for existing_start, existing_end, _, _ in selected):
            continue
        selected.append((start, end, canonical, matched))

    selected.sort(key=lambda item: (item[0], item[1], item[2]))
    return [
        SkillEvidence(
            canonical_skill=canonical,
            matched_text=matched,
            start=start,
            end=end,
            section=section,
        )
        for start, end, canonical, matched in selected
    ]


def extract_normalized_skills(text: str) -> list[str]:
    """Return unique canonical skills in stable alphabetical order."""

    return sorted({evidence.canonical_skill for evidence in extract_skill_evidence(text)})


# Small compatibility alias for callers that use the shorter service name.
extract_skills = extract_normalized_skills

