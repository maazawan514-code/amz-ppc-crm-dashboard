import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from db import init_db, insert_df, read_table, list_niches
from parsers import read_any, parse_rank_tracker

init_db()
st.set_page_config(page_title="Rank Tracking", page_icon="📈", layout="wide")
st.title("📈 Keyword Rank Tracking")
st.caption("Helium 10 Rank Tracker export ya weekly KWs Tracker sheet upload karein — organic rank ka trend time ke saath dikhega.")

with st.form("upload_rank"):
    col1, col2, col3 = st.columns([2, 1, 1])
    niche = col1.text_input("Niche naam", "")
    file = col2.file_uploader("Rank tracker file (.csv / .xlsx)", type=["csv", "xlsx"])
    tracked_date = col3.date_input("Tracked date (agar file mein date column nahi)", value=date.today())
    submitted = st.form_submit_button("Upload & Save")

if submitted:
    if not niche.strip():
        st.error("Pehle niche ka naam likhein.")
    elif not file:
        st.error("Koi file select nahi hui.")
    else:
        sheets = read_any(file)
        total = 0
        for sheet_name, df in sheets.items():
            parsed = parse_rank_tracker(df, niche.strip(), tracked_date=tracked_date)
            if not parsed.empty:
                total += insert_df("keyword_rank_tracking", parsed, file.name)
        if total:
            st.success(f"{total} rank-tracking rows save ho gayi '{niche}' niche ke liye.")
        else:
            st.warning("Is file mein 'Keyword' column nahi mila — format check kar lein.")

st.divider()

niches = ["All niches"] + list_niches()
selected_niche = st.selectbox("Niche filter", niches)

df = read_table("keyword_rank_tracking", selected_niche)

if df.empty:
    st.info("Abhi koi rank-tracking data nahi hai. Upar se file upload karein.")
else:
    df["tracked_date"] = pd.to_datetime(df["tracked_date"], errors="coerce")

    all_keywords = sorted(df["keyword"].dropna().unique().tolist())
    chosen = st.multiselect("Keywords select karein (trend dekhne ke liye)", all_keywords,
                              default=all_keywords[:5] if len(all_keywords) >= 5 else all_keywords)

    if chosen:
        trend_df = df[df["keyword"].isin(chosen)].sort_values("tracked_date")
        fig = px.line(trend_df, x="tracked_date", y="organic_rank", color="keyword", markers=True,
                      title="Organic Rank Trend (neeche jaana = better rank)")
        fig.update_yaxes(autorange="reversed")  # rank 1 at top
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Latest rank snapshot")
    latest = df.sort_values("tracked_date").groupby(["asin", "keyword"], as_index=False).tail(1)
    st.dataframe(
        latest.sort_values("organic_rank")[
            ["niche", "asin", "keyword", "search_volume", "cpr", "organic_rank", "sponsored_position", "tracked_date"]
        ],
        use_container_width=True, height=400
    )
    st.download_button("⬇️ Latest snapshot CSV", latest.to_csv(index=False), "rank_tracking_latest.csv")
