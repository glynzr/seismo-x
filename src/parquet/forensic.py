import re
from pathlib import Path

FLAG_PATTERN = rb"FLAG\{[^}]+\}"

def extract_flag(path: Path) -> str | None:
    data = path.read_bytes()
    match = re.search(FLAG_PATTERN, data)
    return match.group(0).decode(errors="ignore") if match else None
