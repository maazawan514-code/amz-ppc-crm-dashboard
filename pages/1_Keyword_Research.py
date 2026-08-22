import streamlit as st
import pandas as pd
import plotly.express as px
from db import init_db, insert_df, read_table, list_niches
from parsers import read_any, parse_cerebro

init_db()
st.set_page_config(page_title="Keyword Research", page_icon="🔍", layout="wide")
st.title("🔍 Keyword Research (Cerebro)")
st.caption("Helium 10 Cerebro export upload karein — keyword phrase, search volume, CPR, competing products, title density, organic rank sab yahan analyze hoga.")

with st.form("upload_form"):
    col1, col2 = st.columns([2, 1])
    niche = col1.text_input("Niche naam (jaise 'Bifold Wallet')", "")
    file = col2.file_uploader("Cerebro file (.csv / .xlsx)", type=["csv", "xlsx"])
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
            parsed = parse_cerebro(df, niche.strip())
            if not parsed.empty:
                total += insert_df("cerebro_keywords", parsed, file.name)
        if total:
            st.success(f"{total} keywords save ho gayi '{niche}' niche ke liye.")
        else:
            st.warning("Is file mein 'Keyword Phrase' column nahi mila — format check kar lein.")

st.divider()

niches = ["All niches"] + list_niches()
selected_niche = st.selectbox("Niche filter", niches)

df = read_table("cerebro_keywords", selected_niche)

if df.empty:
    st.info("Abhi koi keyword data nahi hai. Upar se Cerebro file upload karein.")
else:
    st.subheader(f"{len(df)} keywords")

    fcol1, fcol2, fcol3 = st.columns(3)
    min_sv = fcol1.number_input("Min Search Volume", min_value=0, value=0)
    max_cpr = fcol2.number_input("Max CPR (0 = no limit)", min_value=0, value=0)
    search_text = fcol3.text_input("Keyword contains", "")

    filtered = df.copy()
    if min_sv:
        filtered = filtered[filtered["search_volume"] >= min_sv]
    if max_cpr:
        filtered = filtered[filtered["cpr"] <= max_cpr]
    if search_text:
        filtered = filtered[filtered["keyword_phrase"].str.contains(search_text, case=False, na=False)]

    st.dataframe(
        filtered.sort_values("search_volume", ascending=False)[
            ["niche", "keyword_phrase", "search_volume", "competing_products", "cpr",
             "title_density", "organic_rank", "cerebro_iq_score", "uploaded_at"]
        ],
        use_container_width=True, height=400
    )

    st.download_button("⬇️ Filtered CSV download karein", filtered.to_csv(index=False), "keyword_research.csv")

    st.markdown("#### Top opportunity keywords (high volume, low CPR)")
    opp = filtered.dropna(subset=["search_volume", "cpr"])
    opp = opp[opp["cpr"] > 0]
    opp["opportunity_score"] = opp["search_volume"] / opp["cpr"]
    top_opp = opp.sort_values("opportunity_score", ascending=False).head(20)
    if not top_opp.empty:
        fig = px.bar(top_opp, x="opportunity_score", y="keyword_phrase", orientation="h",
                      hover_data=["search_volume", "cpr", "competing_products"],
                      title="Search Volume ÷ CPR — highest opportunity keywords")
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=600)
        st.plotly_chart(fig, use_container_width=True)
