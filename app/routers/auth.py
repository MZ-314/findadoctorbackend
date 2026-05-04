from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db import get_db
from app import models
from app.schemas import (
    UserRegister, UserLogin,
    UserOut, Token, ChangePassword
)
from app.utils.auth import (
    hash_password, verify_password,
    create_access_token, decode_token
)

router = APIRouter(prefix="/auth", tags=["Auth"])
bearer_scheme = HTTPBearer()

FEE_MAP = {"low": 400, "medium": 900, "high": 2500}


# ── Dependency: get current user from JWT ─────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Staff token (no user_id in DB)
    if payload.get("role") == "staff":
        raise HTTPException(status_code=403,
                            detail="Staff must use staff endpoints")

    user_id = payload.get("user_id")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user

def require_role(*roles):
    def checker(current_user: models.User = Depends(get_current_user)):
        if current_user.role.value not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return checker


# ── Register ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    # These roles cannot self-register
    if payload.role.value == "staff":
        raise HTTPException(status_code=400,
                            detail="Staff accounts are provisioned by the company")

    existing = db.query(models.User).filter(
        models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role
    )
    db.add(user)
    db.flush()

    # Doctor registration
    if payload.role.value == "doctor":
        missing = [f for f in ["specialisation", "hospital_id",
                               "experience_years", "languages"]
                   if not getattr(payload, f)]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required doctor fields: {', '.join(missing)}"
            )
        hospital = db.query(models.Hospital).filter(
            models.Hospital.id == payload.hospital_id,
            models.Hospital.verification_status == models.VerificationStatus.approved
        ).first()
        if not hospital:
            raise HTTPException(status_code=400,
                                detail="Invalid or unverified hospital")
        doctor = models.Doctor(
            user_id=user.id,
            hospital_id=payload.hospital_id,
            specialisation=payload.specialisation,
            experience_years=payload.experience_years,
            languages=payload.languages,
            education=payload.education or "",
            bio=payload.bio or "",
            availability="green",
            consultation_fee=FEE_MAP.get(hospital.budget_tier.value, 500),
            avg_rating=0.0,
            review_count=0,
            verification_status=models.VerificationStatus.pending
        )
        db.add(doctor)

    # Hospital admin registration
    elif payload.role.value == "hospital_admin":
        missing = [f for f in ["hospital_name", "hospital_city_id",
                               "hospital_address", "hospital_budget_tier"]
                   if not getattr(payload, f)]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required hospital fields: {', '.join(missing)}"
            )
        city = db.query(models.City).filter(
            models.City.id == payload.hospital_city_id).first()
        if not city:
            raise HTTPException(status_code=400, detail="Invalid city_id")
        hospital = models.Hospital(
            name=payload.hospital_name,
            city_id=payload.hospital_city_id,
            address=payload.hospital_address,
            budget_tier=payload.hospital_budget_tier,
            description=payload.hospital_description,
            phone=payload.hospital_phone,
            email=payload.hospital_email,
            website=payload.hospital_website,
            cleanliness_rating=3.0,
            quality_score=0.0,
            verification_status=models.VerificationStatus.pending,
            admin_id=user.id
        )
        db.add(hospital)

    db.commit()
    db.refresh(user)
    return user


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401,
                            detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token({
        "user_id": user.id,
        "role":    user.role.value
    })
    return {"access_token": token, "role": user.role.value, "name": user.name}




# ── Me, Change Password, Delete Account ───────────────────────────────────────

@router.get("/me", response_model=UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.put("/change-password")
def change_password(
    payload: ChangePassword,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password updated successfully"}

@router.delete("/delete-account")
def delete_account(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user.is_active = False
    db.commit()
    return {"message": "Account deactivated successfully"}