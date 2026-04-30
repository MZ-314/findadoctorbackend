"""
Run once to populate Supabase with seed data.
Usage: python -m app.seed
"""

from app.db import SessionLocal, engine
from app import models
from app.models import (
    BudgetTier, AvailabilityStatus, UserRole,
    VerificationStatus, DayOfWeek
)
from passlib.context import CryptContext
from datetime import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

FEE_MAP = {
    BudgetTier.low:    400,
    BudgetTier.medium: 900,
    BudgetTier.high:   2500,
}

CITIES = ["Hyderabad", "Pune", "Guwahati"]

HOSPITALS = [
    # (name, city, budget_tier, cleanliness_rating, address, description, phone, email, website)

    # Hyderabad
    ("Apollo Hospitals Jubilee Hills", "Hyderabad", BudgetTier.high, 4.7,
     "Jubilee Hills, Hyderabad",
     "Apollo Hospitals Jubilee Hills is a 350-bed multi-specialty hospital offering advanced cardiac care, neurology, oncology, and orthopaedics. Equipped with state-of-the-art robotic surgery and a 24/7 trauma centre. JCI accredited.",
     "+91-40-23607777", "jubileehills@apollohospitals.com", "https://www.apollohospitals.com"),

    ("Yashoda Hospitals Somajiguda", "Hyderabad", BudgetTier.high, 4.5,
     "Somajiguda, Hyderabad",
     "Yashoda Hospitals is a leading tertiary care hospital in Hyderabad with expertise in cardiology, neurosciences, gastroenterology and transplant surgery. Known for affordable high-quality care and experienced medical staff.",
     "+91-40-45674567", "somajiguda@yashodahospitals.com", "https://www.yashodahospitals.com"),

    ("Care Hospitals Banjara Hills", "Hyderabad", BudgetTier.medium, 4.2,
     "Banjara Hills, Hyderabad",
     "Care Hospitals Banjara Hills is a 200-bed multi-specialty hospital providing quality healthcare in obstetrics, orthopaedics, and general medicine. Focuses on patient-centric care with modern diagnostic facilities.",
     "+91-40-30418000", "banjarahills@carehospitals.com", "https://www.carehospitals.com"),

    ("Kamineni Hospitals LB Nagar", "Hyderabad", BudgetTier.medium, 3.9,
     "LB Nagar, Hyderabad",
     "Kamineni Hospitals LB Nagar serves the eastern corridor of Hyderabad with specialities in neurology, cardiology and general surgery. Community-focused hospital with strong outpatient services.",
     "+91-40-39879999", "lbnagar@kaminenihospitals.com", "https://www.kaminenihospitals.com"),

    ("Government General Hospital", "Hyderabad", BudgetTier.low, 3.2,
     "Afzalgunj, Hyderabad",
     "One of the oldest and largest government hospitals in Telangana providing free and subsidised healthcare to underprivileged citizens. Offers general medicine, surgery, gynaecology and emergency services.",
     "+91-40-24600123", "ggh.hyderabad@gov.in", ""),

    # Pune
    ("Ruby Hall Clinic", "Pune", BudgetTier.high, 4.6,
     "Sassoon Road, Pune",
     "Ruby Hall Clinic is Pune's premier tertiary care hospital with over 60 years of excellence. Specialises in cardiac sciences, oncology, neurology and transplant medicine. NABH accredited with 450 beds.",
     "+91-20-66455000", "info@rubyhall.com", "https://www.rubyhall.com"),

    ("Jehangir Hospital", "Pune", BudgetTier.high, 4.4,
     "Sassoon Road, Pune",
     "Jehangir Hospital is one of Pune's most trusted hospitals established in 1946. Offers comprehensive care in cardiology, orthopaedics, dermatology and women's health. Known for highly experienced consultants.",
     "+91-20-66810000", "info@jehangirhospital.org", "https://www.jehangirhospital.org"),

    ("Deenanath Mangeshkar Hospital", "Pune", BudgetTier.medium, 4.3,
     "Erandwane, Pune",
     "Deenanath Mangeshkar Hospital is a 700-bed charitable hospital offering high-quality healthcare at affordable rates. Strong departments in gynaecology, paediatrics, cardiology and oncology.",
     "+91-20-49150000", "info@dmhospital.org", "https://www.dmhospital.org"),

    ("Poona Hospital & Research Centre", "Pune", BudgetTier.medium, 4.0,
     "Sadashiv Peth, Pune",
     "Poona Hospital is a 400-bed teaching hospital affiliated with BJ Medical College. Provides specialised care in cardiology, nephrology and general surgery with strong research and academic programs.",
     "+91-20-24476111", "info@poonahospital.org", "https://www.poonahospital.org"),

    ("Sassoon General Hospital", "Pune", BudgetTier.low, 3.1,
     "Pune Station, Pune",
     "Sassoon General Hospital is Pune's largest government hospital serving over 2000 patients daily. Provides free emergency, surgical and medical care to the underprivileged population of Pune and surrounding districts.",
     "+91-20-26128000", "sassoon@gov.in", ""),

    # Guwahati
    ("Nemcare Hospital", "Guwahati", BudgetTier.high, 4.3,
     "Bhangagarh, Guwahati",
     "Nemcare Hospital is Northeast India's leading private hospital with advanced facilities in cardiac sciences, neurology and oncology. 300-bed facility with cutting-edge diagnostic equipment and experienced specialists.",
     "+91-361-2340222", "info@nemcarehospital.com", "https://www.nemcarehospital.com"),

    ("Downtown Hospital", "Guwahati", BudgetTier.high, 4.2,
     "GS Road, Guwahati",
     "Downtown Hospital is one of Guwahati's most comprehensive multi-specialty hospitals offering cardiology, neurology, orthopaedics and women's health services. Known for excellent patient care and modern infrastructure.",
     "+91-361-2331003", "info@downtownhospital.in", "https://www.downtownhospital.in"),

    ("Wintrobe Hospital", "Guwahati", BudgetTier.medium, 3.8,
     "Zoo Road, Guwahati",
     "Wintrobe Hospital provides quality secondary care in general medicine, orthopaedics and gynaecology to the residents of Guwahati. Affordable pricing with competent medical staff and modern diagnostic facilities.",
     "+91-361-2636000", "info@wintrobehospital.com", ""),

    ("Gauhati Medical College Hospital", "Guwahati", BudgetTier.low, 3.0,
     "Bhangagarh, Guwahati",
     "Gauhati Medical College Hospital is the premier government medical institution of Assam providing free tertiary care to patients from across Northeast India. Strong departments in general medicine, surgery and emergency care.",
     "+91-361-2529457", "gmch@gov.in", ""),
]

