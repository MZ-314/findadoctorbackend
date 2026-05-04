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
    # Fetch doctors — apply city and budget filter BEFORE sending to AI
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
        raise HTTPException(
            status_code=404,
            detail="No approved doctors found matching your filters. Try a different city or budget."
        )

    # Get city name for context
    city_name = None
    if payload.city_id:
        city = db.query(models.City).filter(models.City.id == payload.city_id).first()
        city_name = city.name if city else None

    # Validate that user actually described something meaningful
    description = payload.problem_description.strip()
    if len(description) < 10:
        raise HTTPException(
            status_code=400,
            detail="Please describe your symptoms in more detail so we can find the right doctor for you."
        )

    # Build minimal doctor context — only what AI needs
    doctor_context = []
    for d in doctors:
        doctor_context.append({
            "id":               d.id,
            "name":             d.user.name,
            "specialisation":   d.specialisation,
            "experience_years": d.experience_years,
            "bio":              (d.bio or "")[:200],  # truncate to save tokens
            "avg_rating":       d.avg_rating,
            "availability":     d.availability.value,
            "hospital":         d.hospital.name if d.hospital else "",
            "city":             d.hospital.city.name if d.hospital else "",
            "consultation_fee": d.consultation_fee,
        })

    city_instruction = f"The patient is looking for doctors in {city_name} ONLY. Do NOT recommend doctors from other cities." if city_name else "No city preference — recommend the best matches regardless of city."

    prompt = f"""You are a medical recommendation assistant for Docfolio, a healthcare platform in India.

PATIENT'S EXACT DESCRIPTION: "{description}"

{city_instruction}

AVAILABLE DOCTORS (these are the ONLY doctors you can recommend):
{json.dumps(doctor_context, indent=2)}

YOUR TASK:
1. Read the patient's description carefully and identify the correct medical specialisation and location. For example, if the patient says "I have chest pain and shortness of breath", the specialisation is likely "Cardiologist". If they say "I have a skin rash that won't go away", the specialisation is likely "Dermatologist". If the description is too vague to determine a specialisation, set suggested_specialisation to "unclear".
2. From the available doctors list above, find doctors whose specialisation and location matches
3. Rank them by: availability (green first), then experience, then rating
4. Return EXACTLY the top 3 matching doctors by their IDs. Do NOT recommend doctors that do not match the specialisation or city (if city was specified). If fewer than 3 doctors match, return only those that match — do not fill slots with wrong specialisations.

STRICT RULES:
- You MUST only recommend doctors from the list above
- You MUST only recommend doctors whose specialisation directly matches the patient's condition
- If the patient selected a city, ALL recommended doctors MUST be from that city
- If fewer than 3 doctors match, return only those that match — do not fill slots with wrong specialisations
- If the description is too vague to identify a specialisation, set suggested_specialisation to "unclear"
- Never invent or assume doctors not in the list

Respond ONLY with valid JSON, no markdown, no explanation outside the JSON:
{{
  "suggested_specialisation": "Cardiologist",
  "recommended_doctor_ids": [18],
  "explanation": "Based on your chest pain, you need a Cardiologist. Only Dr. Bhaskar Bora is available in Guwahati with this specialisation."
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a medical recommendation assistant. You respond ONLY with valid JSON. No markdown, no backticks, no extra text. You strictly follow the rules given to you."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=400,
            temperature=0.05  # as close to deterministic as possible
        )
        text = response.choices[0].message.content.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text.strip())
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI returned an invalid response. Please try again.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI recommendation failed: {str(e)}")

    suggested_spec = result.get("suggested_specialisation", "")
    recommended_ids = result.get("recommended_doctor_ids", [])
    explanation = result.get("explanation", "")

    # If AI says unclear, reject with helpful message
    if suggested_spec.lower() == "unclear":
        raise HTTPException(
            status_code=400,
            detail="Your description is too vague. Please describe your symptoms in more detail — for example: 'I have chest pain and shortness of breath' or 'I have a skin rash that won't go away'."
        )

    # HARD FILTER — only return doctors that:
    # 1. Are in the recommended_ids list
    # 2. Have the correct specialisation
    # 3. Are in the correct city (if city was specified)
    recommended_doctors = [
        d for d in doctors
        if d.id in recommended_ids
        and d.specialisation.lower() == suggested_spec.lower()
    ]

    # If city was selected, enforce city filter on final results too
    if payload.city_id:
        recommended_doctors = [
            d for d in recommended_doctors
            if d.hospital and d.hospital.city_id == payload.city_id
        ]

    if not recommended_doctors:
        raise HTTPException(
            status_code=404,
            detail=f"No {suggested_spec}s found{f' in {city_name}' if city_name else ''}. Try searching without a city filter or choose a different specialisation."
        )

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
        recommended_doctors=[doctor_to_list_item(d, doctors) for d in recommended_doctors],
        recommended_hospitals=recommended_hospitals,
        explanation=explanation,
        suggested_specialisation=suggested_spec
    )