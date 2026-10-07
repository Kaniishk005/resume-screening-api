import json
from typing import Any

from groq import Groq
from pydantic import BaseModel, ValidationError

from app.core.config import settings

class AIFeedbackPayload(BaseModel):
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    recommendation: str


class AIServiceError(RuntimeError):
    """Raised when the configured AI provider cannot return valid feedback."""


def _get_client() -> Groq:
    if not settings.GROQ_API_KEY:
        raise AIServiceError("AI feedback service is not configured.")
    return Groq(
        api_key=settings.GROQ_API_KEY,
        timeout=settings.GROQ_TIMEOUT_SECONDS,
        max_retries=0,
    )


def _parse_feedback(content: Any) -> dict:
    if not isinstance(content, str):
        raise AIServiceError("AI provider returned an invalid response.")
    try:
        payload = json.loads(content)
        return AIFeedbackPayload.model_validate(payload).model_dump()
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise AIServiceError("AI provider returned malformed feedback.") from exc


def generate_feedback(
    resume_text: str, matched_skills: list, missing_skills: list, ats_score: int
):

    prompt = f"""
        You are an expert technical recruiter.

        Analyze the candidate's resume for the given job.

        Resume:

        {resume_text}

        Matched Skills:
        {matched_skills}

        Missing Skills:
        {missing_skills}

        ATS Score:
        {ats_score}

        Return ONLY valid JSON.

        Use this exact schema.

        {{
            "summary":"",

            "strengths":[
                "",
                "",
                ""
            ],

            "weaknesses":[
                "",
                ""
            ],

            "recommendation":""
        }}

        Do not write markdown.

        Do not wrap in ```json.

        Return JSON only.
    """

    client = _get_client()
    last_error: Exception | None = None
    for _ in range(2):
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return _parse_feedback(completion.choices[0].message.content)
        except AIServiceError as exc:
            last_error = exc
        except Exception as exc:
            raise AIServiceError("AI feedback provider is unavailable.") from exc

    raise AIServiceError("AI provider returned malformed feedback.") from last_error
