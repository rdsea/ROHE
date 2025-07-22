
import os
import subprocess
import duckdb

DB_PATH = './file.duckdb'
CONTAINER_NAME = 'duckdb_container'
IMAGE_NAME = 'airbyte/destination-duckdb'
INSTANCE_TABLE = 'inference_service_instance'
SERVICE_TABLE = 'inference_service'
MONITORING_TABLE = 'monitoring_report'
INFERENCE_RESULT_TABLE = 'inference_result'

# Connect to the DuckDB database
conn = duckdb.connect(DB_PATH)

# Remove all data from the database



conn.execute(f"DROP TABLE IF EXISTS {INSTANCE_TABLE};")

conn.execute(f"""
CREATE TABLE {INSTANCE_TABLE} (
    instance_id TEXT,
    model_id TEXT,
    model_version TEXT,
    device_id TEXT,
    device_type TEXT,
    ip_address TEXT,
    port INT,
    modality TEXT,
    inference_service_id TEXT,
    data TEXT
);
""")

conn.execute(f"DROP TABLE IF EXISTS {SERVICE_TABLE};")

conn.execute(f"""
CREATE TABLE {SERVICE_TABLE} (
    inference_service_id TEXT,
    model_id TEXT,
    model_version TEXT,
    device_type TEXT,
    modality TEXT,
    data TEXT
);
""")

conn.execute(f"DROP TABLE IF EXISTS {MONITORING_TABLE};")
conn.execute(f"""
CREATE TABLE {MONITORING_TABLE} (
    query_id TEXT,
    inf_id TEXT,
    instance_id TEXT,
    inf_time FLOAT,
    time_window INT,
    model_id TEXT,
    device_id TEXT,
    model_version TEXT,
    response_time FLOAT,
    data_source TEXT,
    explainability TEXT,
    data TEXT
);
""")

conn.execute(f"DROP TABLE IF EXISTS {INFERENCE_RESULT_TABLE};")
conn.execute(f"""
CREATE TABLE IF NOT EXISTS {INFERENCE_RESULT_TABLE} (
    inference_time TEXT,
    data JSON,
    query_id TEXT,
    task_id TEXT,
    inf_id TEXT
);
""")

# # Load new data from the file

print("Database has been reset and new data has been loaded.")