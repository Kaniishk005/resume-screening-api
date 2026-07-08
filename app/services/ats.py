from typing import List


def calculate_skill_match(required_skills: str, candidate_skills: List[str]):

    required = {
        skill.strip().lower() for skill in required_skills.split(",") if skill.strip()
    }

    candidate = {skill.lower() for skill in candidate_skills}

    matched = sorted(required & candidate)
    missing = sorted(required - candidate)

    if len(required) == 0:
        percentage = 0
    else:
        percentage = round((len(matched) / len(required)) * 100, 2)

    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "match_percentage": percentage,
    }


def calculate_ats_score(match_percentage: float):

    if match_percentage >= 90:
        return 95

    if match_percentage >= 80:
        return 90

    if match_percentage >= 70:
        return 80

    if match_percentage >= 60:
        return 70

    if match_percentage >= 50:
        return 60

    return 40
