"""
db.py — SQLite storage layer for the Amazon PPC CRM Dashboard.

Every upload gets appended (not overwritten) with a timestamp, so the
database builds up history automatically over time. This is what makes
"keyword tracking" and "trend" views possible — you just keep uploading
your weekly Cerebro / rank-tracker / STR exports and the dashboard
accumulates the history for you.
"""
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "ppc_crm.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Cerebro keyword research (one row per keyword per upload)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cerebro_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            niche TEXT,
            keyword_phrase TEXT,
            match_type TEXT,
            search_volume REAL,
            competing_products REAL,
            cpr REAL,
            title_density REAL,
            cerebro_iq_score REAL,
            organic_rank REAL,
            relevancy REAL,
            uploaded_at TEXT,
            source_file TEXT
        )
    """)

    # Keyword rank tracking over time (Helium10 rank tracker / weekly KWs tracker)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS keyword_rank_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            niche TEXT,
            asin TEXT,
            keyword TEXT,
            search_volume REAL,
            cpr REAL,
            competing_products TEXT,
            organic_rank REAL,
            sponsored_position TEXT,
            tracked_date TEXT,
            uploaded_at TEXT,
            source_file TEXT
        )
    """)

    # Market / niche analysis (competitor ASIN comparison)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            niche TEXT,
            asin TEXT,
            brand TEXT,
            price REAL,
            sales REAL,
            revenue REAL,
            uploaded_at TEXT,
            source_file TEXT
        )
    """)

    # Daily PPC tracker (ACOS / TACOS / spend / sales)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ppc_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            niche TEXT,
            date TEXT,
            ad_spend REAL,
            ad_spend_sales REAL,
            acos REAL,
            roas REAL,
            total_sales REAL,
            tacos REAL,
            profit REAL,
            sessions REAL,
            page_views REAL,
            total_units REAL,
            price REAL,
            uploaded_at TEXT,
            source_file TEXT
        )
    """)

    # Search term report (raw Amazon Ads export)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS search_term_report (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            niche TEXT,
            start_date TEXT,
            end_date TEXT,
            campaign_name TEXT,
            ad_group_name TEXT,
            targeting TEXT,
            match_type TEXT,
            impressions REAL,
            clicks REAL,
            ctr REAL,
            cpc REAL,
            spend REAL,
            acos REAL,
            roas REAL,
            sales REAL,
            orders REAL,
            units REAL,
            uploaded_at TEXT,
            source_file TEXT
        )
    """)

    # Profit calculator (per-ASIN cost breakdown)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS profit_calc (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asin TEXT,
            product_name TEXT,
            weekly_units REAL,
            revenue REAL,
            asp REAL,
            landed_cost REAL,
            referral_fee REAL,
            ppc_cost REAL,
            fba_fee REAL,
            storage_fee REAL,
            coupon_pct REAL,
            total_cost REAL,
            profit_per_unit REAL,
            profit_pct REAL,
            uploaded_at TEXT,
            source_file TEXT
        )
    """)

    conn.commit()
    conn.close()


def insert_df(table: str, df: pd.DataFrame, source_file: str):
    """Append a dataframe to a table, stamping uploaded_at and source_file."""
    if df.empty:
        return 0
    df = df.copy()
    df["uploaded_at"] = datetime.now().isoformat(timespec="seconds")
    df["source_file"] = source_file
    conn = get_conn()
    df.to_sql(table, conn, if_exists="append", index=False)
    conn.commit()
    conn.close()
    return len(df)


def read_table(table: str, niche: str = None) -> pd.DataFrame:
    conn = get_conn()
    if niche and niche != "All niches":
        df = pd.read_sql(f"SELECT * FROM {table} WHERE niche = ?", conn, params=(niche,))
    else:
        df = pd.read_sql(f"SELECT * FROM {table}", conn)
    conn.close()
    return df


def list_niches() -> list:
    conn = get_conn()
    niches = set()
    for t in ["cerebro_keywords", "keyword_rank_tracking", "market_analysis", "ppc_daily", "search_term_report"]:
        try:
            rows = conn.execute(f"SELECT DISTINCT niche FROM {t} WHERE niche IS NOT NULL AND niche != ''").fetchall()
            niches.update(r[0] for r in rows)
        except Exception:
            pass
    conn.close()
    return sorted(niches)


def row_counts() -> dict:
    conn = get_conn()
    tables = ["cerebro_keywords", "keyword_rank_tracking", "market_analysis",
              "ppc_daily", "search_term_report", "profit_calc"]
    counts = {}
    for t in tables:
        try:
            counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except Exception:
            counts[t] = 0
    conn.close()
    return counts
