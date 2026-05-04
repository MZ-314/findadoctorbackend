from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey,
    Enum, DateTime, Text, Boolean, Date, Time
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db import Base


# ── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    patient        = "patient"
    doctor         = "doctor"
    hospital_admin = "hospital_admin"
    staff          = "staff"

class BudgetTier(str, enum.Enum):
    low    = "low"
    medium = "medium"
    high   = "high"

class AvailabilityStatus(str, enum.Enum):
    green  = "green"
    yellow = "yellow"
    red    = "red"

class VerificationStatus(str, enum.Enum):
    pending  = "pending"
    approved = "approved"
    rejected = "rejected"

class AppointmentStatus(str, enum.Enum):
    pending   = "pending"
    accepted  = "accepted"
    rejected  = "rejected"
    cancelled = "cancelled"

class EnquiryStatus(str, enum.Enum):
    open     = "open"
    answered = "answered"
    closed   = "closed"

class DayOfWeek(str, enum.Enum):
    monday    = "monday"
    tuesday   = "tuesday"
    wednesday = "wednesday"
    thursday  = "thursday"
    friday    = "friday"
    saturday  = "saturday"
    sunday    = "sunday"


# ── Models ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(120), nullable=False)
    email         = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role          = Column(Enum(UserRole), nullable=False)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    doctor_profile = relationship("Doctor", back_populates="user", uselist=False,
                                  foreign_keys="Doctor.user_id")
    hospital_admin = relationship("Hospital", back_populates="admin",
                                  foreign_keys="Hospital.admin_id")
    reviews        = relationship("Review", back_populates="reviewer",
                                  foreign_keys="Review.reviewer_id")
    appointments   = relationship("Appointment", back_populates="patient",
                                  foreign_keys="Appointment.patient_id")
    enquiries      = relationship("Enquiry", back_populates="patient",
                                  foreign_keys="Enquiry.patient_id")


class City(Base):
    __tablename__ = "cities"

    id   = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)

    hospitals = relationship("Hospital", back_populates="city")


class Hospital(Base):
    __tablename__ = "hospitals"

    id                  = Column(Integer, primary_key=True, index=True)
    name                = Column(String(200), nullable=False)
    city_id             = Column(Integer, ForeignKey("cities.id"), nullable=False)
    address             = Column(String(300))
    budget_tier         = Column(Enum(BudgetTier), nullable=False)
    cleanliness_rating  = Column(Float, default=3.0)
    quality_score       = Column(Float, default=0.0)
    description         = Column(Text)
    phone               = Column(String(20))
    email               = Column(String(255))
    website             = Column(String(255))
    verification_status = Column(Enum(VerificationStatus),
                                 default=VerificationStatus.pending)
    verified_by         = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at         = Column(DateTime(timezone=True), nullable=True)
    rejection_reason    = Column(Text, nullable=True)
    admin_id            = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())

    city    = relationship("City", back_populates="hospitals")
    admin   = relationship("User", back_populates="hospital_admin",
                           foreign_keys=[admin_id])
    verifier = relationship("User", foreign_keys=[verified_by])
    doctors = relationship("Doctor", back_populates="hospital",
                           foreign_keys="Doctor.hospital_id")


class Doctor(Base):
    __tablename__ = "doctors"

    id                  = Column(Integer, primary_key=True, index=True)
    user_id             = Column(Integer, ForeignKey("users.id"),
                                 unique=True, nullable=False)
    hospital_id         = Column(Integer, ForeignKey("hospitals.id"), nullable=True)

    specialisation      = Column(String(150), nullable=False)
    experience_years    = Column(Integer, default=0)
    languages           = Column(String(200))
    education           = Column(Text)
    bio                 = Column(Text)

    availability        = Column(Enum(AvailabilityStatus),
                                 default=AvailabilityStatus.green)
    available_from      = Column(String(50), nullable=True)

    consultation_fee    = Column(Integer, nullable=False)

    avg_rating          = Column(Float, default=0.0)
    review_count        = Column(Integer, default=0)

    verification_status = Column(Enum(VerificationStatus),
                                 default=VerificationStatus.pending)
    verified_by         = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at         = Column(DateTime(timezone=True), nullable=True)
    rejection_reason    = Column(Text, nullable=True)

    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())

    user         = relationship("User", back_populates="doctor_profile",
                                foreign_keys=[user_id])
    hospital     = relationship("Hospital", back_populates="doctors",
                                foreign_keys=[hospital_id])
    verifier     = relationship("User", foreign_keys=[verified_by])
    schedule     = relationship("DoctorSchedule", back_populates="doctor",
                                cascade="all, delete-orphan")
    reviews      = relationship("Review", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor",
                                foreign_keys="Appointment.doctor_id")
    enquiries    = relationship("Enquiry", back_populates="doctor",
                                foreign_keys="Enquiry.doctor_id")


class DoctorSchedule(Base):
    __tablename__ = "doctor_schedule"

    id                   = Column(Integer, primary_key=True, index=True)
    doctor_id            = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    day_of_week          = Column(Enum(DayOfWeek), nullable=False)
    start_time           = Column(String(5), nullable=False)   # "09:00"
    end_time             = Column(String(5), nullable=False)   # "17:00"
    slot_duration_minutes = Column(Integer, default=30)

    doctor = relationship("Doctor", back_populates="schedule")


class Appointment(Base):
    __tablename__ = "appointments"

    id             = Column(Integer, primary_key=True, index=True)
    patient_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id      = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    requested_date = Column(String(10), nullable=False)   # "2026-05-10"
    requested_time = Column(String(5), nullable=False)    # "10:30"
    status         = Column(Enum(AppointmentStatus),
                            default=AppointmentStatus.pending)
    reason         = Column(Text, nullable=True)
    doctor_note    = Column(Text, nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())

    patient = relationship("User", back_populates="appointments",
                           foreign_keys=[patient_id])
    doctor  = relationship("Doctor", back_populates="appointments",
                           foreign_keys=[doctor_id])


class Enquiry(Base):
    __tablename__ = "enquiries"

    id         = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id  = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    message    = Column(Text, nullable=False)
    reply      = Column(Text, nullable=True)
    status     = Column(Enum(EnquiryStatus), default=EnquiryStatus.open)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    patient = relationship("User", back_populates="enquiries",
                           foreign_keys=[patient_id])
    doctor  = relationship("Doctor", back_populates="enquiries",
                           foreign_keys=[doctor_id])


class Review(Base):
    __tablename__ = "reviews"

    id          = Column(Integer, primary_key=True, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id   = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    rating      = Column(Integer, nullable=False)
    comment     = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    reviewer = relationship("User", back_populates="reviews",
                            foreign_keys=[reviewer_id])
    doctor   = relationship("Doctor", back_populates="reviews")

class CompanyAdmin(Base):
    __tablename__ = "company_admins"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(120), nullable=False)
    email         = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    city_id       = Column(Integer, ForeignKey("cities.id"), nullable=True)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    city = relationship("City")