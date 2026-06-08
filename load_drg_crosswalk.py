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

# ── LOAD DRG MDC CROSSWALK ──
df = pd.read_csv('drg_mdc_crosswalk.csv', dtype=str)
print(f"DRG crosswalk loaded: {len(df)} rows")
print(f"Columns: {list(df.columns)}")

df.columns = [c.upper().strip() for c in df.columns]
df = df.where(pd.notnull(df), None)

# Create table first
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS BRG_PROVIDER_ANALYTICS.RAW.DRG_MDC_CROSSWALK (
        MS_DRG      VARCHAR,
        PA_DRG      VARCHAR,
        NPRM_DRG    VARCHAR,
        MDC         VARCHAR,
        TYPE        VARCHAR,
        MSDRG_TITLE VARCHAR,
        WEIGHTS     VARCHAR,
        LOS_GEO     VARCHAR,
        LOS_MEAN    VARCHAR,
        LOAD_TIMESTAMP TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
    )
""")
print("Table created")

success, nchunks, nrows, _ = write_pandas(
    conn=conn,
    df=df,
    table_name='DRG_MDC_CROSSWALK',
    database='BRG_PROVIDER_ANALYTICS',
    schema='RAW',
    overwrite=True
)
print(f"DRG crosswalk loaded: {nrows} rows")

# ── VERIFY ──
cursor.execute("SELECT COUNT(*) FROM BRG_PROVIDER_ANALYTICS.RAW.DRG_MDC_CROSSWALK")
print(f"Row count: {cursor.fetchone()[0]}")

cursor.execute("""
    SELECT MDC, COUNT(*) as drg_count 
    FROM BRG_PROVIDER_ANALYTICS.RAW.DRG_MDC_CROSSWALK 
    GROUP BY MDC 
    ORDER BY MDC
""")
print("\nMDC distribution:")
for row in cursor.fetchall():
    print(f"  MDC {row[0]}: {row[1]} DRGs")

cursor.close()
conn.close()
print("Done")
