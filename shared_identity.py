import hashlib
import hmac


def hash_pin(name, pin):
    value = f"{str(name).strip().casefold()}::{str(pin).strip()}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def verify_pin(name, pin, expected_hash):
    if not expected_hash:
        return False
    return hmac.compare_digest(hash_pin(name, pin), str(expected_hash))


def active_directory(extra):
    collaboration = extra.get("collaboration", {})
    users = collaboration.get("users", [])
    hashes = collaboration.get("pin_hashes", {})
    result = []
    for row in users:
        if not row.get("active", True):
            continue
        name = str(row.get("name", "")).strip()
        if not name:
            continue
        result.append({
            "name": name,
            "email": str(row.get("email", "")).strip().casefold(),
            "role": str(row.get("role", "")),
            "department": str(row.get("department", "")),
            "admin": bool(row.get("admin", False)),
            "pin_hash": str(hashes.get(name, "")),
        })
    return result
