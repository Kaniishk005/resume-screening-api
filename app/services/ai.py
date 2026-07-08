import json

from groq import Groq

from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)


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

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    response = completion.choices[0].message.content

    return json.loads(response)
