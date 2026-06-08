import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
import pandas as pd
import os

# ── CREDENTIALS ──
conn = snowflake.connector.connect(
    user=os.environ.get('SNOWFLAKE_USER'),
    password=os.environ.get('SNOWFLAKE_PASSWORD'),
    account='lfzytsf-ot13072',
    warehouse='COMPUTE_WH',
    database='BRG_PROVIDER_ANALYTICS',
    schema='RAW'
)

print("Connected to Snowflake")

# ── LOAD CSV ──
df = pd.read_csv('RAW_provider_volume_dirty.csv')
print(f"CSV loaded: {len(df)} rows")

# ── FORCE UPPERCASE COLUMN NAMES TO MATCH SNOWFLAKE ──
df.columns = [
    'SOURCE_PROVIDER_NAME',
    'SOURCE_HEALTH_SYSTEM',
    'SOURCE_GEOGRAPHY',
    'SOURCE_SERVICE_LINE',
    'SOURCE_MARKET',
    'SOURCE_PERIOD',
    'SOURCE_VOLUME',
    'PAYER_TYPE',
    'DATA_SOURCE',
    'SOURCE_FILE'
]

# ── REPLACE NaN WITH None ──
df = df.where(pd.notnull(df), None)

print("Writing to Snowflake...")

success, nchunks, nrows, _ = write_pandas(
    conn=conn,
    df=df,
    table_name='PROVIDER_VOLUME_RAW',
    database='BRG_PROVIDER_ANALYTICS',
    schema='RAW',
    overwrite=True
)

print(f"Load complete: {nrows} rows written in {nchunks} chunks")

# ── VERIFY ──
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM BRG_PROVIDER_ANALYTICS.RAW.PROVIDER_VOLUME_RAW")
count = cursor.fetchone()[0]
print(f"Snowflake row count: {count}")

cursor.close()
conn.close()
print("Done")
