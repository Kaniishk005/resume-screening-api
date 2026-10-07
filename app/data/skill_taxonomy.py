"""Canonical skills and aliases used throughout document intelligence.

This is intentionally a small, human-maintained taxonomy.  It is not meant to
be a complete ontology; keeping it explicit makes every extraction explainable
and easy to extend.
"""

from __future__ import annotations


# The insertion order is stable and the normalizer additionally sorts aliases
# by length.  Keep canonical spellings compatible with the existing API.
SKILL_TAXONOMY: dict[str, tuple[str, ...]] = {
    "Python": ("python",),
    "Java": ("java",),
    "C++": ("c++", "cpp"),
    "C#": ("c#", "c sharp", "csharp"),
    "C": ("c",),
    "JavaScript": ("javascript", "js", "ecmascript"),
    "TypeScript": ("typescript", "ts"),
    "FastAPI": ("fastapi",),
    "Flask": ("flask",),
    "Django": ("django",),
    "Node.js": ("node.js", "nodejs", "node js"),
    "Express": ("express", "express.js", "expressjs"),
    "Spring": ("spring", "spring boot", "springboot"),
    ".NET": (".net", "dotnet", "dot net"),
    "ASP.NET": ("asp.net", "aspnet"),
    "MongoDB": ("mongodb", "mongo db", "mongo"),
    "MySQL": ("mysql", "my sql"),
    "PostgreSQL": ("postgresql", "postgres", "psql", "postgre sql"),
    "SQLite": ("sqlite",),
    "Redis": ("redis",),
    "GraphQL": ("graphql", "graph ql"),
    "REST API": ("rest api", "rest apis", "restful api", "restful apis"),
    "React": ("react", "react.js", "reactjs"),
    "Next.js": ("next.js", "nextjs", "next js"),
    "Vue.js": ("vue.js", "vuejs", "vue js"),
    "Angular": ("angular",),
    "HTML": ("html",),
    "CSS": ("css",),
    "Tailwind CSS": ("tailwind", "tailwind css"),
    "Docker": ("docker",),
    "Kubernetes": ("kubernetes", "k8s"),
    "AWS": ("aws", "amazon web services"),
    "Azure": ("azure", "microsoft azure"),
    "GCP": ("gcp", "google cloud", "google cloud platform"),
    "Git": ("git",),
    "GitHub": ("github",),
    "GitLab": ("gitlab",),
    "CI/CD": ("ci/cd", "ci cd", "continuous integration", "continuous deployment"),
    "Linux": ("linux",),
    "Terraform": ("terraform",),
    "Jenkins": ("jenkins",),
    "Apache Kafka": ("kafka", "apache kafka"),
    "RabbitMQ": ("rabbitmq", "rabbit mq"),
    "TensorFlow": ("tensorflow",),
    "PyTorch": ("pytorch",),
    "Scikit-learn": ("scikit-learn", "scikit learn", "sklearn"),
    "Pandas": ("pandas",),
    "NumPy": ("numpy", "num py"),
    "Machine Learning": ("machine learning", "ml"),
    "Deep Learning": ("deep learning",),
    "Artificial Intelligence": ("artificial intelligence", "ai"),
    "NLP": ("nlp", "natural language processing"),
    "Computer Vision": ("computer vision",),
    "LLM": ("llm", "llms", "large language model", "large language models"),
    "Generative AI": ("generative ai", "genai", "gen ai"),
    "OpenAI": ("openai",),
    "GitHub Actions": ("github actions",),
    "Pytest": ("pytest",),
    "Jest": ("jest",),
    "Selenium": ("selenium",),
    "Unit Testing": ("unit testing", "unit tests", "unit test"),
    "Test-Driven Development": ("tdd", "test-driven development", "test driven development"),
    "OAuth": ("oauth", "oauth2", "oauth 2"),
    "JWT": ("jwt", "json web token", "json web tokens"),
    "SQL": ("sql",),
    "NoSQL": ("nosql", "no sql"),
    "Linux Shell": ("shell scripting", "bash", "shell script"),
}

# Backwards-compatible export used by the original parser and callers.
SKILLS = list(SKILL_TAXONOMY)

