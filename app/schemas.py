from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.models import (
    UserRole, BudgetTier, VerificationStatus,
    AppointmentStatus, EnquiryStatus, DayOfWeek
)


# ── Auth ─────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole
    # Doctor fields
    specialisation:   Optional[str] = None
    hospital_id:      Optional[int] = None
    experience_years: Optional[int] = None
    languages:        Optional[str] = None
    education:        Optional[str] = None
    bio:              Optional[str] = None
    # Hospital admin fields
    hospital_name:        Optional[str] = None
    hospital_city_id:     Optional[int] = None
    hospital_address:     Optional[str] = None
    hospital_budget_tier: Optional[BudgetTier] = None
    hospital_description: Optional[str] = None
    hospital_phone:       Optional[str] = None
    hospital_email:       Optional[EmailStr] = None
    hospital_website:     Optional[str] = None

class UserLogin(BaseModel):
    email:    EmailStr
    password: str

class StaffLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id:         int
    name:       str
    email:      str
    role:       UserRole
    is_active:  bool
    created_at: datetime
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    role:         str
    name:         str

class ChangePassword(BaseModel):
    current_password: str
    new_password:     str


# ── Cities ───────────────────────────────────────────────────────────────────

class CityOut(BaseModel):
    id:   int
    name: str
    class Config:
        from_attributes = True


# ── Hospitals ────────────────────────────────────────────────────────────────

class HospitalOut(BaseModel):
    id:                  int
    name:                str
    city_id:             int
    address:             Optional[str]
    budget_tier:         str
    cleanliness_rating:  float
    quality_score:       float
    description:         Optional[str]
    phone:               Optional[str]
    email:               Optional[str]
    website:             Optional[str]
    verification_status: str
    class Config:
        from_attributes  = True
        use_enum_values  = True

class HospitalUpdate(BaseModel):
    name:               Optional[str] = None
    address:            Optional[str] = None
    description:        Optional[str] = None
    phone:              Optional[str] = None
    email:              Optional[str] = None
    website:            Optional[str] = None
    cleanliness_rating: Optional[float] = None


# ── Doctors ──────────────────────────────────────────────────────────────────

class DoctorScheduleOut(BaseModel):
    id:                    int
    day_of_week:           str
    start_time:            str
    end_time:              str
    slot_duration_minutes: int
    class Config:
        from_attributes = True

class DoctorScheduleCreate(BaseModel):
    day_of_week:           DayOfWeek
    start_time:            str
    end_time:              str
    slot_duration_minutes: int = 30

class DoctorListItem(BaseModel):
    id:               int
    name:             str
    specialisation:   str
    experience_years: int
    languages:        List[str]
    availability:     str
    available_from:   Optional[str]
    consultation_fee: int
    avg_rating:       float
    review_count:     int
    hospital_name:    Optional[str]
    city_name:        Optional[str]
    budget_tier:      Optional[str]
    badges:           List[str] = []
    class Config:
        from_attributes = True
        use_enum_values = True

class DoctorProfile(BaseModel):
    id:                  int
    name:                str
    email:               str
    specialisation:      str
    experience_years:    int
    languages:           List[str]
    education:           Optional[str]
    bio:                 Optional[str]
    availability:        str
    available_from:      Optional[str]
    consultation_fee:    int
    avg_rating:          float
    review_count:        int
    verification_status: str
    hospital:            Optional[HospitalOut]
    city_name:           Optional[str]
    schedule:            List[DoctorScheduleOut] = []
    class Config:
        from_attributes = True
        use_enum_values = True

class DoctorUpdate(BaseModel):
    specialisation:   Optional[str] = None
    experience_years: Optional[int] = None
    languages:        Optional[str] = None
    education:        Optional[str] = None
    bio:              Optional[str] = None
    availability:     Optional[str] = None
    available_from:   Optional[str] = None

class DoctorChangeHospital(BaseModel):
    hospital_id: int


# ── Reviews ──────────────────────────────────────────────────────────────────

class ReviewCreate(BaseModel):
    rating:  int
    comment: Optional[str] = None

class ReviewOut(BaseModel):
    id:            int
    rating:        int
    comment:       Optional[str]
    reviewer_name: str
    created_at:    datetime
    class Config:
        from_attributes = True


# ── Appointments ─────────────────────────────────────────────────────────────

class AppointmentCreate(BaseModel):
    doctor_id:      int
    requested_date: str   # "2026-05-10"
    requested_time: str   # "10:30"
    reason:         Optional[str] = None

class AppointmentOut(BaseModel):
    id:             int
    patient_id:     int
    doctor_id:      int
    requested_date: str
    requested_time: str
    status:         str
    reason:         Optional[str]
    doctor_note:    Optional[str]
    patient_name:   Optional[str] = None
    doctor_name:    Optional[str] = None
    created_at:     datetime
    class Config:
        from_attributes = True
        use_enum_values = True

class AppointmentUpdate(BaseModel):
    status:      AppointmentStatus
    doctor_note: Optional[str] = None


# ── Enquiries ─────────────────────────────────────────────────────────────────

class EnquiryCreate(BaseModel):
    doctor_id: int
    message:   str

class EnquiryOut(BaseModel):
    id:           int
    patient_id:   int
    doctor_id:    int
    message:      str
    reply:        Optional[str]
    status:       str
    patient_name: Optional[str] = None
    doctor_name:  Optional[str] = None
    created_at:   datetime
    class Config:
        from_attributes = True
        use_enum_values = True

class EnquiryReply(BaseModel):
    reply: str


# ── Staff / Verification ─────────────────────────────────────────────────────

class VerificationAction(BaseModel):
    action:           str   # "approve" | "reject"
    rejection_reason: Optional[str] = None


# ── AI ───────────────────────────────────────────────────────────────────────

class AIRecommendRequest(BaseModel):
    problem_description: str
    city_id:             Optional[int] = None
    budget:              Optional[str] = None

class AIRecommendResponse(BaseModel):
    recommended_doctors:   List[DoctorListItem]
    recommended_hospitals: List[HospitalOut]
    explanation:           str
    suggested_specialisation: str