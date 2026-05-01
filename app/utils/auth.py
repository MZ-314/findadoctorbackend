from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY                 = os.getenv("SECRET_KEY") or ""
ALGORITHM                  = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

def _build_staff_credentials() -> dict:
    creds = {}
    entries = [
        ("Hyderabad", os.getenv("STAFF_HYD_USERNAME"), os.getenv("STAFF_HYD_PASSWORD")),
        ("Pune", os.getenv("STAFF_PUN_USERNAME"), os.getenv("STAFF_PUN_PASSWORD")),
        ("Guwahati", os.getenv("STAFF_GHY_USERNAME"), os.getenv("STAFF_GHY_PASSWORD")),
    ]
    for city, username, password in entries:
        if username and password:
            creds[username] = {"password": password, "city": city}
    return creds


STAFF_CREDENTIALS = _build_staff_credentials()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict,
                        expires_delta: Optional[timedelta] = None) -> str:
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY is not set")
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def verify_staff_credentials(username: str, password: str) -> Optional[dict]:
    staff = STAFF_CREDENTIALS.get(username)
    if staff and staff["password"] == password:
        return {"username": username, "city": staff["city"]}
    return None