from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sys, os
from chatbot.components.bot_flow.bot_logic import InterviewLoop
from chatbot.components.judge.judge_logic import InterviewJudge
from chatbot.components.exception.exception import ChatbotException
from chatbot.components.src_logging.logger import logging
from database import models
from database.database import get_db

router = APIRouter(prefix="/api/interview", tags=["interview"])

ACTIVE_SESSIONS: Dict[str, Any] = {}

# Data Validation
class StartRequest(BaseModel):
    username: str
    role: str
    resume_text: Optional[str] = None

class ChatRequest(BaseModel):
    username: str
    message: str

class FeedbackRequest(BaseModel):
    username: str

# Endpoints

@router.post("/start")
async def start_interview(request: StartRequest, db: Session = Depends(get_db)):
    bot = InterviewLoop(request.role, request.resume_text)
    
    user = db.query(models.User).filter(models.User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # NEW: Update User's default resume if a new one is provided
    if request.resume_text:
        user.resume_text = request.resume_text
        db.commit() # Save to User table

    # Create DB Record
    new_interview = models.Interview(
        user_id=user.id,
        job_role=request.role,
        resume_text=request.resume_text or user.resume_text # Use saved if current is empty
    )
    db.add(new_interview)
    db.commit()
    db.refresh(new_interview)

    ACTIVE_SESSIONS[request.username] = {
        "bot": bot,
        "interview_id": new_interview.id 
    }

    return {"message": "Interview Started", "session_id": new_interview.id}
    
@router.post("/chat")
async def chat_turn(request: ChatRequest):
    try:
        if request.username not in ACTIVE_SESSIONS:
            raise HTTPException(status_code=404, detail="Session expired.")
        
        session = ACTIVE_SESSIONS[request.username]
        bot = session["bot"]
        ai_response = bot.process_turn(request.message)

        return {
            "reply": ai_response,
            "is_finished": "INTERVIEW_FINISHED" in ai_response or "Interview Finished" in ai_response or "Verdict:" in ai_response
        }
    except Exception as e:
        raise ChatbotException(e, sys)
    
@router.post("/feedback")
async def get_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    try:
        if request.username not in ACTIVE_SESSIONS:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = ACTIVE_SESSIONS[request.username]
        bot = session_data["bot"]
        interview_db_id = session_data["interview_id"]

        # Judge
        transcript = bot.get_transcript_str()
        judge = InterviewJudge()
        report = judge.evaluate_interview(transcript)

        # save to db
        interview_record = db.query(models.Interview).filter(models.Interview.id == interview_db_id).first()
        if interview_record:
            interview_record.score = report.get("score", 0)
            interview_record.verdict = report.get("verdict", "N/A")
            interview_record.feedback_summary = report.get("summary", "")
            db.commit()
        
        return report
    except Exception as e:
        raise ChatbotException(e, sys)