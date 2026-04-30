from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, doctors, patients, hospitals, staff, ai

app = FastAPI(title="FindADoctor API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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