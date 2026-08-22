"""
parsers.py — turns raw uploaded files (Helium10 Cerebro exports, rank
tracker exports, Amazon Search Term Reports, market analysis sheets,
PPC daily trackers) into clean dataframes matching our DB schema.

Column names in real-world exports vary slightly (extra spaces, case,
minor renames between Helium10 versions), so every parser matches
columns loosely (lowercased, stripped, partial match) instead of
requiring an exact header.
"""
import pandas as pd
import numpy as np
import re
import datetime as _dt


def _norm(col) -> str:
    return re.sub(r"\s+", " ", str(col).strip().lower())


def _find_col(columns, *candidates):
    """Find the first column whose normalized name contains any candidate substring."""
    norm_map = {_norm(c): c for c in columns}
    for cand in candidates:
        cand = _norm(cand)
        for norm_c, orig_c in norm_map.items():
            if cand == norm_c:
                return orig_c
        for norm_c, orig_c in norm_map.items():
            if cand in norm_c:
                return orig_c
    return None


def _col(df, name):
    """Safely get a single column as a Series even if the sheet has duplicate column names."""
    s = df[name]
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    return s


def _to_num(series):
    """Coerce a column to numeric, stripping $, %, commas, '>' and '-' placeholders."""
    def clean(v):
        if pd.isna(v):
            return np.nan
        if isinstance(v, (int, float)):
            return v
        s = str(v).strip()
        if s in ("", "-", "N/A", "#N/A", "n/a"):
            return np.nan
        s = s.replace(">", "").replace(",", "").replace("$", "").replace("%", "")
        try:
            return float(s)
        except ValueError:
            return np.nan
    return series.apply(clean)


def _fix_header(df: pd.DataFrame, key_terms=("date", "asin", "keyword", "targeting", "customer search term")) -> pd.DataFrame:
    """
    Real-world exports sometimes have a title row above the real header
    (e.g. 'SPONSORED PRODUCTS / SPONSORED BRANDS' merged-cell banner).
    If the current header row doesn't look like a real header (mostly
    'Unnamed: N' placeholders) but one of the first 5 data rows contains
    a recognizable key term (Date, ASIN, Keyword...), promote that row
    to be the header instead.
    """
    cols = [str(c) for c in df.columns]
    unnamed_ratio = sum(1 for c in cols if c.startswith("Unnamed") or c.strip() == "") / max(len(cols), 1)
    if unnamed_ratio < 0.5:
        return df  # header already looks fine

    for i in range(min(5, len(df))):
        row_vals = [_norm(v) for v in df.iloc[i].tolist()]
        if any(any(term in v for term in key_terms) for v in row_vals):
            new_header = df.iloc[i].tolist()
            new_df = df.iloc[i + 1:].reset_index(drop=True)
            new_df.columns = [str(h).strip() if pd.notna(h) else f"col_{j}" for j, h in enumerate(new_header)]
            return new_df
    return df


def read_any(file) -> dict:
    """Read an uploaded file (csv or xlsx) and return {sheet_name: dataframe}."""
    name = getattr(file, "name", str(file))
    if name.lower().endswith(".csv"):
        return {"Sheet1": pd.read_csv(file)}
    xls = pd.ExcelFile(file)
    return {sn: xls.parse(sn) for sn in xls.sheet_names}


