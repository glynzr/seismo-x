from pathlib import Path


def recover_parquet(src: Path, dst: Path) -> dict:
    data = src.read_bytes()

    last_par1 = data.rfind(b"PAR1")
    if last_par1 == -1:
        return {
            "status": "invalid",
            "removed_bytes": 0,
        }

    fixed_data = data[: last_par1 + 4]
    removed = len(data) - len(fixed_data)

    if removed > 0:
        dst.write_bytes(fixed_data)
        return {
            "status": "repaired",
            "removed_bytes": removed,
        }

    return {
        "status": "ok",
        "removed_bytes": 0,
    }
