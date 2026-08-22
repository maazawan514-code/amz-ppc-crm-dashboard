import streamlit as st
import pandas as pd
import plotly.express as px
from db import init_db, insert_df, read_table
from parsers import read_any, parse_profit

init_db()
st.set_page_config(page_title="Profit Calculator", page_icon="🧮", layout="wide")
st.title("🧮 Profit Calculator")
st.caption("Per-ASIN cost breakdown sheet upload karein (Landed Cost, Referral Fee, PPC, FBA Fee, Storage Fee...) — ya neeche manually calculate karein.")

with st.form("upload_profit"):
    file = st.file_uploader("Profit sheet (.csv / .xlsx)", type=["csv", "xlsx"])
    submitted = st.form_submit_button("Upload & Save")

if submitted:
    if not file:
        st.error("Koi file select nahi hui.")
    else:
        sheets = read_any(file)
        total = 0
        for sheet_name, df in sheets.items():
            parsed = parse_profit(df)
            if not parsed.empty:
                total += insert_df("profit_calc", parsed, file.name)
        if total:
            st.success(f"{total} ASIN profit rows save ho gayi.")
        else:
            st.warning("Is file mein ASIN column nahi mila.")

st.divider()

df = read_table("profit_calc")

if not df.empty:
    latest = df["uploaded_at"].max()
    df_latest = df[df["uploaded_at"] == latest]
    st.subheader("Uploaded profit data (latest)")
    st.dataframe(
        df_latest[["asin", "product_name", "weekly_units", "revenue", "asp", "landed_cost",
                  "referral_fee", "ppc_cost", "fba_fee", "storage_fee", "total_cost",
                  "profit_per_unit", "profit_pct"]],
        use_container_width=True, height=300
    )
    fig = px.bar(df_latest.sort_values("profit_per_unit", ascending=False),
                x="profit_per_unit", y="product_name", orientation="h",
                title="Profit per unit by product")
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)
    st.download_button("⬇️ CSV download karein", df_latest.to_csv(index=False), "profit_calc.csv")

st.divider()
st.subheader("🧮 Quick manual calculator")

c1, c2, c3 = st.columns(3)
price = c1.number_input("Selling Price ($)", min_value=0.0, value=25.99, step=0.01)
landed_cost = c1.number_input("Landed Cost ($)", min_value=0.0, value=8.0, step=0.01)
referral_pct = c2.number_input("Referral Fee (%)", min_value=0.0, max_value=100.0, value=15.0, step=0.1) / 100
fba_fee = c2.number_input("FBA Fee ($)", min_value=0.0, value=4.5, step=0.01)
ppc_per_unit = c3.number_input("PPC Cost per Unit ($)", min_value=0.0, value=3.0, step=0.01)
storage_fee = c3.number_input("Storage Fee per Unit ($)", min_value=0.0, value=0.5, step=0.01)

referral_fee = price * referral_pct
total_cost = landed_cost + referral_fee + fba_fee + ppc_per_unit + storage_fee
profit = price - total_cost
margin = profit / price if price else 0

r1, r2, r3 = st.columns(3)
r1.metric("Total Cost / Unit", f"${total_cost:,.2f}")
r2.metric("Profit / Unit", f"${profit:,.2f}")
r3.metric("Profit Margin", f"{margin:.1%}")
