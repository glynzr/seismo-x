"""
CaspianPetro SGX Binary Format

Header (16 bytes):
- magic[8]      : b'CPETRO01'
- survey_type   : uint16
- trace_count   : uint32

Trace Record (13 bytes):
- well_id       : uint16
- depth         : float32
- amplitude     : float32
- quality_flag  : uint8
Little Endian
"""
