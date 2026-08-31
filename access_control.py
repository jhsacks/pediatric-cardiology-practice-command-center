import hashlib
import hmac


def pin_hash(name, pin):
    raw = f"{str(name).strip().casefold()}::{str(pin).strip()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def verify_pin(name, pin, expected):
    return bool(expected) and hmac.compare_digest(pin_hash(name, pin), str(expected))


def active_users(extra):
    data = extra.get("collaboration", {})
    hashes = data.get("pin_hashes", {})
    result = []
    for row in data.get("users", []):
        if not row.get("active", True) or not str(row.get("name", "")).strip():
            continue
        item = dict(row)
        item["pin_hash"] = hashes.get(item["name"], "")
        result.append(item)
    return result
