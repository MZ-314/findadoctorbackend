import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, doctors, patients, hospitals, staff, ai

app = FastAPI(title="FindADoctor API", version="2.0")

default_origins = [
    "http://localhost:5173",
    "https://findadoctorfrontend.vercel.app",
]

cors_origins_env = os.getenv("CORS_ORIGINS", "").strip()
allow_origins = (
    [o.strip() for o in cors_origins_env.split(",") if o.strip()]
    if cors_origins_env
    else default_origins
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    # Allow Vercel preview deploy URLs like:
    # https://findadoctorfrontend-git-branch-mz-314.vercel.app
    allow_origin_regex=r"^https:\/\/findadoctorfrontend(-.+)?\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(doctors.router)
app.include_router(patients.router)
app.include_router(hospitals.router)
app.include_router(staff.router)
app.include_router(ai.router)

@app.get("/")
def root():
    return {"message": "FindADoctor API v2.0 is running"}