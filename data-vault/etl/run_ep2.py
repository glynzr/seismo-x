import subprocess
import sys

def run(cmd):
    print("\n>", " ".join(cmd))
    subprocess.check_call(cmd)

def main():
    # Load master CSVs (use data/ folder)
    run([sys.executable, "etl/load_masters.py", "--data-dir", "data/masters"])

    # Build Data Vault
    print("\n[Step 1/5] Building Data Vault...")
    run([sys.executable, "etl/build_vault_wells_surveys.py"])
    run([sys.executable, "etl/build_vault_sensors.py"])
    run([sys.executable, "etl/build_vault_track1_readings.py"])

    # Validate
    print("\n[Step 2/5] Running data quality tests...")
    run([sys.executable, "tests/test_data_quality.py"])

    # Build analytics layer
    print("\n[Step 3/5] Building star schema...")
    run([sys.executable, "etl/build_star_schema.py"])
    
    print("\n[Step 4/5] Building marts and exporting to Delta Lake...")
    run([sys.executable, "etl/build_marts.py"])

    print("\n" + "="*80)
    print("✅ EP2 pipeline completed successfully!")
    print("="*80)
    print("\nNext steps:")
    print("  - Run dashboard: streamlit run dashboards/app.py")
    print("  - Test time travel: python etl/delta_time_travel_demo.py")

if __name__ == "__main__":
    main()
