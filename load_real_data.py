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

# ── LOAD HOSPITAL GENERAL INFO ──
print("Loading Hospital General Info...")
hgi = pd.read_csv('Hospital_General_Information.csv', dtype=str)

# Keep only columns we need
hgi = hgi[[
    'Facility ID',
    'Facility Name', 
    'Address',
    'City/Town',
    'State',
    'ZIP Code',
    'County/Parish',
    'Telephone Number',
    'Hospital Type',
    'Hospital Ownership',
    'Emergency Services',
    'Hospital overall rating'
]]

# Rename to match Snowflake table
hgi.columns = [
    'FACILITY_ID',
    'FACILITY_NAME',
    'ADDRESS',
    'CITY',
    'STATE',
    'ZIP_CODE',
    'COUNTY',
    'PHONE',
    'HOSPITAL_TYPE',
    'HOSPITAL_OWNERSHIP',
    'EMERGENCY_SERVICES',
    'OVERALL_RATING'
]

hgi = hgi.where(pd.notnull(hgi), None)

success, nchunks, nrows, _ = write_pandas(
    conn=conn,
    df=hgi,
    table_name='HOSPITAL_GENERAL_INFO',
    database='BRG_PROVIDER_ANALYTICS',
    schema='RAW',
    overwrite=True
)
print(f"Hospital General Info: {nrows} rows loaded")

# ── LOAD MEDICARE INPATIENT VOLUME ──
print("Loading Medicare Inpatient Volume (this may take 30 seconds)...")
med = pd.read_csv('medicare_inpatient_2024.csv', dtype=str)

med.columns = [
    'CCN',
    'PROVIDER_NAME',
    'CITY',
    'ADDRESS',
    'STATE_FIPS',
    'ZIP',
    'STATE',
    'RUCA',
    'RUCA_DESC',
    'DRG_CODE',
    'DRG_DESC',
    'TOTAL_DISCHARGES',
    'AVG_COVERED_CHARGES',
    'AVG_TOTAL_PAYMENT',
    'AVG_MEDICARE_PAYMENT'
]

med = med.where(pd.notnull(med), None)

success, nchunks, nrows, _ = write_pandas(
    conn=conn,
    df=med,
    table_name='MEDICARE_INPATIENT_VOLUME',
    database='BRG_PROVIDER_ANALYTICS',
    schema='RAW',
    overwrite=True
)
print(f"Medicare Inpatient Volume: {nrows} rows loaded")

# ── VERIFY ──
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM BRG_PROVIDER_ANALYTICS.RAW.HOSPITAL_GENERAL_INFO")
print(f"Hospital General Info row count: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM BRG_PROVIDER_ANALYTICS.RAW.MEDICARE_INPATIENT_VOLUME")
print(f"Medicare Inpatient Volume row count: {cursor.fetchone()[0]}")

cursor.execute("""
    SELECT COUNT(*) 
    FROM BRG_PROVIDER_ANALYTICS.RAW.MEDICARE_INPATIENT_VOLUME 
    WHERE STATE = 'VA'
""")
print(f"Virginia rows: {cursor.fetchone()[0]}")

cursor.close()
conn.close()
print("Done")