# (name, email, password, specialisation, experience, languages,
#  education, bio, availability, available_from, hospital_name)
DOCTORS = [
    # Apollo Hyderabad
    ("Dr. Ramesh Rao", "ramesh.rao@apollo.com", "Doctor@123",
     "Cardiologist", 18, "English, Hindi, Telugu",
     "MBBS, MD (Cardiology) – AIIMS Delhi",
     "Senior cardiologist with 18 years of expertise in interventional cardiology, heart failure management, and complex angioplasty procedures. Performed over 3000 successful cardiac interventions.",
     AvailabilityStatus.green, None, "Apollo Hospitals Jubilee Hills"),

    ("Dr. Priya Mehta", "priya.mehta@apollo.com", "Doctor@123",
     "Neurologist", 12, "English, Hindi",
     "MBBS, DM (Neurology) – CMC Vellore",
     "Specialises in epilepsy management, stroke rehabilitation and neurodegenerative disorders. Pioneer in implementing telemedicine neurology consultations in Hyderabad.",
     AvailabilityStatus.yellow, "4:00 PM", "Apollo Hospitals Jubilee Hills"),

    ("Dr. Sanjay Gupta", "sanjay.gupta@apollo.com", "Doctor@123",
     "Orthopedist", 15, "English, Hindi, Telugu",
     "MBBS, MS (Orthopaedics) – Osmania Medical College",
     "Expert in joint replacement surgeries, sports injury rehabilitation and spine surgery. Introduced minimally invasive knee replacement technique at Apollo Hyderabad.",
     AvailabilityStatus.green, None, "Apollo Hospitals Jubilee Hills"),

    # Yashoda Hyderabad
    ("Dr. Kavitha Reddy", "kavitha.reddy@yashoda.com", "Doctor@123",
     "Dermatologist", 10, "English, Telugu",
     "MBBS, MD (Dermatology) – NTR University",
     "Focused on clinical dermatology, cosmetic procedures and hair disorders. Expert in treating psoriasis, vitiligo and conducting advanced laser skin treatments.",
     AvailabilityStatus.green, None, "Yashoda Hospitals Somajiguda"),

    ("Dr. Arun Kumar", "arun.kumar@yashoda.com", "Doctor@123",
     "Cardiologist", 20, "English, Hindi, Telugu",
     "MBBS, DM (Cardiology) – PGIMER Chandigarh",
     "Pioneer in non-invasive cardiology with 20 years of clinical experience. Specialises in echocardiography, cardiac imaging and preventive cardiology programs.",
     AvailabilityStatus.red, None, "Yashoda Hospitals Somajiguda"),

    # Care Hospitals Hyderabad
    ("Dr. Neha Sharma", "neha.sharma@care.com", "Doctor@123",
     "Gynecologist", 8, "English, Hindi",
     "MBBS, MS (Obstetrics & Gynaecology) – Hyderabad",
     "Specialises in high-risk pregnancies, laparoscopic gynaecological procedures and infertility treatments. Delivered over 2000 successful births including complex cases.",
     AvailabilityStatus.yellow, "5:30 PM", "Care Hospitals Banjara Hills"),

    ("Dr. Suresh Patil", "suresh.patil@care.com", "Doctor@123",
     "Orthopedist", 11, "English, Hindi, Telugu",
     "MBBS, MS (Orthopaedics) – Bangalore",
     "Focuses on trauma surgery, minimally invasive joint procedures and paediatric orthopaedics. Has successfully treated over 500 complex fracture cases.",
     AvailabilityStatus.green, None, "Care Hospitals Banjara Hills"),

    # Kamineni Hyderabad
    ("Dr. Lalitha Nair", "lalitha.nair@kamineni.com", "Doctor@123",
     "Neurologist", 9, "English, Malayalam, Telugu",
     "MBBS, MD, DM (Neurology) – Kerala",
     "Expertise in headache disorders, dementia management and clinical neurophysiology. Runs a dedicated memory clinic for early Alzheimer's detection at Kamineni.",
     AvailabilityStatus.green, None, "Kamineni Hospitals LB Nagar"),

    # Government General Hyderabad
    ("Dr. Mohammed Farooq", "farooq@ggh.com", "Doctor@123",
     "General Physician", 5, "English, Hindi, Telugu, Urdu",
     "MBBS – Osmania Medical College",
     "Dedicated general physician providing affordable primary care to underserved communities. Expertise in managing infectious diseases, hypertension and diabetes in resource-limited settings.",
     AvailabilityStatus.green, None, "Government General Hospital"),

    # Ruby Hall Pune
    ("Dr. Anjali Desai", "anjali.desai@ruby.com", "Doctor@123",
     "Cardiologist", 16, "English, Hindi, Marathi",
     "MBBS, DM (Cardiology) – KEM Hospital Pune",
     "Renowned interventional cardiologist known for complex angioplasty procedures and structural heart disease management. Has performed over 4000 cardiac catheterisations.",
     AvailabilityStatus.green, None, "Ruby Hall Clinic"),

    ("Dr. Rohit Kulkarni", "rohit.kulkarni@ruby.com", "Doctor@123",
     "Orthopedist", 14, "English, Marathi",
     "MBBS, MS (Orthopaedics) – BJ Medical College Pune",
     "Hip and knee replacement specialist with international fellowship training from Germany. Expert in revision joint surgeries and complex trauma management.",
     AvailabilityStatus.yellow, "6:00 PM", "Ruby Hall Clinic"),

    # Jehangir Pune
    ("Dr. Sunita Joshi", "sunita.joshi@jehangir.com", "Doctor@123",
     "Dermatologist", 13, "English, Hindi, Marathi",
     "MBBS, MD (Dermatology) – Pune University",
     "Expert in skin cancer detection, psoriasis management and aesthetic dermatology. Pioneered a dermoscopy screening program that has diagnosed over 200 early-stage melanomas.",
     AvailabilityStatus.green, None, "Jehangir Hospital"),

    ("Dr. Vikram Bhat", "vikram.bhat@jehangir.com", "Doctor@123",
     "Neurologist", 17, "English, Kannada, Hindi",
     "MBBS, DM (Neurology) – NIMHANS Bangalore",
     "Leading neurologist with special interest in movement disorders and Parkinson's disease. Established the first dedicated Parkinson's clinic in Pune with over 500 registered patients.",
     AvailabilityStatus.red, None, "Jehangir Hospital"),

    # Deenanath Mangeshkar Pune
    ("Dr. Meera Kulkarni", "meera.k@dmh.com", "Doctor@123",
     "Gynecologist", 10, "English, Marathi",
     "MBBS, MS (OBG) – Pune",
     "Specialises in fertility treatments, minimally invasive gynaecology and maternal-foetal medicine. Has helped over 300 couples achieve successful pregnancies through IVF and related procedures.",
     AvailabilityStatus.green, None, "Deenanath Mangeshkar Hospital"),

    ("Dr. Prasad Deshpande", "prasad.d@dmh.com", "Doctor@123",
     "General Physician", 7, "English, Hindi, Marathi",
     "MBBS, MD (Internal Medicine) – Pune",
     "Primary care physician with expertise in diabetes management, thyroid disorders and preventive health. Manages a diabetic clinic serving over 800 patients monthly.",
     AvailabilityStatus.green, None, "Deenanath Mangeshkar Hospital"),

    # Poona Hospital Pune
    ("Dr. Ashok Wagh", "ashok.wagh@poona.com", "Doctor@123",
     "Cardiologist", 12, "English, Marathi",
     "MBBS, MD, DM (Cardiology) – Nagpur",
     "Cardiologist focused on preventive cardiology, lipid disorders and cardiac rehabilitation. Runs community heart health camps benefiting over 5000 patients annually.",
     AvailabilityStatus.yellow, "3:30 PM", "Poona Hospital & Research Centre"),

    # Sassoon Pune
    ("Dr. Rekha Thorat", "rekha.thorat@sassoon.com", "Doctor@123",
     "General Physician", 4, "English, Hindi, Marathi",
     "MBBS – BJ Medical College Pune",
     "Dedicated public sector physician providing accessible primary healthcare to underprivileged communities. Expert in managing infectious diseases and conducting community health programs.",
     AvailabilityStatus.green, None, "Sassoon General Hospital"),

    # Nemcare Guwahati
    ("Dr. Bhaskar Bora", "bhaskar.bora@nemcare.com", "Doctor@123",
     "Cardiologist", 14, "English, Hindi, Assamese",
     "MBBS, DM (Cardiology) – GMCH Guwahati",
     "Foremost cardiologist in Northeast India with expertise in cardiac imaging, device therapy and heart failure management. Has established the first cardiac electrophysiology lab in Assam.",
     AvailabilityStatus.green, None, "Nemcare Hospital"),

    ("Dr. Dipali Baruah", "dipali.b@nemcare.com", "Doctor@123",
     "Dermatologist", 9, "English, Assamese",
     "MBBS, MD (Dermatology) – Gauhati University",
     "Specialist in tropical dermatology, vitiligo treatment and hair restoration procedures. Runs the only dedicated hair transplant clinic in Guwahati with over 400 successful procedures.",
     AvailabilityStatus.yellow, "2:00 PM", "Nemcare Hospital"),

    # Downtown Guwahati
    ("Dr. Pranab Kalita", "pranab.k@downtown.com", "Doctor@123",
     "Neurologist", 11, "English, Hindi, Assamese",
     "MBBS, DM (Neurology) – NIMHANS",
     "Neurologist specialising in epilepsy management, cerebrovascular diseases and headache disorders. Established the first stroke unit in Northeast India at Downtown Hospital.",
     AvailabilityStatus.green, None, "Downtown Hospital"),

    ("Dr. Rima Das", "rima.das@downtown.com", "Doctor@123",
     "Gynecologist", 8, "English, Assamese, Bengali",
     "MBBS, MS (OBG) – Gauhati Medical College",
     "Expert in maternal-foetal medicine, reproductive endocrinology and laparoscopic surgery. Has managed over 1500 high-risk pregnancies with excellent maternal and foetal outcomes.",
     AvailabilityStatus.red, None, "Downtown Hospital"),

    # Wintrobe Guwahati
    ("Dr. Saurav Gogoi", "saurav.g@wintrobe.com", "Doctor@123",
     "Orthopedist", 10, "English, Assamese, Hindi",
     "MBBS, MS (Orthopaedics) – Gauhati University",
     "Orthopaedic surgeon specialising in spine surgery, trauma management and sports injuries. Trained at AIIMS Delhi with expertise in minimally invasive spinal procedures.",
     AvailabilityStatus.green, None, "Wintrobe Hospital"),

    ("Dr. Anita Hazarika", "anita.h@wintrobe.com", "Doctor@123",
     "General Physician", 6, "English, Assamese",
     "MBBS, MD (General Medicine) – Guwahati",
     "General physician with a focus on infectious diseases, preventive care and chronic disease management. Conducts regular health camps in rural Assam serving remote communities.",
     AvailabilityStatus.green, None, "Wintrobe Hospital"),

    # GMCH Guwahati
    ("Dr. Hemanta Nath", "hemanta.n@gmch.com", "Doctor@123",
     "General Physician", 3, "English, Hindi, Assamese",
     "MBBS – Gauhati Medical College",
     "Dedicated public sector physician providing primary and emergency care at GMCH. Expert in managing tropical diseases and providing affordable healthcare to patients from across Northeast India.",
     AvailabilityStatus.yellow, "7:00 PM", "Gauhati Medical College Hospital"),
]

