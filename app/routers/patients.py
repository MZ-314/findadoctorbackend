from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.db import get_db
from app import models
from app.schemas import (
    AppointmentCreate, AppointmentOut,
    EnquiryCreate, EnquiryOut
)
from app.routers.auth import require_role

router = APIRouter(prefix="/patient", tags=["Patients"])


# ── Appointments ──────────────────────────────────────────────────────────────

@router.post("/appointments", status_code=201)
def book_appointment(
    payload: AppointmentCreate,
    current_user=Depends(require_role("patient")),
    db: Session = Depends(get_db)
):
    doctor = db.query(models.Doctor).filter(
        models.Doctor.id == payload.doctor_id,
        models.Doctor.verification_status == models.VerificationStatus.approved
    ).first()
    if not doctor:
        raise HTTPException(status_code=404,
                            detail="Doctor not found or not verified")

    # Check slot not already taken
    conflict = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == payload.doctor_id,
        models.Appointment.requested_date == payload.requested_date,
        models.Appointment.requested_time == payload.requested_time,
        models.Appointment.status == models.AppointmentStatus.accepted
    ).first()
    if conflict:
        raise HTTPException(status_code=400,
                            detail="This time slot is already booked")

    appt = models.Appointment(
        patient_id=current_user.id,
        doctor_id=payload.doctor_id,
        requested_date=payload.requested_date,
        requested_time=payload.requested_time,
        reason=payload.reason
    )
    db.add(appt)
    db.commit()
    return {"message": "Appointment request sent"}


@router.get("/appointments")
def my_appointments(
    current_user=Depends(require_role("patient")),
    db: Session = Depends(get_db)
):
    return (db.query(models.Appointment)
            .options(joinedload(models.Appointment.doctor)
                     .joinedload(models.Doctor.user))
            .filter(models.Appointment.patient_id == current_user.id)
            .order_by(models.Appointment.requested_date,
                      models.Appointment.requested_time)
            .all())


@router.delete("/appointments/{appointment_id}")
def cancel_appointment(
    appointment_id: int,
    current_user=Depends(require_role("patient")),
    db: Session = Depends(get_db)
):
    appt = db.query(models.Appointment).filter(
        models.Appointment.id == appointment_id,
        models.Appointment.patient_id == current_user.id
    ).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.status.value == "accepted":
        raise HTTPException(status_code=400,
                            detail="Cannot cancel an accepted appointment")

    appt.status = models.AppointmentStatus.cancelled
    db.commit()
    return {"message": "Appointment cancelled"}


# ── Enquiries ─────────────────────────────────────────────────────────────────

@router.post("/enquiries", status_code=201)
def send_enquiry(
    payload: EnquiryCreate,
    current_user=Depends(require_role("patient")),
    db: Session = Depends(get_db)
):
    doctor = db.query(models.Doctor).filter(
        models.Doctor.id == payload.doctor_id,
        models.Doctor.verification_status == models.VerificationStatus.approved
    ).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    enquiry = models.Enquiry(
        patient_id=current_user.id,
        doctor_id=payload.doctor_id,
        message=payload.message
    )
    db.add(enquiry)
    db.commit()
    return {"message": "Enquiry sent"}


@router.get("/enquiries")
def my_enquiries(
    current_user=Depends(require_role("patient")),
    db: Session = Depends(get_db)
):
    return (db.query(models.Enquiry)
            .options(joinedload(models.Enquiry.doctor)
                     .joinedload(models.Doctor.user))
            .filter(models.Enquiry.patient_id == current_user.id)
            .order_by(models.Enquiry.created_at.desc())
            .all())