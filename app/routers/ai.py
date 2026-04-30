from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import Optional
import os, json
from groq import Groq
from app.db import get_db
from app import models
from app.schemas import AIRecommendRequest, AIRecommendResponse, DoctorListItem
from app.routers.doctors import doctor_to_list_item

router = APIRouter(prefix="/ai", tags=["AI"])

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


@router.post("/recommend", response_model=AIRecommendResponse)
def ai_recommend(
    payload: AIRecommendRequest,
    db: Session = Depends(get_db)
):
    # Fetch all approved doctors with their hospital info
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

    # Build context for Groq
    doctor_context = []
    for d in doctors:
        doctor_context.append({
            "id":               d.id,
            "name":             d.user.name,
            "specialisation":   d.specialisation,
            "experience_years": d.experience_years,
            "bio":              d.bio or "",
            "education":        d.education or "",
            "languages":        d.languages or "",
            "avg_rating":       d.avg_rating,
            "availability":     d.availability.value,
            "hospital":         d.hospital.name if d.hospital else "",
            "hospital_desc":    d.hospital.description or "" if d.hospital else "",
            "city":             d.hospital.city.name if d.hospital else "",
            "budget_tier":      d.hospital.budget_tier.value if d.hospital else "",
            "consultation_fee": d.consultation_fee,
        })

    prompt = f"""
You are a medical recommendation assistant for FindADoctor, a platform in India.

A patient has described their problem:
"{payload.problem_description}"

Here are the available doctors:
{json.dumps(doctor_context, indent=2)}

Your task:
1. Identify the most relevant medical specialisation for this problem
2. Select the top 3 most suitable doctors based on specialisation match, experience, rating, bio, and availability
3. Return their IDs and a brief explanation of why they are recommended

Respond ONLY with a valid JSON object in this exact format:
{{
  "suggested_specialisation": "Cardiologist",
  "recommended_doctor_ids": [1, 5, 12],
  "explanation": "Based on your symptoms of chest pain and shortness of breath, you need a Cardiologist. These doctors were selected for their expertise in cardiac conditions, high ratings, and current availability."
}}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a medical recommendation assistant. You always respond with valid JSON only, no markdown, no extra text."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=1000,
            temperature=0.3
        )
        text = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
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

    recommended_doctors = [d for d in doctors if d.id in recommended_ids]
    recommended_doctors.sort(key=lambda d: recommended_ids.index(d.id)
                             if d.id in recommended_ids else 99)

    # Get unique hospitals of recommended doctors
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