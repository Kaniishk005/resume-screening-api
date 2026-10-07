from enum import Enum


class CandidateStatus(str, Enum):
    NEW = "NEW"

    SHORTLISTED = "SHORTLISTED"

    INTERVIEW = "INTERVIEW"

    REJECTED = "REJECTED"

    HIRED = "HIRED"