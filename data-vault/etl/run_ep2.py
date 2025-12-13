import subprocess
import sys

def run(cmd):
    print("\n>", " ".join(cmd))
    subprocess.check_call(cmd)

def main():
    # Load master CSVs (explicit path so teammate doesn't guess)
    run([sys.executable, "etl/load_masters.py", "--data-dir", "data/masters"])

    # Build Data Vault
    run([sys.executable, "etl/build_vault_wells_surveys.py"])
    run([sys.executable, "etl/build_vault_sensors.py"])
    run([sys.executable, "etl/build_vault_track1_readings.py"])

    # Validate
    run([sys.executable, "tests/test_data_quality.py"])

    # Build analytics layer
    run([sys.executable, "etl/build_star_schema.py"])
    run([sys.executable, "etl/build_marts.py"])

    print("\nEP2 pipeline completed successfully.")

if __name__ == "__main__":
    main()