# Hospital admin accounts (one per hospital)
HOSPITAL_ADMINS = [
    ("Admin Apollo HYD",      "admin.apollo.hyd@findadoctor.com",    "Admin@123", "Apollo Hospitals Jubilee Hills"),
    ("Admin Yashoda HYD",     "admin.yashoda.hyd@findadoctor.com",   "Admin@123", "Yashoda Hospitals Somajiguda"),
    ("Admin Care HYD",        "admin.care.hyd@findadoctor.com",      "Admin@123", "Care Hospitals Banjara Hills"),
    ("Admin Kamineni HYD",    "admin.kamineni.hyd@findadoctor.com",  "Admin@123", "Kamineni Hospitals LB Nagar"),
    ("Admin GGH HYD",         "admin.ggh.hyd@findadoctor.com",       "Admin@123", "Government General Hospital"),
    ("Admin Ruby Pune",       "admin.ruby.pune@findadoctor.com",     "Admin@123", "Ruby Hall Clinic"),
    ("Admin Jehangir Pune",   "admin.jehangir.pune@findadoctor.com", "Admin@123", "Jehangir Hospital"),
    ("Admin DMH Pune",        "admin.dmh.pune@findadoctor.com",      "Admin@123", "Deenanath Mangeshkar Hospital"),
    ("Admin Poona Pune",      "admin.poona.pune@findadoctor.com",    "Admin@123", "Poona Hospital & Research Centre"),
    ("Admin Sassoon Pune",    "admin.sassoon.pune@findadoctor.com",  "Admin@123", "Sassoon General Hospital"),
    ("Admin Nemcare GHY",     "admin.nemcare.ghy@findadoctor.com",   "Admin@123", "Nemcare Hospital"),
    ("Admin Downtown GHY",    "admin.downtown.ghy@findadoctor.com",  "Admin@123", "Downtown Hospital"),
    ("Admin Wintrobe GHY",    "admin.wintrobe.ghy@findadoctor.com",  "Admin@123", "Wintrobe Hospital"),
    ("Admin GMCH GHY",        "admin.gmch.ghy@findadoctor.com",      "Admin@123", "Gauhati Medical College Hospital"),
]

