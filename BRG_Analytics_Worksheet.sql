-- ============================================================
-- BRG PROVIDER ANALYTICS HUB — SNOWFLAKE WORKSHEET
-- Author: BRG Summer Associate (Shanjhitha Kannan)
-- Purpose: Build a proof-of-concept Provider Analytics Hub
--          demonstrating healthcare market share analytics
--          using real CMS Medicare data
--
-- HOW TO READ THIS FILE:
--   Every concept is explained before it appears.
--   Look for "CONCEPT EXPLAINER" sections to understand
--   the SQL technique being used, then see it applied below.
-- ============================================================


-- ============================================================
--                    DATABASE SETUP
-- ============================================================

-- One database holds all three layers of the pipeline
-- Keeps the project self-contained and separate from company data
CREATE DATABASE IF NOT EXISTS BRG_PROVIDER_ANALYTICS;

-- 3 Layers (Bronze → Silver → Gold pattern)
--   RAW       = data exactly as received from source, never modified
--   CLEAN     = standardized, validated, analytics-ready
--   ANALYTICS = aggregated views and KPIs for the dashboard
CREATE SCHEMA IF NOT EXISTS BRG_PROVIDER_ANALYTICS.RAW;
CREATE SCHEMA IF NOT EXISTS BRG_PROVIDER_ANALYTICS.CLEAN;
CREATE SCHEMA IF NOT EXISTS BRG_PROVIDER_ANALYTICS.ANALYTICS;

-- Verify everything was created
SHOW SCHEMAS IN DATABASE BRG_PROVIDER_ANALYTICS;


-- ============================================================
-- MOCK DATA EXPLORATION (kept for reference, not for analysis)
-- ============================================================
-- This table was created during early prototype phase using mock data.
-- Replaced by real CMS datasets.
-- Kept to show iteration process — real analysts keep their work history.

