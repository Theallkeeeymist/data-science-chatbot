import os, sys, json, hashlib
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime

from chatbot.components.exception.exception import ChatbotException
from chatbot.components.src_logging.logger import logging
from database import models
from database.database import get_db, engine

models.Base.metadata.create_all(bind = engine)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# USER_DB_FILE = "users.json"

# Pydantic Models
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str

class UpdateRoleRequest(BaseModel):
    username: str
    new_role: str

class InterviewHistoryItem(BaseModel):
    id: int
    job_role: str
    score: Optional[int]
    verdict: Optional[str]
    date: datetime

class ProfileResponse(BaseModel):
    username: str
    current_role: str
    history: List[InterviewHistoryItem]

# Password Hash helper
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# def load_users():
#     try:
#         if not os.path.exists(USER_DB_FILE):
#             return {}
#         try:
#             with open(USER_DB_FILE, "r") as f:
#                 return json.load(f)
#         except json.JSONDecodeError:
#             return{}
#     except Exception as e:
#         raise ChatbotException(e, sys)

# def save_users(users):
#     with open(USER_DB_FILE, "w") as f:
#         json.dump(users, f, indent=4)

# Endpoints
@router.post("/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    try:
        # 1. Check if user exists
        existing_user = db.query(models.User).filter(models.User.username == request.username).first()
        if existing_user:
            # Raise the error and let it escape immediately
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # 2. Create new user
        new_user = models.User(
            username=request.username,
            password_hash=hash_password(request.password),
            current_role=request.role
        )
        db.add(new_user)
        db.commit()
        return {"message": "User created successfully"}
        
    except HTTPException as he:
        # IMPORTANT: Re-raise HTTP exceptions so FastAPI handles them correctly
        raise he
    except Exception as e:
        # Only wrap UNEXPECTED errors in your custom exception
        raise ChatbotException(e, sys)

@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == request.username).first()
    
    if not user or user.password_hash != hash_password(request.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {
        "message": "Login Successful", 
        "user_id": user.username, 
        "role": user.current_role,
        "resume_text": user.resume_text  # <--- SEND RESUME TO FRONTEND
    }
    
@router.get("/profile/{username}", response_model=ProfileResponse)
async def get_profile(username: str, db: Session = Depends(get_db)):
    try:
        user = db.query(models.User).filter(models.User.username == username).first()

        if not user:
            logging.info("User not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        history_items = []
        for i in user.interviews:
            history_items.append(InterviewHistoryItem(
                id = i.id,
                job_role = i.job_role,
                score = i.score,
                verdict = i.verdict,
                date = i.created_at
            ))
        logging.info("History item added")
        
        return ProfileResponse(
            username=user.username,
            current_role=user.current_role,
            history=history_items
        )
    except Exception as e:
        raise ChatbotException(e, sys)

@router.get("/profile/role")
async def update_role(request: UpdateRoleRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == request.username).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.current_role = request.new_role
    db.commit()

    return{"message": "Role updated", "new_role": user.current_role}