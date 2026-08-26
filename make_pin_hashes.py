import hashlib
import sys

for pin in sys.argv[1:]:
    print(pin, hashlib.sha256(pin.encode("utf-8")).hexdigest())
