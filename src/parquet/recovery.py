from pathlib import Path

PARQUET_MAGIC = b"PAR1"

def recover_parquet(src: Path, dst: Path) -> dict:
    data = src.read_bytes()
    last = data.rfind(PARQUET_MAGIC)

    if last == -1:
        return {"status": "invalid", "removed_bytes": 0}

    fixed = data[: last + 4]
    removed = len(data) - len(fixed)

    if removed > 0:
        dst.write_bytes(fixed)
        return {"status": "repaired", "removed_bytes": removed}

    return {"status": "ok", "removed_bytes": 0}
