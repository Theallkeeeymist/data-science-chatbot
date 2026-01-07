import os, sys, json, hashlib
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from chatbot.components.exception.exception import ChatbotException
from chatbot.components.src_logging.logger import logging

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

USER_DB_FILE = "users.json"

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str

def load_users():
    try:
        if not os.path.exists(USER_DB_FILE):
            return {}
        try:
            with open(USER_DB_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return{}
    except Exception as e:
        raise ChatbotException(e, sys)

def save_users(users):
    with open(USER_DB_FILE, "w") as f:
        json.dump(users, f, indent=4)

def hash_passwords(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Endpoints
@router.post("/register")
async def register(request: RegisterRequest):
    users = load_users()

    if request.username in users:
        raise HTTPException(status_code=400, detail="Username Already exists.")
    
    users[request.username] = {
        "password": hash_passwords(request.password),
        "role": request.role
    }
    save_users(users)

    return {"message": "User created successfully"}

@router.post("/login")
async def login(request: LoginRequest):
    users = load_users()

    if request.username not in users:
        raise HTTPException(status_code=401, detail="Invalid Username or Password...")
    
    stored_user = users[request.username]

    if stored_user["password"] != hash_passwords(request.password):
        raise HTTPException(status_code=401, detail="Invalid username or password...")
    
    return {
        "message": "Login Successful",
        "user_id": request.username,
        "role": stored_user["role"]
    }