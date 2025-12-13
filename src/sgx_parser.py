"""
Parser for legacy .sgx binary format.
Format specification:
- 16-byte global header: magic ('CPETRO01'), survey type, trace count
- Trace records: 13 bytes each (well_id, depth, amplitude, quality_flag)
- Little Endian encoding
"""
import struct
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
import numpy as np


class SGXParser:
    """Parser for .sgx binary format files."""
    
    MAGIC = b'CPETRO01'
    HEADER_SIZE = 16
    TRACE_RECORD_SIZE = 13
    
    def __init__(self, file_path: str):
        """
        Initialize parser with .sgx file path.
        
        Args:
            file_path: Path to .sgx file
        """
        self.file_path = file_path
        self.magic = None
        self.survey_type = None
        self.trace_count = None
        self.traces = []
    
    def parse(self) -> pd.DataFrame:
        """
        Parse .sgx file and return DataFrame.
        
        Returns:
            DataFrame with columns: well_id, depth, amplitude, quality_flag, survey_type
        """
        with open(self.file_path, 'rb') as f:
            # Read 16-byte header
            header = f.read(self.HEADER_SIZE)
            
            if len(header) < self.HEADER_SIZE:
                raise ValueError(f"File too short: {len(header)} bytes")
            
           
            self.magic = header[0:8]
            if self.magic != self.MAGIC:
                raise ValueError(f"Invalid magic number: {self.magic}")
            
           
            self.survey_type = struct.unpack('<I', header[8:12])[0]
            

            self.trace_count = struct.unpack('<I', header[12:16])[0]

            traces = []
            for i in range(self.trace_count):
                trace_data = f.read(self.TRACE_RECORD_SIZE)
                if len(trace_data) < self.TRACE_RECORD_SIZE:
                    break  # End of file
                
                # Parse trace record (13 bytes)
                # Bytes 0-3: well_id (4 bytes, little endian, unsigned int)
                well_id = struct.unpack('<I', trace_data[0:4])[0]
                
                # Bytes 4-7: depth (4 bytes, little endian, float)
                depth = struct.unpack('<f', trace_data[4:8])[0]
                
                # Bytes 8-11: amplitude (4 bytes, little endian, float)
                amplitude = struct.unpack('<f', trace_data[8:12])[0]
                
                # Byte 12: quality_flag (1 byte, unsigned char)
                quality_flag = struct.unpack('<B', trace_data[12:13])[0]
                
                traces.append({
                    'well_id': well_id,
                    'depth': depth,
                    'amplitude': amplitude,
                    'quality_flag': quality_flag,
                    'survey_type': self.survey_type,
                    'source_file': Path(self.file_path).name
                })
            
            self.traces = traces
            
            # Create DataFrame
            df = pd.DataFrame(traces)
            return df
    
    def to_parquet(self, output_path: str) -> None:
        """
        Convert .sgx file to Parquet format.
        
        Args:
            output_path: Path to save Parquet file
        """
        df = self.parse()
        df.to_parquet(output_path, index=False)


def parse_sgx_file(file_path: str) -> pd.DataFrame:
    """
    Convenience function to parse .sgx file.
    
    Args:
        file_path: Path to .sgx file
        
    Returns:
        DataFrame with parsed data
    """
    parser = SGXParser(file_path)
    return parser.parse()


def convert_sgx_to_parquet(input_path: str, output_path: str) -> None:
    """
    Convert .sgx file to Parquet format.
    
    Args:
        input_path: Path to .sgx file
        output_path: Path to save Parquet file
    """
    parser = SGXParser(input_path)
    parser.to_parquet(output_path)


def batch_convert_sgx(data_dir: str, output_dir: str) -> pd.DataFrame:
    """
    Convert all .sgx files in directory to Parquet.
    
    Args:
        data_dir: Directory containing .sgx files
        output_dir: Directory to save Parquet files
        
    Returns:
        Combined DataFrame of all converted data
    """
    import os
    from pathlib import Path
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    all_data = []
    
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith('.sgx'):
                input_path = os.path.join(root, file)
                output_path = os.path.join(output_dir, file.replace('.sgx', '.parquet'))
                
                try:
                    parser = SGXParser(input_path)
                    df = parser.parse()
                    df.to_parquet(output_path, index=False)
                    all_data.append(df)
                    print(f"Converted: {file} -> {Path(output_path).name}")
                except Exception as e:
                    print(f"Error converting {file}: {e}")
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    else:
        return pd.DataFrame()


