"""
EP2 Seismic Data Reconstruction & Modeling - Main Entry Point

This is the main entry point for the EP2 pipeline.
Run the complete ETL pipeline with: python main.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from etl.run_ep2 import main

if __name__ == '__main__':
    main()