# ---------------------------------------------------------------------
# CEREBRO / keyword-research exports
# Handles both the "Own ASINs Cerebro" wide format (one column per
# competitor ASIN) and the plain Cerebro export (Keyword Phrase,
# Cerebro IQ Score, Search Volume, Competing Products, CPR,
# Title Density, Organic Rank).
# ---------------------------------------------------------------------
def parse_cerebro(df: pd.DataFrame, niche: str) -> pd.DataFrame:
    cols = df.columns
    kw_col = _find_col(cols, "keyword phrase", "keyword")
    if kw_col is None:
        return pd.DataFrame()

    out = pd.DataFrame()
    out["keyword_phrase"] = _col(df, kw_col).astype(str).str.strip()
    match_col = _find_col(cols, "match type")
    out["match_type"] = _col(df, match_col) if match_col else None
    sv_col = _find_col(cols, "search volume")
    out["search_volume"] = _to_num(_col(df, sv_col)) if sv_col else np.nan
    cp_col = _find_col(cols, "competing products")
    out["competing_products"] = _to_num(_col(df, cp_col)) if cp_col else np.nan
    cpr_col = _find_col(cols, "cpr")
    out["cpr"] = _to_num(_col(df, cpr_col)) if cpr_col else np.nan
    td_col = _find_col(cols, "title density")
    out["title_density"] = _to_num(_col(df, td_col)) if td_col else np.nan
    iq_col = _find_col(cols, "cerebro iq score", "iq score")
    out["cerebro_iq_score"] = _to_num(_col(df, iq_col)) if iq_col else np.nan
    rank_col = _find_col(cols, "organic rank")
    out["organic_rank"] = _to_num(_col(df, rank_col)) if rank_col else np.nan
    rel_col = _find_col(cols, "relevancy")
    out["relevancy"] = _to_num(_col(df, rel_col)) if rel_col else np.nan

    out["niche"] = niche
    out = out.dropna(subset=["keyword_phrase"])
    out = out[out["keyword_phrase"].str.lower() != "nan"]
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------
# Helium10 rank-tracker export (ASIN, Keyword, Search Volume, CPR,
# Competing Products, Organic Rank, Sponsored Position, Marketplace)
# Also handles the wide "KWs Tracker" format with one column per
# tracked date, by melting it into long format.
# ---------------------------------------------------------------------
def parse_rank_tracker(df: pd.DataFrame, niche: str, tracked_date=None) -> pd.DataFrame:
    cols = df.columns
    kw_col = _find_col(cols, "keyword")
    asin_col = _find_col(cols, "asin")
    if kw_col is None:
        return pd.DataFrame()

    date_cols = [c for c in cols if isinstance(c, (pd.Timestamp, _dt.datetime, _dt.date)) or _is_dateish(c)]

    if date_cols:
        # Wide weekly-tracker format: melt one row-per-keyword-per-date
        id_cols = [c for c in [asin_col, kw_col,
                                _find_col(cols, "search volume"),
                                _find_col(cols, "cpr"),
                                _find_col(cols, "competing products")] if c]
        long_df = df.melt(id_vars=id_cols, value_vars=date_cols,
                           var_name="tracked_date", value_name="organic_rank")
        out = pd.DataFrame()
        out["asin"] = _col(long_df, asin_col) if asin_col else None
        out["keyword"] = _col(long_df, kw_col).astype(str).str.strip()
        sv_col = _find_col(cols, "search volume")
        out["search_volume"] = _to_num(_col(long_df, sv_col)) if sv_col else np.nan
        cpr_col = _find_col(cols, "cpr")
        out["cpr"] = _to_num(_col(long_df, cpr_col)) if cpr_col else np.nan
        cp_col = _find_col(cols, "competing products")
        out["competing_products"] = _col(long_df, cp_col).astype(str) if cp_col else None
        out["organic_rank"] = _to_num(_col(long_df, "organic_rank"))
        out["sponsored_position"] = None
        out["tracked_date"] = pd.to_datetime(_col(long_df, "tracked_date"), errors="coerce").astype(str)
    else:
        out = pd.DataFrame()
        out["asin"] = _col(df, asin_col) if asin_col else None
        out["keyword"] = _col(df, kw_col).astype(str).str.strip()
        sv_col = _find_col(cols, "search volume")
        out["search_volume"] = _to_num(_col(df, sv_col)) if sv_col else np.nan
        cpr_col = _find_col(cols, "cpr")
        out["cpr"] = _to_num(_col(df, cpr_col)) if cpr_col else np.nan
        cp_col = _find_col(cols, "competing products")
        out["competing_products"] = _col(df, cp_col).astype(str) if cp_col else None
        rank_col = _find_col(cols, "organic rank")
        out["organic_rank"] = _to_num(_col(df, rank_col)) if rank_col else np.nan
        sp_col = _find_col(cols, "sponsored position")
        out["sponsored_position"] = _col(df, sp_col).astype(str) if sp_col else None
        out["tracked_date"] = str(tracked_date) if tracked_date else pd.Timestamp.today().date().isoformat()

    out["niche"] = niche
    out = out.dropna(subset=["keyword"])
    out = out[out["keyword"].str.lower() != "nan"]
    return out.reset_index(drop=True)


def _is_dateish(col) -> bool:
    if isinstance(col, str):
        try:
            pd.to_datetime(col)
            return bool(re.search(r"\d{4}|\d{1,2}/\d{1,2}", col))
        except Exception:
            return False
    return False