CREATE TABLE IF NOT EXISTS BRG_PROVIDER_ANALYTICS.RAW.PROVIDER_VOLUME_RAW (
    source_provider_name    VARCHAR,
    source_health_system    VARCHAR,
    source_geograoghy       VARCHAR,    -- typo caught and fixed below
    source_service_line     VARCHAR,
    source_market           VARCHAR,
    source_period           VARCHAR,
    source_volume           VARCHAR,    -- stored as VARCHAR in raw layer intentionally
                                        -- raw layer preserves original format including
                                        -- comma-formatted numbers like "1,247"
                                        -- type casting happens in the clean layer
    payer_type              VARCHAR,
    data_source             VARCHAR,
    source_file             VARCHAR,
    load_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

DESCRIBE TABLE BRG_PROVIDER_ANALYTICS.RAW.PROVIDER_VOLUME_RAW;

-- Fix typo discovered after table creation
-- Lesson: always verify column names before loading data
ALTER TABLE BRG_PROVIDER_ANALYTICS.RAW.PROVIDER_VOLUME_RAW
RENAME COLUMN source_geograoghy TO source_geography;

-- TRUNCATE removes all rows but keeps the table structure intact
-- DROP would remove the entire table — not what we want here
TRUNCATE TABLE BRG_PROVIDER_ANALYTICS.RAW.PROVIDER_VOLUME_RAW;

-- Spot check: confirm data loaded correctly
SELECT
    SOURCE_PROVIDER_NAME,
    SOURCE_SERVICE_LINE,
    SOURCE_PERIOD,
    SOURCE_VOLUME
FROM BRG_PROVIDER_ANALYTICS.RAW.PROVIDER_VOLUME_RAW
LIMIT 20;

-- Profile distinct provider names to see data quality issues
-- In real healthcare data, one hospital system appears under
-- dozens of different spellings — this query surfaces that problem
SELECT
    SOURCE_PROVIDER_NAME,
    COUNT(*) AS row_count
FROM BRG_PROVIDER_ANALYTICS.RAW.PROVIDER_VOLUME_RAW
GROUP BY SOURCE_PROVIDER_NAME
ORDER BY row_count DESC;

-----------------------------------------------------------------------
-- Ignore Everything Above (NOT Delete — kept to show iteration process)
-- Decision: switched from mock data to real CMS public datasets
-- Reason: real data enables real joins, real market share, real insights
-- Mock data was useful for learning architecture — not for presentation
-----------------------------------------------------------------------


-- ============================================================
--                    REAL CMS DATASETS
-- ============================================================

-- DATA: Hospital General Information
-- ABOUT: List of all Medicare-registered hospitals with addresses,
--        phone numbers, hospital type, and overall CMS star rating
-- SOURCE: https://data.cms.gov/provider-data/dataset/xubh-q36u
-- ROLE IN PIPELINE: Reference/dimension table
--                   Provides hospital context joined to volume data using CCN
CREATE TABLE IF NOT EXISTS BRG_PROVIDER_ANALYTICS.RAW.HOSPITAL_GENERAL_INFO (
    FACILITY_ID        VARCHAR,   -- CCN: CMS Certification Number, unique hospital ID
                                  -- this is the JOIN KEY connecting all datasets
    FACILITY_NAME      VARCHAR,   -- official hospital name as registered with CMS
    ADDRESS            VARCHAR,   -- street address
    CITY               VARCHAR,   -- city name
    STATE              VARCHAR,   -- 2-letter state abbreviation (VA, TX, CA etc)
    ZIP_CODE           VARCHAR,   -- kept as VARCHAR to preserve leading zeros
    COUNTY             VARCHAR,   -- useful for sub-state market analysis
    PHONE              VARCHAR,   -- operational data, not used in analytics
    HOSPITAL_TYPE      VARCHAR,   -- acute care, critical access, psychiatric etc
                                  -- critical for fair market share comparison
                                  -- cannot compare 500-bed academic center
                                  -- to 25-bed critical access hospital directly
    HOSPITAL_OWNERSHIP VARCHAR,   -- government, non-profit, proprietary
    EMERGENCY_SERVICES VARCHAR,   -- yes/no flag
    OVERALL_RATING     VARCHAR,   -- CMS star rating 1-5
                                  -- quality signal used in pursuit analytics
                                  -- high volume + low rating = consulting opportunity
    LOAD_TIMESTAMP     TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- DATA: Medicare Inpatient Hospitals by Provider and Service (2024)
-- ABOUT: Medicare Part A inpatient discharges aggregated by hospital and DRG
-- SOURCE: https://data.cms.gov/provider-summary-by-type-of-service/
--         medicare-inpatient-hospitals/medicare-inpatient-hospitals-by-provider-and-service
-- SCOPE: Medicare fee-for-service only
--        Does NOT include Medicaid, commercial insurance, or Medicare Advantage
-- ROLE IN PIPELINE: Primary fact table source
--                   Contains the volume and payment metrics that drive
--                   all market share calculations
CREATE TABLE IF NOT EXISTS BRG_PROVIDER_ANALYTICS.RAW.MEDICARE_INPATIENT_VOLUME (
    CCN                VARCHAR,   -- CMS Certification Number: primary join key
                                  -- connects this table to HOSPITAL_GENERAL_INFO
    PROVIDER_NAME      VARCHAR,   -- hospital name as it appears in Medicare billing
    CITY               VARCHAR,   -- city from Medicare billing records
    ADDRESS            VARCHAR,   -- street address
    STATE_FIPS         VARCHAR,   -- numeric state code (01=AL, 51=VA etc)
    ZIP                VARCHAR,   -- zip code
    STATE              VARCHAR,   -- 2-letter state abbreviation
    RUCA               VARCHAR,   -- Rural-Urban Commuting Area code
    RUCA_DESC          VARCHAR,   -- description of rural/urban classification
    DRG_CODE           VARCHAR,   -- Diagnosis Related Group code
                                  -- one row per hospital per DRG code
                                  -- a hospital with 400 DRGs = 400 rows
    DRG_DESC           VARCHAR,   -- human readable DRG description
    TOTAL_DISCHARGES   FLOAT,     -- CORE METRIC: drives all market share calculations
    AVG_COVERED_CHARGES FLOAT,    -- what the hospital billed Medicare on average
    AVG_TOTAL_PAYMENT  FLOAT,     -- what Medicare actually paid per discharge
    AVG_MEDICARE_PAYMENT FLOAT,   -- Medicare portion of total payment
    LOAD_TIMESTAMP     TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- DATA: DRG to MDC Crosswalk (CMS Official Grouping)
-- SOURCE: CMS MS-DRG Definitions Manual FY2024, via NBER public repository
-- WHY A THIRD TABLE?
--   Medicare data has 500+ granular DRG procedure codes
--   Too detailed for a director dashboard
--   CMS officially groups every DRG into 25 Major Diagnostic Categories (MDCs)
--   which map cleanly to service lines (MDC 05 = Cardiology, MDC 08 = Orthopedics)
--   Joining this crosswalk replaces 500 manual mappings with 25 CASE WHEN statements
--   This is the same methodology used by real healthcare analytics firms
CREATE TABLE IF NOT EXISTS BRG_PROVIDER_ANALYTICS.RAW.HEALTH_SYSTEM_REFERENCE (
    KEYWORD        VARCHAR,  -- pattern to match against hospital name (stored UPPERCASE)
    HEALTH_SYSTEM  VARCHAR   -- canonical system name to assign when keyword matches
);


-- ============================================================
-- KEY DEFINITIONS TO REMEMBER
-- ============================================================
--
-- CCN (CMS Certification Number):
--   Unique identifier assigned by CMS to every Medicare/Medicaid
--   certified provider. The universal join key across all CMS datasets.
--   Think of it as a hospital's Social Security Number.
--
-- DRG (Diagnosis Related Group):
--   Billing classification that groups inpatients with similar
--   diagnoses and resource requirements. Medicare pays a fixed
--   rate per DRG regardless of actual cost. 500+ DRGs exist.
--
-- MDC (Major Diagnostic Category):
--   CMS groups all DRGs into 25 MDCs by organ system.
--   MDC 05 = Circulatory, MDC 08 = Musculoskeletal.
--   We map MDCs to service lines for the dashboard.
--
-- Market Share Formula:
--   Market Share % = (Provider Discharges / Total Market Discharges) x 100
--   Numerator   = one provider's discharges in one state + service line
--   Denominator = ALL providers' discharges in same state + service line


-- ============================================================
-- EXPLORATION QUERIES
-- (used during development to understand data before building)
-- ============================================================

-- JOINING TWO DATASETS BY CCN
-- Purpose: verify the join works and understand available columns
--
-- WHY LEFT JOIN AND NOT INNER JOIN?
--   LEFT JOIN = keep ALL rows from the LEFT table
--               bring matching columns from RIGHT table where found
--               where no match exists, RIGHT table columns show NULL
--
--   INNER JOIN = only keep rows that exist in BOTH tables
--                if one hospital has no match in General Info
--                that hospital DISAPPEARS from results entirely
--                its discharges vanish from the denominator
--                market share percentages become WRONG silently
--
--   PSEUDOCODE:
--   for every hospital in Medicare volume (LEFT table):
--       look for a matching record in Hospital General Info (RIGHT table)
--       if found   → bring along city, hospital type, rating
--       if missing → keep the hospital row, set those columns to NULL
--       never drop any row from the LEFT table
--
--   Rule: LEFT table = data you cannot afford to lose
--         RIGHT table = context you are adding to enrich it
--         When in doubt → LEFT JOIN

SELECT
    m.CCN,               -- JOIN KEY: unique hospital identifier (CCN)
                         -- m. prefix = column comes from Medicare table (alias m)
    m.PROVIDER_NAME,     -- hospital name from Medicare billing
    m.DRG_CODE,          -- procedure group code — joined to MDC crosswalk later
    m.DRG_DESC,          -- human-readable procedure description
    m.TOTAL_DISCHARGES,  -- CORE METRIC: volume drives market share calculations
    m.AVG_TOTAL_PAYMENT, -- what Medicare paid — used for competitor cost comparisons
    h.CITY,              -- from Hospital General Info (alias h)
                         -- more reliable city name than Medicare file
    h.STATE,             -- readable state abbreviation vs numeric FIPS in Medicare
    h.HOSPITAL_TYPE,     -- academic vs community vs critical access
                         -- essential context for fair market comparison
    h.OVERALL_RATING     -- CMS star rating 1-5
                         -- quality lens for pursuit analytics
FROM BRG_PROVIDER_ANALYTICS.RAW.MEDICARE_INPATIENT_VOLUME m   -- LEFT TABLE (primary data)
LEFT JOIN BRG_PROVIDER_ANALYTICS.RAW.HOSPITAL_GENERAL_INFO h  -- RIGHT TABLE (enrichment)
    ON m.CCN = h.FACILITY_ID   -- join condition: CCN = FACILITY_ID
                               -- both contain the same CMS Certification Number
                               -- just named differently across the two datasets
-- WHERE h.STATE = 'VA'
--   AND m.PROVIDER_NAME LIKE '%Inova%'
-- WHERE filters removed after exploration phase
-- full national dataset enables multi-state dashboard selection
ORDER BY m.TOTAL_DISCHARGES DESC
LIMIT 20;

-- Explore DRG codes to understand procedure-level granularity
-- Confirms we need the MDC crosswalk to roll up to service lines
SELECT DISTINCT
    DRG_CODE,
    DRG_DESC
FROM BRG_PROVIDER_ANALYTICS.RAW.MEDICARE_INPATIENT_VOLUME
-- WHERE STATE = 'VA' -- removed: national view
ORDER BY DRG_CODE
LIMIT 50;

-- Confirm MDC values in the crosswalk table
-- MDC codes are 2-digit strings (01, 02 ... 25, PRE)
-- NOT prefixed with "MDC " — critical for CASE WHEN matching
SELECT DISTINCT MDC
FROM BRG_PROVIDER_ANALYTICS.RAW.DRG_MDC_CROSSWALK
LIMIT 5;


-- ============================================================
-- CONCEPT EXPLAINER: WHAT IS A CTE?
-- ============================================================
-- CTE = Common Table Expression
-- A temporary named table that only exists for one query
-- You build it, name it, use it, and it disappears
--
-- SYNTAX:
--   WITH my_temp_table AS (
--       SELECT ...
--   )
--   SELECT * FROM my_temp_table;
--
-- WHY USE CTEs INSTEAD OF SUBQUERIES?
--   Without CTE (hard to read):
--     SELECT * FROM (SELECT col1, SUM(col2) FROM table GROUP BY col1) AS sub
--     WHERE sub.col1 = 'VA'
--
--   With CTE (reads like a story):
--     WITH state_totals AS (
--         SELECT col1, SUM(col2) AS total FROM table GROUP BY col1
--     )
--     SELECT * FROM state_totals WHERE col1 = 'VA'
--
-- PSEUDOCODE FOR HOW CTEs WORK:
--   Step 1: Run the code inside WITH block, store result as named table
--   Step 2: Use that named table in the main SELECT below
--   Step 3: Temporary table disappears after query finishes
--
-- WHY WE USE MULTIPLE CTEs HERE:
--   CTE 1 → maps DRG codes to service lines (the clinical translation)
--   CTE 2 → maps hospitals to health systems (the business grouping)
--   Final SELECT → joins everything together into one clean fact table
--   Each CTE does ONE job. Together they tell the full story.
-- ============================================================


-- ============================================================
-- CONCEPT EXPLAINER: WHAT IS LPAD?
-- ============================================================
-- LPAD = Left Pad
-- Adds characters to the LEFT of a string until it reaches a target length
--
-- SYNTAX: LPAD(value, target_length, padding_character)
--
-- EXAMPLE:
--   LPAD('3',   3, '0') → '003'
--   LPAD('47',  3, '0') → '047'
--   LPAD('291', 3, '0') → '291'  (already 3 chars, no padding needed)
--
-- WHY WE NEED IT HERE:
--   Medicare volume table stores DRG codes as: '3', '47', '291'
--   MDC crosswalk table stores DRG codes as:   '003', '047', '291'
--   These look different so the JOIN would FAIL to match them
--
--   PSEUDOCODE:
--   for every DRG code in Medicare table:
--       if length < 3, add zeros on the left until length = 3
--   now both tables have the same format → JOIN works correctly
--
-- THE FIX:
--   ON LPAD(m.DRG_CODE, 3, '0') = LPAD(sl.MS_DRG, 3, '0')
--   Apply LPAD to BOTH sides so format is guaranteed to match
-- ============================================================


-- ============================================================
-- CONCEPT EXPLAINER: WHAT IS A WINDOW FUNCTION?
-- ============================================================
-- A window function calculates a value ACROSS a set of rows
-- WITHOUT collapsing those rows (unlike GROUP BY)
--
-- THE KEY DIFFERENCE:
--   GROUP BY collapses rows:        Window function keeps all rows:
--   ─────────────────────────       ────────────────────────────────
--   State  | Total                  State | System    | Share | Rank
--   VA     | 4,733,796              VA    | Sentara   | 18.1% | 1
--   TX     | 8,201,445              VA    | Inova     | 17.2% | 2
--                                   VA    | HCA       | 13.3% | 3
--   (2 rows, detail lost)           (all rows kept, rank added)
--
-- SYNTAX:
--   RANK() OVER (
--       PARTITION BY column1   ← restart ranking for each group
--       ORDER BY column2 DESC  ← rank by this column
--   )
--
-- PSEUDOCODE FOR RANK():
--   for each unique combination of PARTITION BY columns:
--       sort the rows by ORDER BY column
--       assign rank 1 to highest, 2 to next, and so on
--       start over at rank 1 for the next partition
--
-- OUR EXAMPLE:
--   RANK() OVER (
--       PARTITION BY h.state, h.service_line   ← separate ranking per market
--       ORDER BY h.system_discharges DESC      ← #1 = most discharges
--   )
--
--   VA + Cardiology gets its own ranking (Sentara #1, Inova #2...)
--   TX + Cardiology gets its own separate ranking
--   VA + Orthopedics gets its own separate ranking
--   Each market segment ranked independently
--
-- WHY NOT JUST USE ORDER BY?
--   ORDER BY sorts rows but gives no number
--   RANK() gives each row an actual rank number we can filter on
--   e.g. WHERE market_rank = 1 → find the leader in every market
-- ============================================================


-- ============================================================
-- CONCEPT EXPLAINER: WHAT IS COALESCE?
-- ============================================================
-- COALESCE returns the first non-NULL value from a list
--
-- SYNTAX: COALESCE(value1, value2, value3, ...)
--
-- EXAMPLE:
--   COALESCE('Inova Health System', 'Independent / Other') → 'Inova Health System'
--   COALESCE(NULL,                  'Independent / Other') → 'Independent / Other'
--
-- WHY WE NEED IT HERE:
--   When a hospital name does NOT match any keyword in reference table
--   the JOIN returns NULL for the health_system column
--   NULL values break filters, aggregations, and dashboard displays
--
--   PSEUDOCODE:
--   if r.health_system has a value → use that value
--   if r.health_system is NULL    → use 'Independent / Other' instead
--   never let NULL reach the dashboard
-- ============================================================


-- ============================================================
-- CONCEPT EXPLAINER: WHAT IS CAST?
-- ============================================================
-- CAST converts a value from one data type to another
--
-- SYNTAX: CAST(column AS new_type)
--
-- WHY WE NEED IT HERE:
--   Raw layer stores TOTAL_DISCHARGES as VARCHAR (text)
--   Reason: raw layer preserves data exactly as received
--   Some source values had commas: "1,247" or text: "N/A"
--   Storing as VARCHAR prevents load errors
--
--   But we CANNOT do math on text:
--   '1247' + '500' = '1247500'  (string concatenation, WRONG)
--   1247  +  500  = 1747        (numeric addition, CORRECT)
--
--   CAST(TOTAL_DISCHARGES AS FLOAT) converts text to number
--   Now SUM(), AVG(), and division all work correctly
--
-- PSEUDOCODE:
--   take the text value '1247'
--   convert it to the number 1247
--   now math operations work as expected
-- ============================================================


-- ============================================================
--                        CLEAN LAYER
-- Purpose: Join all three source tables, apply service line
--          mapping, and create the analytics-ready fact table
-- Output:  CLEAN.FACT_PROVIDER_SERVICE_LINE_VOLUME
--          One row per hospital per DRG code
--          With service line, health system, and payment columns
-- ============================================================

CREATE OR REPLACE TABLE BRG_PROVIDER_ANALYTICS.CLEAN.FACT_PROVIDER_SERVICE_LINE_VOLUME AS


-- ── CTE 1: MDC TO SERVICE LINE MAPPING ───────────────────────
-- WHAT IT DOES:
--   Reads every row in the DRG crosswalk table
--   Assigns a business-friendly service line name to each MDC code
--   Result: a temporary table with DRG code + service line name
--
-- PSEUDOCODE:
--   for every DRG in the crosswalk table:
--       look at its MDC code
--       if MDC = '05' → label it 'Cardiology'
--       if MDC = '08' → label it 'Orthopedics'
--       ... and so on for all 25 MDCs
--       store DRG code + service line as a named temporary table
--   later: join this table to Medicare volume using DRG code

WITH mdc_to_service_line AS (
    SELECT
        ms_drg,       -- DRG code: will be used as join key to Medicare volume table
        mdc,          -- Major Diagnostic Category code (01-25, PRE)
        msdrg_title,  -- full DRG title: kept for audit trail in final table

        CASE
            -- CASE WHEN works like an if/else statement
            -- Snowflake checks each WHEN condition top to bottom
            -- Returns the THEN value for the first matching condition
            -- ELSE handles anything that did not match any condition

            -- ── NEUROLOGICAL ──────────────────────────────────
            WHEN mdc = '01' THEN 'Neurology'
                -- Nervous system diseases and disorders

            -- ── SENSORY ───────────────────────────────────────
            WHEN mdc = '02' THEN 'Ophthalmology'
                -- Eye diseases and disorders
            WHEN mdc = '03' THEN 'ENT'
                -- Ear, nose, mouth, throat

            -- ── RESPIRATORY ───────────────────────────────────
            WHEN mdc = '04' THEN 'Pulmonology'
                -- Respiratory system diseases

            -- ── CARDIOVASCULAR ────────────────────────────────
            WHEN mdc = '05' THEN 'Cardiology'
                -- Circulatory system diseases

            -- ── DIGESTIVE ─────────────────────────────────────
            WHEN mdc = '06' THEN 'Gastroenterology'
                -- Digestive system diseases
            WHEN mdc = '07' THEN 'Gastroenterology'
                -- Hepatobiliary system (liver, gallbladder) and pancreas
                -- grouped with GI: same clinical service line

            -- ── MUSCULOSKELETAL ───────────────────────────────
            WHEN mdc = '08' THEN 'Orthopedics'
                -- Musculoskeletal and connective tissue

            -- ── SKIN ──────────────────────────────────────────
            WHEN mdc = '09' THEN 'Dermatology'
                -- Skin, subcutaneous tissue, breast

            -- ── ENDOCRINE / METABOLIC ─────────────────────────
            WHEN mdc = '10' THEN 'Endocrinology'
                -- Endocrine, nutritional, metabolic diseases

            -- ── UROLOGICAL ────────────────────────────────────
            WHEN mdc = '11' THEN 'Urology'
                -- Kidney and urinary tract
            WHEN mdc = '12' THEN 'Urology'
                -- Male reproductive system
                -- grouped with Urology: same clinical service line

            -- ── WOMEN'S HEALTH ────────────────────────────────
            WHEN mdc = '13' THEN 'Womens Health'
                -- Female reproductive system diseases
            WHEN mdc = '14' THEN 'Womens Health'
                -- Pregnancy, childbirth, postpartum care
            WHEN mdc = '15' THEN 'Womens Health'
                -- Newborns and neonates: attributed to Womens Health
                -- because neonatal volume follows OB program growth
                -- a hospital growing Women's Health grows NICU simultaneously

            -- ── HEMATOLOGY ────────────────────────────────────
            WHEN mdc = '16' THEN 'Hematology'
                -- Blood and blood-forming organ diseases

            -- ── ONCOLOGY ──────────────────────────────────────
            WHEN mdc = '17' THEN 'Oncology'
                -- Neoplasms: tumors and cancer diagnoses

            -- ── INFECTIOUS DISEASE ────────────────────────────
            WHEN mdc = '18' THEN 'Infectious Disease'
                -- Infectious and parasitic diseases
                -- includes sepsis which drives high inpatient volume

            -- ── BEHAVIORAL HEALTH ─────────────────────────────
            WHEN mdc = '19' THEN 'Behavioral Health'
                -- Mental diseases and disorders
            WHEN mdc = '20' THEN 'Behavioral Health'
                -- Alcohol and drug use disorders
                -- grouped together: same strategic service line

            -- ── TRAUMA ────────────────────────────────────────
            WHEN mdc = '21' THEN 'Trauma'
                -- Injuries, poisoning, toxic effects
            WHEN mdc = '22' THEN 'Trauma'
                -- Burns
            WHEN mdc = '25' THEN 'Trauma'
                -- Multiple significant trauma

            -- ── RENAL ─────────────────────────────────────────
            WHEN mdc = '23' THEN 'Renal'
                -- Factors influencing health status
                -- primarily renal and dialysis-related

            -- ── HIV ───────────────────────────────────────────
            WHEN mdc = '24' THEN 'HIV'
                -- HIV infections

            -- ── COMPLEX / HIGH ACUITY ─────────────────────────
            WHEN mdc = 'PRE' THEN 'Complex/Surgical'
                -- Pre-MDC: highest complexity cases
                -- transplants, ECMO, long-term ventilation
                -- assigned before standard MDC grouping

            -- ── UNMATCHED ─────────────────────────────────────
            ELSE 'Other'
                -- DRGs not matched above should be near zero
                -- if significant volume lands here, review crosswalk

        END AS service_line

    FROM BRG_PROVIDER_ANALYTICS.RAW.DRG_MDC_CROSSWALK
),

-- ── CTE 2: HEALTH SYSTEM CONSOLIDATION ───────────────────────
-- WHAT IT DOES:
--   Medicare data has one row per individual hospital
--   e.g. Inova Fairfax, Inova Loudoun, Inova Alexandria = 3 separate rows
--   This CTE groups individual hospitals under their parent health system
--   so market share reflects the full system competitive footprint
--
-- PSEUDOCODE:
--   for every hospital in Medicare volume table:
--       convert hospital name to UPPERCASE (case-insensitive matching)
--       check if name CONTAINS any keyword from reference table
--       if keyword found  → assign that keyword's health_system value
--       if no keyword found → r.health_system will be NULL
--       COALESCE converts NULL → 'Independent / Other'
--       always keep the hospital row (LEFT JOIN)
--
-- METHOD: Reference table JOIN (professional approach)
--   instead of hardcoding 200 lines of CASE WHEN:
--     add new system = just insert one row into reference table
--     no SQL changes needed ever
--
-- LIMITATION: keyword matching may miss some affiliations
--   Production solution: direct CCN-to-health-system crosswalk
--   from vendors like Definitive Healthcare (BRG likely licenses this)
--   or the free CMS Provider of Services file
--   Keyword matching is appropriate for this proof-of-concept

health_system_mapping AS (
    SELECT
        m.ccn,            -- hospital identifier: used as join key
        m.provider_name,  -- individual hospital name from Medicare billing
        m.state,          -- state: needed to partition market share by geography
        COALESCE(r.health_system, 'Independent / Other') AS health_system
        -- COALESCE: if no keyword match found, r.health_system = NULL
        --           COALESCE converts NULL → 'Independent / Other'
        --           prevents NULL from reaching dashboard and breaking aggregations

    FROM BRG_PROVIDER_ANALYTICS.RAW.MEDICARE_INPATIENT_VOLUME m  -- LEFT TABLE
    LEFT JOIN BRG_PROVIDER_ANALYTICS.RAW.HEALTH_SYSTEM_REFERENCE r  -- RIGHT TABLE
        ON UPPER(m.provider_name) LIKE '%' || r.KEYWORD || '%'
        -- HOW THIS JOIN CONDITION WORKS:
        --   UPPER(m.provider_name) → converts 'Inova Fairfax Hospital' to
        --                            'INOVA FAIRFAX HOSPITAL' (case safety)
        --   '%' || r.KEYWORD || '%' → builds a LIKE pattern dynamically:
        --                             '%' + 'INOVA' + '%' = '%INOVA%'
        --                             '%' means "any characters here"
        --   So: 'INOVA FAIRFAX HOSPITAL' LIKE '%INOVA%' = TRUE → match found
        --   The JOIN checks every hospital against every keyword automatically
),


-- ── FINAL SELECT: JOIN ALL THREE TABLES ──────────────────────
-- WHAT IT DOES:
--   Brings together all data sources into one clean fact table
--   Medicare volume (volumes + payments)
--   + MDC crosswalk via CTE 1 (service line names)
--   + Hospital General Info (city, type, rating)
--   + Health system mapping via CTE 2 (parent system name)
--
-- PSEUDOCODE:
--   start with every row in Medicare volume table
--   for each row:
--       look up service line from CTE 1 using DRG code (LPAD for format match)
--       look up city/type/rating from Hospital General Info using CCN
--       look up health system name from CTE 2 using CCN
--       combine all columns into one output row
--   result: one row per hospital per DRG with all analytical dimensions

SELECT
    m.CCN,
    m.PROVIDER_NAME                           AS hospital_name,
    h.health_system,        -- from CTE 2: parent health system name
    h.STATE                 AS state,          -- market geography dimension
    hgi.CITY                AS city,           -- from Hospital General Info
    hgi.HOSPITAL_TYPE       AS hospital_type,  -- from Hospital General Info
    hgi.OVERALL_RATING      AS overall_rating, -- CMS star rating 1-5
    sl.service_line,        -- from CTE 1: business-friendly service line name
    sl.mdc,                 -- MDC code: kept for audit trail
    sl.msdrg_title          AS drg_description,-- full DRG title for reference
    m.DRG_CODE,             -- original DRG code: kept for traceability

    CAST(m.TOTAL_DISCHARGES AS FLOAT)      AS total_discharges,
    -- CAST: converts text '1247' to number 1247
    -- required so SUM() and division work correctly in market share calculations

    CAST(m.AVG_TOTAL_PAYMENT AS FLOAT)     AS avg_total_payment,
    CAST(m.AVG_MEDICARE_PAYMENT AS FLOAT)  AS avg_medicare_payment,
    CAST(m.AVG_COVERED_CHARGES AS FLOAT)   AS avg_covered_charges,

    CURRENT_TIMESTAMP()                    AS load_timestamp
    -- audit field: records exactly when this clean table was built
    -- if numbers are questioned later, load_timestamp proves when data was current

FROM BRG_PROVIDER_ANALYTICS.RAW.MEDICARE_INPATIENT_VOLUME m
LEFT JOIN mdc_to_service_line sl
    -- join Medicare volume to MDC crosswalk on DRG code
    -- LPAD: pads DRG codes to 3 digits for consistent format matching
    -- Medicare has '3', crosswalk has '003' → LPAD makes both '003' → match works
    ON LPAD(m.DRG_CODE, 3, '0') = LPAD(sl.MS_DRG, 3, '0')

LEFT JOIN BRG_PROVIDER_ANALYTICS.RAW.HOSPITAL_GENERAL_INFO hgi
    -- join to get city, hospital type, and CMS star rating
    -- LEFT JOIN: keeps hospitals even if no match in General Info
    ON m.CCN = hgi.FACILITY_ID

LEFT JOIN health_system_mapping h
    -- join to get parent health system name from CTE 2
    -- LEFT JOIN: keeps all hospitals including independents
    ON m.CCN = h.CCN;
-- WHERE m.STATE = 'VA' -- removed: full national dataset loaded
--                         state filtering happens in dashboard sidebar dropdown
--                         this enables the proof-of-concept to work for any market


-- ── VERIFY CLEAN TABLE ───────────────────────────────────────
-- Spot check: confirm service lines and health systems loaded correctly
SELECT
    health_system,
    service_line,
    SUM(total_discharges) AS total_discharges
FROM BRG_PROVIDER_ANALYTICS.CLEAN.FACT_PROVIDER_SERVICE_LINE_VOLUME
GROUP BY health_system, service_line
ORDER BY health_system, total_discharges DESC;


-- ============================================================
--                      ANALYTICS LAYER
-- Purpose: Calculate market share percentages and competitive
--          rankings from the clean fact table
-- Output:  VW_MARKET_SHARE (a VIEW, not a table)
--
-- WHAT IS A VIEW?
--   A view is a saved SQL query, not stored data
--   Every time the dashboard queries VW_MARKET_SHARE,
--   Snowflake runs this SQL fresh against the clean table
--   If the clean table is updated, the view automatically
--   reflects the new data — no manual refresh needed
-- ============================================================

CREATE OR REPLACE VIEW BRG_PROVIDER_ANALYTICS.ANALYTICS.VW_MARKET_SHARE AS


-- ── CTE 3: MARKET DENOMINATOR ────────────────────────────────
-- WHAT IT DOES:
--   Calculates the total Medicare discharges for every
--   state + service line combination across ALL providers
--   This becomes the DENOMINATOR in the market share formula:
--   Market Share % = Provider Discharges / Total Market Discharges x 100
--
-- WHY WE NEED THIS AS A SEPARATE CTE:
--   We cannot calculate market share in one step
--   We first need the total BEFORE we can calculate each provider's percentage
--   This CTE produces the total; the next CTE produces each provider's slice
--
-- PSEUDOCODE:
--   for every unique state + service line combination:
--       add up ALL discharges from ALL providers in that market segment
--       store as total_market_discharges
--   result: one row per state + service line with the market total

WITH service_line_totals AS (
    SELECT
        state,
        service_line,
        SUM(total_discharges) AS total_market_discharges
        -- SUM across ALL providers (including independents)
        -- because independent hospitals compete for the same patients
        -- leaving them out would make market share percentages add up to more than 100%
    FROM BRG_PROVIDER_ANALYTICS.CLEAN.FACT_PROVIDER_SERVICE_LINE_VOLUME
    WHERE service_line IS NOT NULL   -- exclude DRGs that had no MDC match
      AND service_line != 'Other'    -- exclude catch-all bucket
    GROUP BY state, service_line     -- one total per market segment
),


-- ── CTE 4: PROVIDER NUMERATOR ────────────────────────────────
-- WHAT IT DOES:
--   Calculates each health system's total discharges
--   grouped by state and service line
--   This becomes the NUMERATOR in the market share formula
--
-- PSEUDOCODE:
--   for every unique state + health_system + service_line combination:
--       add up discharges for that health system in that market segment
--       calculate average payment and average charges
--       count how many distinct hospitals contributed
--   result: one row per health system per market segment

health_system_totals AS (
    SELECT
        state,
        health_system,
        service_line,
        SUM(total_discharges)           AS system_discharges,
        -- NUMERATOR: this health system's total volume
        -- will be divided by total_market_discharges from CTE 3

        AVG(avg_total_payment)          AS avg_payment,
        -- average Medicare payment per discharge across all DRGs
        -- directors use this to compare payment efficiency between competitors

        AVG(avg_covered_charges)        AS avg_charges,
        -- average amount billed before Medicare adjustment
        -- large gap between charges and payment = potential revenue cycle opportunity

        COUNT(DISTINCT hospital_name)   AS hospital_count
        -- how many individual hospitals make up this system's volume
        -- strategic context: 20% share from 10 hospitals vs 2 hospitals
        -- tells very different stories about market penetration

    FROM BRG_PROVIDER_ANALYTICS.CLEAN.FACT_PROVIDER_SERVICE_LINE_VOLUME
    WHERE service_line IS NOT NULL
      AND service_line != 'Other'
      AND health_system != 'Independent / Other'
      -- exclude independents from system rankings
      -- they are counted in denominators but not ranked as named systems
    GROUP BY state, health_system, service_line
)


-- ── FINAL SELECT: CALCULATE MARKET SHARE ─────────────────────
-- WHAT IT DOES:
--   Joins the denominator (CTE 3) to the numerator (CTE 4)
--   Divides to get market share percentage
--   Adds competitive ranking using window function RANK()
--
-- PSEUDOCODE:
--   for every health system in every market segment:
--       find the matching market total from CTE 3
--       divide system discharges by market total
--       multiply by 100 to get percentage
--       rank all systems in that market from highest to lowest volume

SELECT
    h.state,
    h.health_system,
    h.service_line,
    h.system_discharges,            -- numerator (from CTE 4)
    t.total_market_discharges,      -- denominator (from CTE 3)

    ROUND(
        (h.system_discharges / t.total_market_discharges) * 100,
        2
    ) AS market_share_pct,
    -- THE CORE FORMULA:
    --   provider volume / total market volume x 100
    --   ROUND(..., 2) → keeps 2 decimal places: 18.11%
    --   without ROUND we get: 18.11349827364...  (too many decimals)

    h.avg_payment,
    h.avg_charges,
    h.hospital_count,

    RANK() OVER (
        -- WINDOW FUNCTION: assigns competitive rank per market segment
        -- does NOT collapse rows like GROUP BY would
        -- every health system keeps its own row AND gets a rank number
        PARTITION BY h.state, h.service_line
        -- PARTITION BY = restart ranking for each unique group
        -- VA + Cardiology ranked separately from TX + Cardiology
        -- VA + Orthopedics ranked separately from VA + Cardiology
        ORDER BY h.system_discharges DESC
        -- rank by volume: highest discharges = rank #1
    ) AS market_rank
    -- market_rank = 1 means this system leads that market segment
    -- market_rank = 5 means 4 other systems have higher volume

FROM health_system_totals h     -- health system data (numerator)
JOIN service_line_totals t      -- market total data (denominator)
    ON h.state = t.state
    AND h.service_line = t.service_line;
    -- JOIN CONDITION IS CRITICAL:
    --   must match on BOTH state AND service line
    --   ensures Inova's Cardiology volume divides by VA Cardiology total
    --   NOT by TX Cardiology total or VA Orthopedics total
    --   wrong join condition = wrong market share = wrong dashboard = wrong client advice


-- ── VERIFY MARKET SHARE VIEW ─────────────────────────────────
-- Spot check Virginia Cardiology to confirm rankings look correct
-- Expected: Sentara leads Inova by roughly 1 percentage point
SELECT *
FROM BRG_PROVIDER_ANALYTICS.ANALYTICS.VW_MARKET_SHARE
WHERE state = 'VA'
  AND service_line = 'Cardiology'
ORDER BY market_rank;
