# setting up env
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

# The Parquet Enigma

Make scripts executable:
```
chmod +x solutions/*.sh

```

Run script for getting flag:
```
solutions/flag_parquet.sh --data-dir <data folder>
```

flag.txt will be in processed_data/flag


Only 1 parquet file is corrupted . For recovery run this script:
```
solutions/corrupted_parquet.sh --data-dir <data folder>
```

Recovered parquet file will be stored in processed_data/recovered-parquet


Converted files(from sgx to parquet) will be stored in processed_data/sgx_converted
For converting:
```
solutions/load_sgx.sh --data-dir <path to caspian_hackathon_assets>
```