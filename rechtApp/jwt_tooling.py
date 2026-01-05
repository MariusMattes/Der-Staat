import time
import jwt

# WICHTIG:
# Dieser Schlüssel MUSS auf ALLEN Servern IDENTISCH sein
JWT_SECRET = "Kai hat den richtigen Schlüssel"
JWT_ALGORITHM = "HS256"
JWT_LIFETIME_SECONDS = 300  # 5 Minuten

def create_jwt(buerger_id: str) -> str:
    """
    Erzeugt ein JWT mit Bürger-ID.
    """
    now = int(time.time())
    payload = {
        "user_id": str(buerger_id),
        "iat": now,
        "exp": now + JWT_LIFETIME_SECONDS,
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    # PyJWT < 2.x liefert bytes zurück
    if isinstance(token, bytes):
        token = token.decode("utf-8")

    return token


def decode_jwt(token: str) -> dict:
    """
    Prüft und dekodiert ein JWT.
    Wirft Exception bei ungültigem / abgelaufenem Token.
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
