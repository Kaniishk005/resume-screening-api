from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.security import get_current_user
from app.models.user import User
from app.schemas.resume import ResumeResponse
from app.services.parser import ResumeParsingError, parse_resume
from app.services.uploads import UploadValidationError, temporary_pdf

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post("/upload", response_model=ResumeResponse)
def upload_resume(
    file: UploadFile = File(...), current_user: User = Depends(get_current_user)
):

    try:
        with temporary_pdf(file) as file_path:
            parsed = parse_resume(file_path)
    except UploadValidationError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except ResumeParsingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "filename": file.filename,
        "candidate_name": parsed["candidate_name"],
        "email": parsed["email"],
        "phone": parsed["phone"],
        "skills": parsed["skills"],
        "extracted_text": parsed["extracted_text"],
    }
