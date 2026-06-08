import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
import pandas as pd
import os

conn = snowflake.connector.connect(
    user=os.environ.get('SNOWFLAKE_USER'),
    password=os.environ.get('SNOWFLAKE_PASSWORD'),
    account='lfzytsf-ot13072',
    warehouse='COMPUTE_WH',
    database='BRG_PROVIDER_ANALYTICS',
    schema='RAW'
)
print("Connected to Snowflake")

df = pd.read_csv('health_system_reference.csv', dtype=str)
df.columns = ['KEYWORD', 'HEALTH_SYSTEM']
df = df.where(pd.notnull(df), None)

print(f"Loaded {len(df)} keywords from CSV")

success, nchunks, nrows, _ = write_pandas(
    conn=conn,
    df=df,
    table_name='HEALTH_SYSTEM_REFERENCE',
    database='BRG_PROVIDER_ANALYTICS',
    schema='RAW',
    overwrite=True
)
print(f"Loaded {nrows} rows into HEALTH_SYSTEM_REFERENCE")

cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM BRG_PROVIDER_ANALYTICS.RAW.HEALTH_SYSTEM_REFERENCE")
print(f"Row count: {cursor.fetchone()[0]}")

cursor.close()
conn.close()
print("Done")