# ---------------------------------------------------------------------
# Market / niche analysis (ASIN, Brand, Price, Sales, Revenue columns
# laid out across columns rather than rows — transposed sheet)
# ---------------------------------------------------------------------
def parse_market_analysis(df: pd.DataFrame, niche: str) -> pd.DataFrame:
    # These sheets are transposed: row 0/1 = ASIN, row label 'Brand', 'Price $', 'Sales', 'Revenue'
    # Use positional (.iloc) access throughout — these sheets often have
    # duplicate/blank column headers, which makes label-based access ambiguous.
    df = df.reset_index(drop=True)
    labels = df.iloc[:, 0].astype(str).str.strip().str.lower()

    def get_row_idx(label_substr):
        matches = labels[labels.str.contains(label_substr, na=False)]
        if matches.empty:
            return None
        return matches.index[0]

    asin_idx = get_row_idx("asin")
    if asin_idx is None:
        return pd.DataFrame()
    brand_idx = get_row_idx("brand")
    price_idx = get_row_idx("price")
    sales_idx = get_row_idx("sales")
    revenue_idx = get_row_idx("revenue")

    n_cols = df.shape[1]
    records = []
    for col_pos in range(1, n_cols):
        asin = df.iat[asin_idx, col_pos]
        if pd.isna(asin) or str(asin).strip() == "":
            continue
        records.append({
            "asin": str(asin).strip(),
            "brand": df.iat[brand_idx, col_pos] if brand_idx is not None else None,
            "price": _to_num(pd.Series([df.iat[price_idx, col_pos]]))[0] if price_idx is not None else np.nan,
            "sales": _to_num(pd.Series([df.iat[sales_idx, col_pos]]))[0] if sales_idx is not None else np.nan,
            "revenue": _to_num(pd.Series([df.iat[revenue_idx, col_pos]]))[0] if revenue_idx is not None else np.nan,
        })
    out = pd.DataFrame(records)
    if out.empty:
        return out
    out["niche"] = niche
    return out


