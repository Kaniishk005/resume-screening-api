"""Backwards-compatible skill export.

New code should use :mod:`app.services.skill_normalizer`; this import keeps
older integrations that import ``app.utils.skills.SKILLS`` working.
"""

from app.data.skill_taxonomy import SKILLS

__all__ = ["SKILLS"]
