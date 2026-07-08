import os
import shutil

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.security import get_current_user
from app.models.user import User
from app.schemas.resume import ResumeResponse
from app.services.parser import parse_resume

router = APIRouter(prefix="/resume", tags=["Resume"])


UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@router.post("/upload", response_model=ResumeResponse)
def upload_resume(
    file: UploadFile = File(...), current_user: User = Depends(get_current_user)
):

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    parsed = parse_resume(file_path)

    return {
        "filename": file.filename,
        "candidate_name": parsed["candidate_name"],
        "email": parsed["email"],
        "phone": parsed["phone"],
        "skills": parsed["skills"],
        "extracted_text": parsed["text"],
    }
