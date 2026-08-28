from pathlib import Path
p=Path('app.py'); s=p.read_text()
# Package intentionally leaves Practice app.py routing unchanged.
p.write_text(s)
