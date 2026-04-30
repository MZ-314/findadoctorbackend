from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime
from app.db import get_db
from app import models
from app.schemas import (
    HospitalOut, HospitalUpdate,
    DoctorListItem, VerificationAction
)
from app.routers.auth import get_current_user, require_role

router = APIRouter(prefix="/hospital", tags=["Hospital"])


def get_admin_hospital(
    current_user: models.User,
    db: Session
) -> models.Hospital:
    hospital = db.query(models.Hospital).filter(
        models.Hospital.admin_id == current_user.id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="No hospital found for this admin")
    return hospital


# ── Hospital profile ──────────────────────────────────────────────────────────

@router.get("/me")
def get_my_hospital(
    current_user=Depends(require_role("hospital_admin")),
    db: Session = Depends(get_db)
):
    return get_admin_hospital(current_user, db)


@router.put("/me")
def update_my_hospital(
    payload: HospitalUpdate,
    current_user=Depends(require_role("hospital_admin")),
    db: Session = Depends(get_db)
):
    hospital = get_admin_hospital(current_user, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(hospital, field, value)
    db.commit()
    return {"message": "Hospital updated successfully"}


# ── Doctor verification ───────────────────────────────────────────────────────

@router.get("/pending-doctors")
def list_pending_doctors(
    current_user=Depends(require_role("hospital_admin")),
    db: Session = Depends(get_db)
):
    hospital = get_admin_hospital(current_user, db)
    doctors = (db.query(models.Doctor)
               .options(joinedload(models.Doctor.user))
               .filter(
                   models.Doctor.hospital_id == hospital.id,
                   models.Doctor.verification_status == models.VerificationStatus.pending
               ).all())
    return doctors


@router.put("/doctors/{doctor_id}/verify")
def verify_doctor(
    doctor_id: int,
    payload: VerificationAction,
    current_user=Depends(require_role("hospital_admin")),
    db: Session = Depends(get_db)
):
    hospital = get_admin_hospital(current_user, db)
    doctor = db.query(models.Doctor).filter(
        models.Doctor.id == doctor_id,
        models.Doctor.hospital_id == hospital.id
    ).first()
    if not doctor:
        raise HTTPException(status_code=404,
                            detail="Doctor not found in your hospital")

    if payload.action == "approve":
        doctor.verification_status = models.VerificationStatus.approved
        doctor.rejection_reason = None
        doctor.verified_by = current_user.id
        doctor.verified_at = datetime.utcnow()
    elif payload.action == "reject":
        if not payload.rejection_reason:
            raise HTTPException(status_code=400,
                                detail="rejection_reason is required")
        doctor.verification_status = models.VerificationStatus.rejected
        doctor.rejection_reason = payload.rejection_reason
    else:
        raise HTTPException(status_code=400,
                            detail="action must be approve or reject")

    db.commit()
    return {"message": f"Doctor {payload.action}d successfully"}


@router.delete("/doctors/{doctor_id}/remove")
def remove_doctor(
    doctor_id: int,
    current_user=Depends(require_role("hospital_admin")),
    db: Session = Depends(get_db)
):
    hospital = get_admin_hospital(current_user, db)
    doctor = db.query(models.Doctor).filter(
        models.Doctor.id == doctor_id,
        models.Doctor.hospital_id == hospital.id
    ).first()
    if not doctor:
        raise HTTPException(status_code=404,
                            detail="Doctor not found in your hospital")

    doctor.hospital_id = None
    doctor.verification_status = models.VerificationStatus.pending
    doctor.verified_by = None
    doctor.verified_at = None
    db.commit()
    return {"message": "Doctor removed. They must re-associate with a hospital."}


@router.get("/doctors")
def list_my_doctors(
    current_user=Depends(require_role("hospital_admin")),
    db: Session = Depends(get_db)
):
    hospital = get_admin_hospital(current_user, db)
    return (db.query(models.Doctor)
            .options(joinedload(models.Doctor.user))
            .filter(
                models.Doctor.hospital_id == hospital.id,
                models.Doctor.verification_status == models.VerificationStatus.approved
            ).all())