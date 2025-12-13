import struct
import pandas as pd


TRACE_FMT = "<HffB2x"
TRACE_SIZE = struct.calcsize(TRACE_FMT)  # now 13 bytes ✅

def parse_traces(blob: bytes, survey_type: int):
    rows = []

    for i in range(0, len(blob), TRACE_SIZE):
        chunk = blob[i:i + TRACE_SIZE]

        # SAFETY: skip incomplete records
        if len(chunk) != TRACE_SIZE:
            continue

        well_id, depth, amplitude, quality = struct.unpack(TRACE_FMT, chunk)
        rows.append((well_id, depth, amplitude, quality, survey_type))

    return rows
