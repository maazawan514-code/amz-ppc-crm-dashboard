import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from db import init_db, insert_df, read_table, list_niches
from parsers import read_any, parse_ppc_daily

init_db()
st.set_page_config(page_title="PPC Daily Performance", page_icon="💰", layout="wide")
st.title("💰 PPC Daily Performance")
st.caption("Aapka daily PPC tracker sheet upload karein (Date, Ad Spend, ACOS, ROAS, TACOS, Profit...).")

with st.form("upload_ppc"):
    col1, col2 = st.columns([2, 1])
    niche = col1.text_input("Niche / product naam", "")
    file = col2.file_uploader("PPC daily tracker file (.csv / .xlsx)", type=["csv", "xlsx"])
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
            parsed = parse_ppc_daily(df, niche.strip())
            if not parsed.empty:
                total += insert_df("ppc_daily", parsed, file.name)
        if total:
            st.success(f"{total} daily rows save ho gayi '{niche}' ke liye.")
        else:
            st.warning("Is sheet mein 'Date' column nahi mila — agar workbook mein kayi sheets hain to har sheet try ki gayi hai.")

st.divider()

niches = ["All niches"] + list_niches()
selected_niche = st.selectbox("Niche filter", niches)

df = read_table("ppc_daily", selected_niche)

if df.empty:
    st.info("Abhi koi PPC daily data nahi hai. Upar se file upload karein.")
else:
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    df = df.drop_duplicates(subset=["niche", "date"], keep="last")

    date_range = st.date_input("Date range", value=(df["date"].min(), df["date"].max()))
    if isinstance(date_range, tuple) and len(date_range) == 2:
        mask = (df["date"] >= pd.Timestamp(date_range[0])) & (df["date"] <= pd.Timestamp(date_range[1]))
        df = df[mask]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Spend", f"${df['ad_spend'].sum():,.0f}")
    c2.metric("Total Ad Sales", f"${df['ad_spend_sales'].sum():,.0f}")
    avg_acos = df["acos"].mean()
    c3.metric("Avg ACOS", f"{avg_acos:.1%}" if pd.notna(avg_acos) else "—")
    avg_tacos = df["tacos"].mean()
    c4.metric("Avg TACOS", f"{avg_tacos:.1%}" if pd.notna(avg_tacos) else "—")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["ad_spend"], name="Ad Spend", mode="lines"))
    fig.add_trace(go.Scatter(x=df["date"], y=df["ad_spend_sales"], name="Ad Sales", mode="lines"))
    fig.add_trace(go.Scatter(x=df["date"], y=df["total_sales"], name="Total Sales", mode="lines"))
    fig.update_layout(title="Spend vs Sales over time", height=400)
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df["date"], y=df["acos"], name="ACOS", mode="lines"))
    fig2.add_trace(go.Scatter(x=df["date"], y=df["tacos"], name="TACOS", mode="lines"))
    fig2.update_layout(title="ACOS vs TACOS over time", yaxis_tickformat=".0%", height=350)
    st.plotly_chart(fig2, use_container_width=True)

    st.dataframe(df, use_container_width=True, height=350)
    st.download_button("⬇️ CSV download karein", df.to_csv(index=False), "ppc_daily.csv")
