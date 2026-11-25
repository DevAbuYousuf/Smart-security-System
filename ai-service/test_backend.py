
from backend_client import send_security_event

send_security_event(
    event_type="UNKNOWN_PERSON",
    person_name="Unknown Person",
    status="UNAUTHORIZED",
    confidence=82.45,
    snapshot=None
)
