from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from datetime import datetime
from app.db import get_db
from app import models
from app.schemas import (
    DoctorListItem, DoctorProfile, DoctorUpdate,
    DoctorScheduleCreate, DoctorScheduleOut,
    DoctorChangeHospital, ReviewCreate, ReviewOut,
    AppointmentOut, AppointmentUpdate, EnquiryOut, EnquiryReply
)
from app.routers.auth import get_current_user, require_role

router = APIRouter(tags=["Doctors"])

AVAILABILITY_PRIORITY = {"green": 0, "yellow": 1, "red": 2}
FEE_MAP = {"low": 400, "medium": 900, "high": 2500}


# ── Helpers ───────────────────────────────────────────────────────────────────

def compute_badges(doctor, all_doctors) -> List[str]:
    if not all_doctors:
        return []
    badges = []
    ratings     = [d.avg_rating for d in all_doctors]
    experiences = [d.experience_years for d in all_doctors]
    fees        = [d.consultation_fee for d in all_doctors]
    top_idx = max(0, len(ratings) // 5 - 1)

    if doctor.avg_rating >= sorted(ratings, reverse=True)[top_idx]:
        badges.append("Highly Rated")
    if doctor.experience_years >= sorted(experiences, reverse=True)[top_idx]:
        badges.append("Most Experienced")
    if doctor.consultation_fee <= sorted(fees)[top_idx]:
        badges.append("Best Value")
    return badges


def rank_doctors(doctors, budget, availability_pref):
    def score(d):
        avail = AVAILABILITY_PRIORITY.get(d.availability.value, 9)
        if availability_pref == "green" and d.availability.value == "red":
            avail = 10
        budget_bonus = 1 if (budget and d.hospital and
                             d.hospital.budget_tier.value == budget) else 0
        return (avail, -d.avg_rating, -budget_bonus, -d.experience_years)
    return sorted(doctors, key=score)


def doctor_to_list_item(d, all_doctors) -> DoctorListItem:
    return DoctorListItem(
        id=d.id,
        name=d.user.name,
        specialisation=d.specialisation,
        experience_years=d.experience_years,
        languages=d.languages.split(", ") if isinstance(d.languages, str)
                  else (d.languages or []),
        availability=d.availability.value,
        available_from=d.available_from,
        consultation_fee=d.consultation_fee,
        avg_rating=d.avg_rating,
        review_count=d.review_count,
        hospital_name=d.hospital.name if d.hospital else None,
        city_name=d.hospital.city.name if d.hospital else None,
        budget_tier=d.hospital.budget_tier.value if d.hospital else None,
        badges=compute_badges(d, all_doctors)
    )


# ── Public search ─────────────────────────────────────────────────────────────

@router.get("/cities")
def list_cities(db: Session = Depends(get_db)):
    return db.query(models.City).order_by(models.City.name).all()

@router.get("/hospitals")
def list_hospitals(
    city_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    q = (db.query(models.Hospital)
         .filter(models.Hospital.verification_status ==
                 models.VerificationStatus.approved))
    if city_id:
        q = q.filter(models.Hospital.city_id == city_id)
    return q.order_by(models.Hospital.name).all()

@router.get("/specialisations")
def list_specialisations(db: Session = Depends(get_db)):
    rows = (db.query(models.Doctor.specialisation)
            .filter(models.Doctor.verification_status ==
                    models.VerificationStatus.approved)
            .distinct()
            .order_by(models.Doctor.specialisation)
            .all())
    return [r[0] for r in rows]

@router.get("/doctors", response_model=List[DoctorListItem])
def list_doctors(
    city_id:           Optional[int]   = Query(None),
    specialisation:    Optional[str]   = Query(None),
    budget:            Optional[str]   = Query(None),
    availability_pref: Optional[str]   = Query(None),
    min_rating:        Optional[float] = Query(None),
    db: Session = Depends(get_db)
):
    q = (db.query(models.Doctor)
         .join(models.Doctor.user)
         .join(models.Doctor.hospital)
         .join(models.Hospital.city)
         .options(
             joinedload(models.Doctor.user),
             joinedload(models.Doctor.hospital).joinedload(models.Hospital.city)
         )
         .filter(
             models.Doctor.verification_status == models.VerificationStatus.approved,
             models.Doctor.hospital_id.isnot(None),
             models.Hospital.verification_status == models.VerificationStatus.approved
         ))

    if city_id:
        q = q.filter(models.Hospital.city_id == city_id)
    if specialisation:
        q = q.filter(models.Doctor.specialisation.ilike(f"%{specialisation}%"))
    if budget:
        q = q.filter(models.Hospital.budget_tier == budget)
    if availability_pref and availability_pref != "any":
        q = q.filter(models.Doctor.availability == availability_pref)
    if min_rating is not None:
        q = q.filter(models.Doctor.avg_rating >= min_rating)

    doctors = q.all()
    ranked  = rank_doctors(doctors, budget, availability_pref)
    return [doctor_to_list_item(d, doctors) for d in ranked]


@router.get("/doctors/{doctor_id}", response_model=DoctorProfile)
def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    d = (db.query(models.Doctor)
         .options(
             joinedload(models.Doctor.user),
             joinedload(models.Doctor.hospital).joinedload(models.Hospital.city),
             joinedload(models.Doctor.schedule)
         )
         .filter(models.Doctor.id == doctor_id)
         .first())
    if not d:
        raise HTTPException(status_code=404, detail="Doctor not found")

    return DoctorProfile(
        id=d.id,
        name=d.user.name,
        email=d.user.email,
        specialisation=d.specialisation,
        experience_years=d.experience_years,
        languages=d.languages.split(", ") if isinstance(d.languages, str)
                  else (d.languages or []),
        education=d.education,
        bio=d.bio,
        availability=d.availability.value,
        available_from=d.available_from,
        consultation_fee=d.consultation_fee,
        avg_rating=d.avg_rating,
        review_count=d.review_count,
        verification_status=d.verification_status.value,
        hospital=d.hospital,
        city_name=d.hospital.city.name if d.hospital else None,
        schedule=d.schedule
    )


# ── Doctor own profile management ────────────────────────────────────────────

@router.get("/doctor/me")
def get_my_profile(
    current_user=Depends(require_role("doctor")),
    db: Session = Depends(get_db)
):
    d = (db.query(models.Doctor)
         .options(
             joinedload(models.Doctor.hospital).joinedload(models.Hospital.city),
             joinedload(models.Doctor.schedule)
         )
         .filter(models.Doctor.user_id == current_user.id)
         .first())
    if not d:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    return d


@router.put("/doctor/me")
def update_my_profile(
    payload: DoctorUpdate,
    current_user=Depends(require_role("doctor")),
    db: Session = Depends(get_db)
):
    doctor = db.query(models.Doctor).filter(
        models.Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(doctor, field, value)
    db.commit()
    return {"message": "Profile updated"}


@router.put("/doctor/change-hospital")
def change_hospital(
    payload: DoctorChangeHospital,
    current_user=Depends(require_role("doctor")),
    db: Session = Depends(get_db)
):
    doctor = db.query(models.Doctor).filter(
        models.Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    hospital = db.query(models.Hospital).filter(
        models.Hospital.id == payload.hospital_id,
        models.Hospital.verification_status == models.VerificationStatus.approved
    ).first()
    if not hospital:
        raise HTTPException(status_code=400,
                            detail="Invalid or unverified hospital")

    doctor.hospital_id = payload.hospital_id
    doctor.verification_status = models.VerificationStatus.pending
    doctor.verified_by = None
    doctor.verified_at = None
    doctor.consultation_fee = FEE_MAP.get(hospital.budget_tier.value, 500)
    db.commit()
    return {"message": "Hospital change requested. Awaiting admin verification."}


# ── Schedule ──────────────────────────────────────────────────────────────────

@router.post("/doctor/schedule", status_code=201)
def add_schedule_slot(
    payload: DoctorScheduleCreate,
    current_user=Depends(require_role("doctor")),
    db: Session = Depends(get_db)
):
    doctor = db.query(models.Doctor).filter(
        models.Doctor.user_id == current_user.id).first()
    slot = models.DoctorSchedule(
        doctor_id=doctor.id,
        day_of_week=payload.day_of_week,
        start_time=payload.start_time,
        end_time=payload.end_time,
        slot_duration_minutes=payload.slot_duration_minutes
    )
    db.add(slot)
    db.commit()
    return {"message": "Schedule slot added"}


@router.delete("/doctor/schedule/{slot_id}")
def delete_schedule_slot(
    slot_id: int,
    current_user=Depends(require_role("doctor")),
    db: Session = Depends(get_db)
):
    doctor = db.query(models.Doctor).filter(
        models.Doctor.user_id == current_user.id).first()
    slot = db.query(models.DoctorSchedule).filter(
        models.DoctorSchedule.id == slot_id,
        models.DoctorSchedule.doctor_id == doctor.id
    ).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    db.delete(slot)
    db.commit()
    return {"message": "Slot deleted"}


# ── Reviews ───────────────────────────────────────────────────────────────────

@router.get("/doctors/{doctor_id}/reviews", response_model=List[ReviewOut])
def get_reviews(doctor_id: int, db: Session = Depends(get_db)):
    reviews = (db.query(models.Review)
               .options(joinedload(models.Review.reviewer))
               .filter(models.Review.doctor_id == doctor_id)
               .order_by(models.Review.created_at.desc())
               .all())
    return [ReviewOut(
        id=r.id, rating=r.rating, comment=r.comment,
        reviewer_name=r.reviewer.name, created_at=r.created_at
    ) for r in reviews]


@router.post("/doctors/{doctor_id}/reviews", status_code=201)
def submit_review(
    doctor_id: int,
    payload: ReviewCreate,
    current_user=Depends(require_role("patient")),
    db: Session = Depends(get_db)
):
    if not (1 <= payload.rating <= 5):
        raise HTTPException(status_code=400,
                            detail="Rating must be between 1 and 5")
    doctor = db.query(models.Doctor).filter(
        models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    existing = db.query(models.Review).filter(
        models.Review.doctor_id == doctor_id,
        models.Review.reviewer_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400,
                            detail="You have already reviewed this doctor")

    review = models.Review(
        doctor_id=doctor_id,
        reviewer_id=current_user.id,
        rating=payload.rating,
        comment=payload.comment
    )
    db.add(review)
    db.flush()

    all_reviews = db.query(models.Review).filter(
        models.Review.doctor_id == doctor_id).all()
    doctor.review_count = len(all_reviews)
    doctor.avg_rating = round(
        sum(r.rating for r in all_reviews) / len(all_reviews), 2)

    if doctor.hospital:
        hosp_doctors = db.query(models.Doctor).filter(
            models.Doctor.hospital_id == doctor.hospital_id).all()
        rated = [d for d in hosp_doctors if d.review_count > 0]
        if rated:
            avg = sum(d.avg_rating for d in rated) / len(rated)
            doctor.hospital.quality_score = round(
                avg * 0.7 + doctor.hospital.cleanliness_rating * 0.3, 2)

    db.commit()
    return {"message": "Review submitted",
            "avg_rating": doctor.avg_rating,
            "review_count": doctor.review_count}


# ── Appointments (doctor side) ────────────────────────────────────────────────

@router.get("/doctor/appointments")
def get_my_appointments(
    current_user=Depends(require_role("doctor")),
    db: Session = Depends(get_db)
):
    doctor = db.query(models.Doctor).filter(
        models.Doctor.user_id == current_user.id).first()
    return (db.query(models.Appointment)
            .options(joinedload(models.Appointment.patient))
            .filter(models.Appointment.doctor_id == doctor.id)
            .order_by(models.Appointment.requested_date,
                      models.Appointment.requested_time)
            .all())


@router.put("/doctor/appointments/{appointment_id}")
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    current_user=Depends(require_role("doctor")),
    db: Session = Depends(get_db)
):
    doctor = db.query(models.Doctor).filter(
        models.Doctor.user_id == current_user.id).first()
    appt = db.query(models.Appointment).filter(
        models.Appointment.id == appointment_id,
        models.Appointment.doctor_id == doctor.id
    ).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appt.status = payload.status
    if payload.doctor_note:
        appt.doctor_note = payload.doctor_note
    db.commit()
    return {"message": "Appointment updated"}


# ── Enquiries (doctor side) ───────────────────────────────────────────────────

@router.get("/doctor/enquiries")
def get_my_enquiries(
    current_user=Depends(require_role("doctor")),
    db: Session = Depends(get_db)
):
    doctor = db.query(models.Doctor).filter(
        models.Doctor.user_id == current_user.id).first()
    return (db.query(models.Enquiry)
            .options(joinedload(models.Enquiry.patient))
            .filter(models.Enquiry.doctor_id == doctor.id)
            .order_by(models.Enquiry.created_at.desc())
            .all())


@router.put("/doctor/enquiries/{enquiry_id}/reply")
def reply_to_enquiry(
    enquiry_id: int,
    payload: EnquiryReply,
    current_user=Depends(require_role("doctor")),
    db: Session = Depends(get_db)
):
    doctor = db.query(models.Doctor).filter(
        models.Doctor.user_id == current_user.id).first()
    enquiry = db.query(models.Enquiry).filter(
        models.Enquiry.id == enquiry_id,
        models.Enquiry.doctor_id == doctor.id
    ).first()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    enquiry.reply = payload.reply
    enquiry.status = models.EnquiryStatus.answered
    db.commit()
    return {"message": "Reply sent"}