# ---------------------------------------------------------------------
# PPC Daily Tracker (Date, Ad Spend, Ad Spend Sales, ACOS, ROAS,
# Total BR Sales, TACOS, Profit ...)
# ---------------------------------------------------------------------
def parse_ppc_daily(df: pd.DataFrame, niche: str) -> pd.DataFrame:
    df = _fix_header(df, key_terms=("date",))
    cols = df.columns
    date_col = _find_col(cols, "date")
    if date_col is None:
        return pd.DataFrame()

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(_col(df, date_col), errors="coerce", format="mixed")
    spend_col = _find_col(cols, "ad spend (sp/sb)", "ad spend", "sponsored products\n ad spend", "total ppc spend")
    out["ad_spend"] = _to_num(_col(df, spend_col)) if spend_col else np.nan
    sales_col = _find_col(cols, "ad spend sales", "sponsored products\n sales", "total ppc sales")
    out["ad_spend_sales"] = _to_num(_col(df, sales_col)) if sales_col else np.nan
    acos_col = _find_col(cols, "acos")
    out["acos"] = _to_num(_col(df, acos_col)) if acos_col else np.nan
    roas_col = _find_col(cols, "roas")
    out["roas"] = _to_num(_col(df, roas_col)) if roas_col else np.nan
    total_sales_col = _find_col(cols, "total br sales", "sales ($)")
    out["total_sales"] = _to_num(_col(df, total_sales_col)) if total_sales_col else np.nan
    tacos_col = _find_col(cols, "tacos")
    out["tacos"] = _to_num(_col(df, tacos_col)) if tacos_col else np.nan
    profit_col = _find_col(cols, "profit")
    out["profit"] = _to_num(_col(df, profit_col)) if profit_col else np.nan
    sessions_col = _find_col(cols, "sessions")
    out["sessions"] = _to_num(_col(df, sessions_col)) if sessions_col else np.nan
    pv_col = _find_col(cols, "page views")
    out["page_views"] = _to_num(_col(df, pv_col)) if pv_col else np.nan
    units_col = _find_col(cols, "total units")
    out["total_units"] = _to_num(_col(df, units_col)) if units_col else np.nan
    price_col = _find_col(cols, "price")
    out["price"] = _to_num(_col(df, price_col)) if price_col else np.nan

    out["niche"] = niche
    out = out.dropna(subset=["date"])
    out["date"] = out["date"].astype(str)
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------
# Search Term Report (raw Amazon Ads console export)
# ---------------------------------------------------------------------
def parse_search_term_report(df: pd.DataFrame, niche: str) -> pd.DataFrame:
    cols = df.columns
    targeting_col = _find_col(cols, "targeting", "customer search term")
    if targeting_col is None:
        return pd.DataFrame()

    out = pd.DataFrame()
    start_col = _find_col(cols, "start date")
    out["start_date"] = pd.to_datetime(_col(df, start_col), errors="coerce").astype(str) if start_col else None
    end_col = _find_col(cols, "end date")
    out["end_date"] = pd.to_datetime(_col(df, end_col), errors="coerce").astype(str) if end_col else None
    camp_col = _find_col(cols, "campaign name")
    out["campaign_name"] = _col(df, camp_col) if camp_col else None
    adg_col = _find_col(cols, "ad group name")
    out["ad_group_name"] = _col(df, adg_col) if adg_col else None
    out["targeting"] = _col(df, targeting_col).astype(str).str.strip()
    mt_col = _find_col(cols, "match type")
    out["match_type"] = _col(df, mt_col) if mt_col else None
    imp_col = _find_col(cols, "impressions")
    out["impressions"] = _to_num(_col(df, imp_col)) if imp_col else np.nan
    clicks_col = _find_col(cols, "clicks")
    out["clicks"] = _to_num(_col(df, clicks_col)) if clicks_col else np.nan
    ctr_col = _find_col(cols, "click-thru rate", "ctr")
    out["ctr"] = _to_num(_col(df, ctr_col)) if ctr_col else np.nan
    cpc_col = _find_col(cols, "cost per click", "cpc")
    out["cpc"] = _to_num(_col(df, cpc_col)) if cpc_col else np.nan
    spend_col = _find_col(cols, "spend")
    out["spend"] = _to_num(_col(df, spend_col)) if spend_col else np.nan
    acos_col = _find_col(cols, "acos")
    out["acos"] = _to_num(_col(df, acos_col)) if acos_col else np.nan
    roas_col = _find_col(cols, "roas")
    out["roas"] = _to_num(_col(df, roas_col)) if roas_col else np.nan
    sales_col = _find_col(cols, "7 day total sales", "total sales")
    out["sales"] = _to_num(_col(df, sales_col)) if sales_col else np.nan
    orders_col = _find_col(cols, "7 day total orders", "total orders")
    out["orders"] = _to_num(_col(df, orders_col)) if orders_col else np.nan
    units_col = _find_col(cols, "7 day total units", "total units")
    out["units"] = _to_num(_col(df, units_col)) if units_col else np.nan

    out["niche"] = niche
    out = out.dropna(subset=["targeting"])
    out = out[out["targeting"].str.lower() != "nan"]
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------
# Profit calculator sheet (ASIN, Product Name, Weekly ST, Revenue,
# ASP, TACOS, Profit %, Profit (Per Unit), Landed Cost, Referral Fee,
# PPC, FBA Fee, Storage Fee, Coupon %, Total Cost)
# ---------------------------------------------------------------------
def parse_profit(df: pd.DataFrame) -> pd.DataFrame:
    df = _fix_header(df, key_terms=("asin",))
    cols = df.columns
    asin_col = _find_col(cols, "asin")
    if asin_col is None:
        return pd.DataFrame()

    out = pd.DataFrame()
    out["asin"] = _col(df, asin_col)
    name_col = _find_col(cols, "product name")
    out["product_name"] = _col(df, name_col) if name_col else None
    wk_col = _find_col(cols, "weekly st")
    out["weekly_units"] = _to_num(_col(df, wk_col)) if wk_col else np.nan
    rev_col = _find_col(cols, "revenue")
    out["revenue"] = _to_num(_col(df, rev_col)) if rev_col else np.nan
    asp_col = _find_col(cols, "asp")
    out["asp"] = _to_num(_col(df, asp_col)) if asp_col else np.nan
    landed_col = _find_col(cols, "landed cost")
    out["landed_cost"] = _to_num(_col(df, landed_col)) if landed_col else np.nan
    ref_col = _find_col(cols, "referral fee")
    out["referral_fee"] = _to_num(_col(df, ref_col)) if ref_col else np.nan
    ppc_col = _find_col(cols, "ppc")
    out["ppc_cost"] = _to_num(_col(df, ppc_col)) if ppc_col else np.nan
    fba_col = _find_col(cols, "fba fee")
    out["fba_fee"] = _to_num(_col(df, fba_col)) if fba_col else np.nan
    storage_col = _find_col(cols, "storage fee")
    out["storage_fee"] = _to_num(_col(df, storage_col)) if storage_col else np.nan
    coupon_col = _find_col(cols, "coupon %")
    out["coupon_pct"] = _to_num(_col(df, coupon_col)) if coupon_col else np.nan
    total_cost_col = _find_col(cols, "total cost")
    out["total_cost"] = _to_num(_col(df, total_cost_col)) if total_cost_col else np.nan
    pu_col = _find_col(cols, "profit (per unit)", "profit per unit")
    out["profit_per_unit"] = _to_num(_col(df, pu_col)) if pu_col else np.nan
    pct_col = _find_col(cols, "profit %")
    out["profit_pct"] = _to_num(_col(df, pct_col)) if pct_col else np.nan

    out = out.dropna(subset=["asin"])
    out = out[out["asin"].astype(str).str.strip() != ""]
    return out.reset_index(drop=True)
