import streamlit as st
import pandas as pd
import plotly.express as px
from db import init_db, insert_df, read_table, list_niches
from parsers import read_any, parse_search_term_report

init_db()
st.set_page_config(page_title="Search Term Report", page_icon="🔎", layout="wide")
st.title("🔎 Search Term Report Analysis")
st.caption("Amazon Ads console se Search Term Report export karein aur yahan upload karein — wasted spend, converting terms, aur harvest candidates dikhenge.")

with st.form("upload_str"):
    col1, col2 = st.columns([2, 1])
    niche = col1.text_input("Niche naam", "")
    file = col2.file_uploader("Search Term Report file (.csv / .xlsx)", type=["csv", "xlsx"])
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
            parsed = parse_search_term_report(df, niche.strip())
            if not parsed.empty:
                total += insert_df("search_term_report", parsed, file.name)
        if total:
            st.success(f"{total} search-term rows save ho gayi '{niche}' ke liye.")
        else:
            st.warning("Is file mein 'Targeting' / 'Customer Search Term' column nahi mila.")

st.divider()

niches = ["All niches"] + list_niches()
selected_niche = st.selectbox("Niche filter", niches)

df = read_table("search_term_report", selected_niche)

if df.empty:
    st.info("Abhi koi Search Term Report data nahi hai. Upar se file upload karein.")
else:
    df["sales"] = df["sales"].fillna(0)
    df["spend"] = df["spend"].fillna(0)
    df["clicks"] = df["clicks"].fillna(0)
    df["orders"] = df["orders"].fillna(0)

    tab1, tab2, tab3 = st.tabs(["🔴 Wasted Spend (0 sales)", "🟢 Top Converting Terms", "🟡 Harvest Candidates (Auto/Broad)"])

    with tab1:
        wasted = df[(df["spend"] > 0) & (df["sales"] == 0)].sort_values("spend", ascending=False)
        st.markdown(f"**{len(wasted)} search terms** ne spend kiya lekin **koi sale nahi hui** — inhe negative keywords ki tarah add karne ka soch sakte hain.")
        st.metric("Total wasted spend", f"${wasted['spend'].sum():,.2f}")
        st.dataframe(
            wasted[["niche", "campaign_name", "ad_group_name", "targeting", "match_type",
                    "impressions", "clicks", "spend"]],
            use_container_width=True, height=400
        )
        st.download_button("⬇️ Wasted spend CSV", wasted.to_csv(index=False), "wasted_spend.csv")

    with tab2:
        converting = df[df["orders"] > 0].sort_values("sales", ascending=False)
        st.markdown(f"**{len(converting)} search terms** ne sales generate ki.")
        st.dataframe(
            converting[["niche", "campaign_name", "targeting", "match_type", "clicks",
                        "spend", "sales", "orders", "acos"]],
            use_container_width=True, height=400
        )
        top20 = converting.head(20)
        if not top20.empty:
            fig = px.bar(top20, x="sales", y="targeting", orientation="h",
                        hover_data=["spend", "orders", "acos"], title="Top 20 converting search terms")
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=600)
            st.plotly_chart(fig, use_container_width=True)
        st.download_button("⬇️ Converting terms CSV", converting.to_csv(index=False), "converting_terms.csv")

    with tab3:
        harvest = df[(df["match_type"].str.upper().isin(["BROAD", "-", "LOOSE-MATCH"]) | df["match_type"].isna())
                     & (df["orders"] >= 1)].sort_values("orders", ascending=False)
        st.markdown("Broad/Auto campaigns se converting search terms — inhe **exact match** campaigns mein 'harvest' karne ka waqt hai.")
        st.dataframe(
            harvest[["niche", "campaign_name", "targeting", "match_type", "clicks",
                    "spend", "sales", "orders", "acos"]],
            use_container_width=True, height=400
        )
        st.download_button("⬇️ Harvest candidates CSV", harvest.to_csv(index=False), "harvest_candidates.csv")