# Sample schedules for doctors (doctor_email, day, start, end, slot_minutes)
SCHEDULES = [
    ("ramesh.rao@apollo.com",    "monday",    "09:00", "13:00", 30),
    ("ramesh.rao@apollo.com",    "wednesday", "09:00", "13:00", 30),
    ("ramesh.rao@apollo.com",    "friday",    "09:00", "13:00", 30),
    ("priya.mehta@apollo.com",   "tuesday",   "10:00", "14:00", 30),
    ("priya.mehta@apollo.com",   "thursday",  "10:00", "14:00", 30),
    ("sanjay.gupta@apollo.com",  "monday",    "14:00", "18:00", 30),
    ("sanjay.gupta@apollo.com",  "wednesday", "14:00", "18:00", 30),
    ("kavitha.reddy@yashoda.com","tuesday",   "09:00", "13:00", 30),
    ("kavitha.reddy@yashoda.com","thursday",  "09:00", "13:00", 30),
    ("kavitha.reddy@yashoda.com","saturday",  "09:00", "12:00", 30),
    ("anjali.desai@ruby.com",    "monday",    "09:00", "13:00", 30),
    ("anjali.desai@ruby.com",    "tuesday",   "09:00", "13:00", 30),
    ("anjali.desai@ruby.com",    "thursday",  "09:00", "13:00", 30),
    ("bhaskar.bora@nemcare.com", "monday",    "10:00", "14:00", 30),
    ("bhaskar.bora@nemcare.com", "wednesday", "10:00", "14:00", 30),
    ("bhaskar.bora@nemcare.com", "friday",    "10:00", "14:00", 30),
    ("pranab.k@downtown.com",    "tuesday",   "09:00", "13:00", 30),
    ("pranab.k@downtown.com",    "thursday",  "09:00", "13:00", 30),
    ("pranab.k@downtown.com",    "saturday",  "09:00", "12:00", 30),
    ("meera.k@dmh.com",          "monday",    "09:00", "17:00", 30),
    ("meera.k@dmh.com",          "wednesday", "09:00", "17:00", 30),
    ("farooq@ggh.com",           "monday",    "08:00", "16:00", 30),
    ("farooq@ggh.com",           "tuesday",   "08:00", "16:00", 30),
    ("farooq@ggh.com",           "wednesday", "08:00", "16:00", 30),
    ("farooq@ggh.com",           "thursday",  "08:00", "16:00", 30),
    ("farooq@ggh.com",           "friday",    "08:00", "16:00", 30),
]


