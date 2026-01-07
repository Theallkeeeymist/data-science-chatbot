from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sys, os
from chatbot.components.bot_flow.bot_logic import InterviewLoop
from chatbot.components.judge.judge_logic import InterviewJudge
from chatbot.components.exception.exception import ChatbotException
from chatbot.components.src_logging.logger import logging

router = APIRouter(prefix="/api/interview", tags=["interview"])

# IN-MEMORY DATABASE
SESSIONS: Dict[str, Any] = {}

# Data Validation
class StartRequest(BaseModel):
    user_id: str
    role: str
    resume_text: Optional[str] = None

class ChatRequest(BaseModel):
    user_id: str
    message: str

class FeedbackRequest(BaseModel):
    user_id: str

# Endpoints

@router.post("/start")
async def start_interview(request: StartRequest):
    try:
        try:
            bot = InterviewLoop(request.role, request.resume_text)

            SESSIONS[request.user_id]={
                "bot": bot,
                "history": bot.chat_history
            }

            return {"message": "Interview Initialized", "session_id": request.user_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise ChatbotException(e, sys)
    
@router.post("/chat")
async def chat_turn(request: ChatRequest):
    try:
        user_id = request.user_id
        if user_id not in SESSIONS:
            raise HTTPException(status_code=404, detail="Session expired or not found. Please Restart")
        
        session = SESSIONS[user_id]
        bot = session["bot"]

        try:
            ai_response = bot.process_turn(request.message)

            session["history"] = bot.chat_history

            return {
                "reply": ai_response,
                "is_finished": "INTERVIEW_FINISHED" in ai_response
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Bot Error: {str(e)}")
    except Exception as e:
        raise ChatbotException(e, sys)
    
@router.post("/feedback")
async def get_feedback(request: FeedbackRequest):
    try:
        user_id = request.user_id

        if user_id not in SESSIONS:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = SESSIONS[user_id]
        bot = session["bot"]

        try:
            transcript = bot.get_transcript_str()

            judge = InterviewJudge()
            report = judge.evaluate_interview(transcript)

            return report
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Judge Error: {str(e)}")
    except Exception as e:
        raise ChatbotException(e, sys)