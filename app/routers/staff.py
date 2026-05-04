from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from datetime import datetime
from app.db import get_db
from app import models
from app.schemas import (
    VerificationAction, CompanyAdminLogin,
    CompanyAdminOut, CompanyAdminChangePassword, Token
)
from app.utils.auth import (
    verify_password, hash_password, create_access_token, decode_token
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/staff", tags=["Staff"])
bearer_scheme = HTTPBearer()


# ── Auth dependency ───────────────────────────────────────────────────────────

def get_current_staff(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> models.CompanyAdmin:
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("role") != "staff":
        raise HTTPException(status_code=403, detail="Staff access required")

    admin_id = payload.get("admin_id")
    admin = db.query(models.CompanyAdmin).filter(
        models.CompanyAdmin.id == admin_id,
        models.CompanyAdmin.is_active == True
    ).first()
    if not admin:
        raise HTTPException(status_code=403, detail="Staff account not found or inactive")
    return admin


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=Token)
def staff_login(payload: CompanyAdminLogin, db: Session = Depends(get_db)):
    admin = db.query(models.CompanyAdmin).filter(
        models.CompanyAdmin.email == payload.email
    ).first()
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not admin.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    city_name = admin.city.name if admin.city else "All Cities"
    token = create_access_token({
        "role":     "staff",
        "admin_id": admin.id,
        "city":     city_name
    })
    return {
        "access_token": token,
        "role":         "staff",
        "name":         admin.name
    }


# ── Change password ───────────────────────────────────────────────────────────

@router.put("/change-password")
def change_password(
    payload: CompanyAdminChangePassword,
    current_admin: models.CompanyAdmin = Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    if not verify_password(payload.current_password, current_admin.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_admin.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password updated successfully"}


# ── Me ────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=CompanyAdminOut)
def get_me(current_admin: models.CompanyAdmin = Depends(get_current_staff)):
    return current_admin


# ── Helper ────────────────────────────────────────────────────────────────────

def get_staff_city_id(admin: models.CompanyAdmin) -> Optional[int]:
    return admin.city_id


# ── Hospitals ─────────────────────────────────────────────────────────────────

@router.get("/hospitals")
def list_hospitals(
    current_admin: models.CompanyAdmin = Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    city_id = get_staff_city_id(current_admin)
    q = db.query(models.Hospital)
    if city_id:
        q = q.filter(models.Hospital.city_id == city_id)
    return q.order_by(models.Hospital.verification_status).all()


@router.put("/hospitals/{hospital_id}/verify")
def verify_hospital(
    hospital_id: int,
    payload: VerificationAction,
    current_admin: models.CompanyAdmin = Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    hospital = db.query(models.Hospital).filter(
        models.Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    if payload.action == "approve":
        hospital.verification_status = models.VerificationStatus.approved
        hospital.rejection_reason    = None
        hospital.verified_at         = datetime.utcnow()
    elif payload.action == "reject":
        if not payload.rejection_reason:
            raise HTTPException(status_code=400,
                                detail="rejection_reason is required")
        hospital.verification_status = models.VerificationStatus.rejected
        hospital.rejection_reason    = payload.rejection_reason
    else:
        raise HTTPException(status_code=400,
                            detail="action must be approve or reject")

    db.commit()
    return {"message": f"Hospital {payload.action}d successfully"}


@router.delete("/hospitals/{hospital_id}")
def delete_hospital(
    hospital_id: int,
    current_admin: models.CompanyAdmin = Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    hospital = db.query(models.Hospital).filter(
        models.Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    doctors = db.query(models.Doctor).filter(
        models.Doctor.hospital_id == hospital_id).all()
    for d in doctors:
        d.hospital_id          = None
        d.verification_status  = models.VerificationStatus.pending

    db.delete(hospital)
    db.commit()
    return {"message": "Hospital deleted, affected doctors set to pending"}


# ── Doctors ───────────────────────────────────────────────────────────────────

@router.get("/doctors")
def list_all_doctors(
    current_admin: models.CompanyAdmin = Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    city_id = get_staff_city_id(current_admin)
    q = (db.query(models.Doctor)
         .join(models.Doctor.hospital)
         .options(
             joinedload(models.Doctor.user),
             joinedload(models.Doctor.hospital)
         ))
    if city_id:
        q = q.filter(models.Hospital.city_id == city_id)
    return q.all()


# ── Overview ──────────────────────────────────────────────────────────────────

@router.get("/overview")
def overview(
    current_admin: models.CompanyAdmin = Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    city_id    = get_staff_city_id(current_admin)
    hosp_q     = db.query(models.Hospital)
    if city_id:
        hosp_q = hosp_q.filter(models.Hospital.city_id == city_id)

    hospitals  = hosp_q.all()
    hosp_ids   = [h.id for h in hospitals]
    doctors    = db.query(models.Doctor).filter(
        models.Doctor.hospital_id.in_(hosp_ids)).all()

    return {
        "city":               current_admin.city.name if current_admin.city else "All Cities",
        "total_hospitals":    len(hospitals),
        "pending_hospitals":  sum(1 for h in hospitals
                                  if h.verification_status.value == "pending"),
        "approved_hospitals": sum(1 for h in hospitals
                                  if h.verification_status.value == "approved"),
        "total_doctors":      len(doctors),
        "pending_doctors":    sum(1 for d in doctors
                                  if d.verification_status.value == "pending"),
        "approved_doctors":   sum(1 for d in doctors
                                  if d.verification_status.value == "approved"),
    }