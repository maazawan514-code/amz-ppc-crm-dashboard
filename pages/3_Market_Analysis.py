import streamlit as st
import pandas as pd
import plotly.express as px
from db import init_db, insert_df, read_table, list_niches
from parsers import read_any, parse_market_analysis

init_db()
st.set_page_config(page_title="Market / Niche Analysis", page_icon="🏆", layout="wide")
st.title("🏆 Market / Niche Analysis")
st.caption("Competitor ASIN comparison sheet upload karein (ASIN, Brand, Price, Sales, Revenue rows).")

with st.form("upload_market"):
    col1, col2 = st.columns([2, 1])
    niche = col1.text_input("Niche naam", "")
    file = col2.file_uploader("Market analysis file (.csv / .xlsx)", type=["csv", "xlsx"])
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
            parsed = parse_market_analysis(df, niche.strip())
            if not parsed.empty:
                total += insert_df("market_analysis", parsed, file.name)
        if total:
            st.success(f"{total} competitor rows save ho gayi '{niche}' niche ke liye.")
        else:
            st.warning("Is file mein ASIN/Brand/Price/Sales/Revenue rows nahi mile — format check kar lein.")

st.divider()

niches = ["All niches"] + list_niches()
selected_niche = st.selectbox("Niche filter", niches)

df = read_table("market_analysis", selected_niche)

if df.empty:
    st.info("Abhi koi market-analysis data nahi hai. Upar se file upload karein.")
else:
    latest_upload = df["uploaded_at"].max()
    df_latest = df[df["uploaded_at"] == latest_upload]

    st.subheader(f"Niche snapshot ({len(df_latest)} competitors, latest upload)")
    st.dataframe(
        df_latest.sort_values("revenue", ascending=False)[
            ["niche", "asin", "brand", "price", "sales", "revenue"]
        ],
        use_container_width=True, height=350
    )

    c1, c2 = st.columns(2)
    with c1:
        fig1 = px.bar(df_latest.sort_values("revenue", ascending=False).head(15),
                      x="revenue", y="brand", orientation="h",
                      hover_data=["asin", "price", "sales"], title="Revenue by competitor")
        fig1.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig1, use_container_width=True)
    with c2:
        fig2 = px.scatter(df_latest, x="price", y="sales", color="brand", size="revenue",
                          hover_data=["asin"], title="Price vs Sales (bubble = revenue)")
        st.plotly_chart(fig2, use_container_width=True)

    st.download_button("⬇️ CSV download karein", df_latest.to_csv(index=False), "market_analysis.csv")
