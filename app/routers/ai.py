from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
import os, json
from groq import Groq
from app.db import get_db
from app import models
from app.schemas import AIRecommendRequest, AIRecommendResponse
from app.routers.doctors import doctor_to_list_item

router = APIRouter(prefix="/ai", tags=["AI"])
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


@router.post("/recommend", response_model=AIRecommendResponse)
def ai_recommend(
    payload: AIRecommendRequest,
    db: Session = Depends(get_db)
):
    q = (db.query(models.Doctor)
         .join(models.Doctor.hospital)
         .options(
             joinedload(models.Doctor.user),
             joinedload(models.Doctor.hospital).joinedload(models.Hospital.city)
         )
         .filter(
             models.Doctor.verification_status == models.VerificationStatus.approved,
             models.Doctor.hospital_id.isnot(None),
             models.Hospital.verification_status == models.VerificationStatus.approved
         ))

    if payload.city_id:
        q = q.filter(models.Hospital.city_id == payload.city_id)
    if payload.budget:
        q = q.filter(models.Hospital.budget_tier == payload.budget)

    doctors = q.all()

    if not doctors:
        raise HTTPException(status_code=404,
                            detail="No doctors found matching your filters")

    doctor_context = []
    for d in doctors:
        doctor_context.append({
            "id":               d.id,
            "name":             d.user.name,
            "specialisation":   d.specialisation,
            "experience_years": d.experience_years,
            "bio":              d.bio or "",
            "avg_rating":       d.avg_rating,
            "availability":     d.availability.value,
            "hospital":         d.hospital.name if d.hospital else "",
            "city":             d.hospital.city.name if d.hospital else "",
            "consultation_fee": d.consultation_fee,
        })

    prompt = f"""
You are a medical recommendation assistant for Docfolio, a healthcare platform in India.

Patient's problem: "{payload.problem_description}"

Available doctors (ONLY choose from this list, ONLY use their exact IDs):
{json.dumps(doctor_context, indent=2)}

Rules:
1. First identify the correct medical specialisation for this problem
2. Select ONLY doctors whose specialisation matches that identified specialisation
3. From those matching doctors, pick the top 3 based on: availability (green first), experience, rating
4. NEVER recommend a doctor whose specialisation does not match the identified specialisation
5. If fewer than 3 doctors match the specialisation, return only the ones that do

Respond ONLY with this exact JSON format, no other text:
{{
  "suggested_specialisation": "Cardiologist",
  "recommended_doctor_ids": [1, 5, 10],
  "explanation": "Brief explanation of why these doctors were chosen."
}}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a medical recommendation assistant. You respond ONLY with valid JSON. No markdown, no backticks, no extra text whatsoever."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=500,
            temperature=0.1
        )
        text = response.choices[0].message.content.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text.strip())
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"AI recommendation failed: {str(e)}")

    recommended_ids = result.get("recommended_doctor_ids", [])
    explanation     = result.get("explanation", "")
    suggested_spec  = result.get("suggested_specialisation", "")

    # Hard filter: only return doctors whose specialisation matches
    recommended_doctors = [
        d for d in doctors
        if d.id in recommended_ids
        and d.specialisation.lower() == suggested_spec.lower()
    ]
    recommended_doctors.sort(
        key=lambda d: recommended_ids.index(d.id)
        if d.id in recommended_ids else 99
    )

    seen_hosp = set()
    recommended_hospitals = []
    for d in recommended_doctors:
        if d.hospital and d.hospital.id not in seen_hosp:
            seen_hosp.add(d.hospital.id)
            recommended_hospitals.append(d.hospital)

    return AIRecommendResponse(
        recommended_doctors=[doctor_to_list_item(d, doctors)
                             for d in recommended_doctors],
        recommended_hospitals=recommended_hospitals,
        explanation=explanation,
        suggested_specialisation=suggested_spec
    )