from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from app.db import get_db
from app import models
from app.schemas import HospitalOut, DoctorProfile, VerificationAction
from app.routers.auth import get_current_staff

router = APIRouter(prefix="/staff", tags=["Staff"])


def get_staff_city_id(city_name: str, db: Session) -> Optional[int]:
    city = db.query(models.City).filter(
        models.City.name == city_name).first()
    return city.id if city else None


# ── Hospitals ─────────────────────────────────────────────────────────────────

@router.get("/hospitals")
def list_hospitals(
    staff=Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    city_id = get_staff_city_id(staff["city"], db)
    q = db.query(models.Hospital)
    if city_id:
        q = q.filter(models.Hospital.city_id == city_id)
    return q.order_by(models.Hospital.verification_status).all()


@router.put("/hospitals/{hospital_id}/verify")
def verify_hospital(
    hospital_id: int,
    payload: VerificationAction,
    staff=Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    hospital = db.query(models.Hospital).filter(
        models.Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    if payload.action == "approve":
        hospital.verification_status = models.VerificationStatus.approved
        hospital.rejection_reason = None
        hospital.verified_at = datetime.utcnow()
    elif payload.action == "reject":
        if not payload.rejection_reason:
            raise HTTPException(status_code=400,
                                detail="rejection_reason is required")
        hospital.verification_status = models.VerificationStatus.rejected
        hospital.rejection_reason = payload.rejection_reason
    else:
        raise HTTPException(status_code=400, detail="action must be approve or reject")

    db.commit()
    return {"message": f"Hospital {payload.action}d successfully"}


@router.delete("/hospitals/{hospital_id}")
def delete_hospital(
    hospital_id: int,
    staff=Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    hospital = db.query(models.Hospital).filter(
        models.Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    # Unlink all doctors from this hospital
    doctors = db.query(models.Doctor).filter(
        models.Doctor.hospital_id == hospital_id).all()
    for d in doctors:
        d.hospital_id = None
        d.verification_status = models.VerificationStatus.pending

    db.delete(hospital)
    db.commit()
    return {"message": "Hospital deleted, affected doctors set to pending"}


# ── Doctors ───────────────────────────────────────────────────────────────────

@router.get("/doctors")
def list_all_doctors(
    staff=Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    city_id = get_staff_city_id(staff["city"], db)
    q = (db.query(models.Doctor)
         .join(models.Doctor.hospital)
         .options(joinedload(models.Doctor.user),
                  joinedload(models.Doctor.hospital)))
    if city_id:
        q = q.filter(models.Hospital.city_id == city_id)
    return q.all()


# ── Overview ──────────────────────────────────────────────────────────────────

@router.get("/overview")
def overview(
    staff=Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    city_id = get_staff_city_id(staff["city"], db)
    hosp_q  = db.query(models.Hospital)
    if city_id:
        hosp_q = hosp_q.filter(models.Hospital.city_id == city_id)

    hospitals   = hosp_q.all()
    hosp_ids    = [h.id for h in hospitals]
    doctors     = db.query(models.Doctor).filter(
        models.Doctor.hospital_id.in_(hosp_ids)).all()

    return {
        "city":               staff["city"],
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