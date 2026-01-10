import sys, os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.interview_route import router as interview_router
from routes.auth_routes import router as auth_router

app = FastAPI(title = "AI Interviewer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register the routes
app.include_router(interview_router)
app.include_router(auth_router)

@app.get("/")
def health():
    return {"status": "active", "service":"Authentication Service"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)