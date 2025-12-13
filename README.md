# The Parquet Enigma
## Task 1(finding flag)
```
cd solutions
chmod +x flag_parquet.sh
./parquet.sh --data-dir <path to caspian_hackathon_assets>
```
Results(both flag and fixed parquet file) for this challenge will be on processed_data/archive_batch_seismic_readings-parquet

## Loading corrupted parquet files
Only archive_batch_seismic_readings.parquet file is corrupted.Recovered file is stored on processed_data/recovered-parquet
How to recover the file?
```
solutions/corrupted_parquet.sh --data-dir <path to caspian_hackathon_assets>
```