def seed():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if db.query(models.City).count() > 0:
            print("Database already seeded. Skipping.")
            return

        print("Seeding cities...")
        city_map = {}
        for name in CITIES:
            city = models.City(name=name)
            db.add(city)
            db.flush()
            city_map[name] = city

        print("Seeding hospitals and admins...")
        hospital_map = {}
        for (hname, city, tier, clean, addr, desc,
             phone, email, website) in HOSPITALS:

            # Create admin user first
            admin_data = next(
                (a for a in HOSPITAL_ADMINS if a[3] == hname), None)
            admin_user = None
            if admin_data:
                admin_user = models.User(
                    name=admin_data[0],
                    email=admin_data[1],
                    password_hash=pwd_context.hash(admin_data[2]),
                    role=UserRole.hospital_admin
                )
                db.add(admin_user)
                db.flush()

            hospital = models.Hospital(
                name=hname,
                city_id=city_map[city].id,
                budget_tier=tier,
                cleanliness_rating=clean,
                address=addr,
                description=desc,
                phone=phone,
                email=email,
                website=website,
                quality_score=0.0,
                verification_status=VerificationStatus.approved,
                admin_id=admin_user.id if admin_user else None,
                verified_at=datetime.utcnow()
            )
            db.add(hospital)
            db.flush()
            hospital_map[hname] = hospital

            # Link hospital back to admin
            if admin_user:
                pass  # admin_id already set above

        print("Seeding doctors...")
        doctor_user_map = {}
        for (name, email, password, spec, exp, langs,
             edu, bio, avail, avail_from, hname) in DOCTORS:

            hosp = hospital_map[hname]
            user = models.User(
                name=name,
                email=email,
                password_hash=pwd_context.hash(password),
                role=UserRole.doctor
            )
            db.add(user)
            db.flush()

            doctor = models.Doctor(
                user_id=user.id,
                hospital_id=hosp.id,
                specialisation=spec,
                experience_years=exp,
                languages=langs,
                education=edu,
                bio=bio,
                availability=avail,
                available_from=avail_from,
                consultation_fee=FEE_MAP[hosp.budget_tier],
                avg_rating=0.0,
                review_count=0,
                verification_status=VerificationStatus.approved,
                verified_at=datetime.utcnow()
            )
            db.add(doctor)
            db.flush()
            doctor_user_map[email] = doctor

        print("Seeding schedules...")
        for (doc_email, day, start, end, slot) in SCHEDULES:
            doctor = doctor_user_map.get(doc_email)
            if doctor:
                schedule = models.DoctorSchedule(
                    doctor_id=doctor.id,
                    day_of_week=day,
                    start_time=start,
                    end_time=end,
                    slot_duration_minutes=slot
                )
                db.add(schedule)

        db.commit()

        # Recompute hospital quality scores
        db.expire_all()
        for h in db.query(models.Hospital).all():
            doctors = db.query(models.Doctor).filter(
                models.Doctor.hospital_id == h.id).all()
            if doctors:
                avg = sum(d.avg_rating for d in doctors) / len(doctors)
                h.quality_score = round(
                    avg * 0.7 + h.cleanliness_rating * 0.3, 2)
        db.commit()

        print("\n✅ Seed complete!")
        print("\n── Staff credentials ─────────────────────────────")
        print("  Hyderabad : staff_hyderabad / StaffHyd@2026")
        print("  Pune      : staff_pune      / StaffPun@2026")
        print("  Guwahati  : staff_guwahati  / StaffGhy@2026")
        print("\n── Hospital admin credentials (password: Admin@123) ──")
        for a in HOSPITAL_ADMINS:
            print(f"  {a[0]:<25} {a[1]}")
        print("\n── Doctor credentials (password: Doctor@123) ────────")
        for d in DOCTORS:
            print(f"  {d[0]:<28} {d[1]}")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()