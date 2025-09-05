from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import action_logs

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(action_logs.router) 