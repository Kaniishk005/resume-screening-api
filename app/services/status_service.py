from app.enums.candidate_status import CandidateStatus

VALID_TRANSITIONS = {
    CandidateStatus.NEW: [
        CandidateStatus.SHORTLISTED,
        CandidateStatus.REJECTED
    ],
    CandidateStatus.SHORTLISTED: [
        CandidateStatus.INTERVIEW,
        CandidateStatus.REJECTED
    ],
    CandidateStatus.INTERVIEW: [
        CandidateStatus.HIRED,
        CandidateStatus.REJECTED
    ],
    CandidateStatus.REJECTED: [],
    CandidateStatus.HIRED: []
}


def is_valid_transition(current, new):
    return new in VALID_TRANSITIONS[current]