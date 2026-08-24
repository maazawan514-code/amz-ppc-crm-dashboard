import streamlit as st
import pandas as pd
import plotly.express as px
from db import init_db, read_table, list_niches

init_db()
st.set_page_config(page_title="Master Keyword Research — Niche Evaluator", page_icon="🎯", layout="wide")
st.title("🎯 Master Keyword Research — Niche Evaluator")
st.caption(
    "Yeh page us 'Master Keyword Research' method ko automate karta hai jo video mein manually Excel formulas "
    "(word count, COUNTIF, % calculations) se ki jati hai — reverse ASIN se Cerebro data upload karein "
    "(Keyword Research page se), phir yahan niche ka competition level (green/orange/red) dekhein."
)

niches = list_niches()
if not niches:
    st.info("Pehle Keyword Research page se Cerebro export upload karein (reverse ASIN search se, top 10 competitors ka).")
    st.stop()

niche = st.selectbox("Niche select karein", niches)
df = read_table("cerebro_keywords", niche)

if df.empty:
    st.info(f"'{niche}' ke liye abhi koi keyword data nahi hai.")
    st.stop()

# --- Word count formula equivalent: =LEN(TRIM(A3))-LEN(SUBSTITUTE(A3," ",""))+1 ---
df["word_count"] = df["keyword_phrase"].fillna("").apply(lambda x: len(str(x).split()))

st.divider()
st.subheader("1️⃣ Filter thresholds (video mein manually COUNTIF se set kiye jate hain)")

c1, c2 = st.columns(2)
min_sv = c1.number_input("Minimum Search Volume", min_value=0, value=50, step=10,
                          help="Video mein default 50 use hua hai")
min_rel = c2.number_input("Minimum Relevancy", min_value=0.0, value=2.0, step=0.5,
                           help="Video mein default 2 use hua hai — agar aapki file mein Relevancy column nahi hai to yeh 0 rakhein")

has_relevancy = df["relevancy"].notna().any()
if has_relevancy:
    matching = df[(df["search_volume"].fillna(0) > min_sv) & (df["relevancy"].fillna(0) > min_rel)]
else:
    matching = df[df["search_volume"].fillna(0) > min_sv]
    st.warning("Is niche ke data mein 'Relevancy' column nahi mila — sirf Search Volume se filter ho raha hai.")

total_kw = len(df)
total_sv = df["search_volume"].fillna(0).sum()
matching_kw = len(matching)
matching_sv = matching["search_volume"].fillna(0).sum()

pct_kw = (matching_kw / total_kw * 100) if total_kw else 0
pct_sv = (matching_sv / total_sv * 100) if total_sv else 0

st.divider()
st.subheader("2️⃣ COUNTIF results (automatic)")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total keywords", total_kw)
m2.metric("Matching keywords", matching_kw, f"{pct_kw:.1f}% of total")
m3.metric("Total search volume", f"{total_sv:,.0f}")
m4.metric("Matching search volume", f"{matching_sv:,.0f}", f"{pct_sv:.1f}% of total")

st.divider()
st.subheader("3️⃣ Niche competition zone")

zc1, zc2 = st.columns(2)
green_cutoff = zc1.slider("Green zone cutoff (% matching keywords se kam)", 0, 100, 30,
                           help="Isse kam % matching keywords ho to niche mein gaps hain — naye seller ke liye achha")
red_cutoff = zc2.slider("Red zone cutoff (% matching keywords se zyada)", 0, 100, 60,
                         help="Isse zyada % matching keywords ho to established competitors dominate karte hain")

if pct_kw < green_cutoff:
    zone, color, msg = "🟢 GREEN", "green", "Kam keywords high-value hain — gaps maujood hain, naye seller ke liye entry aasan ho sakti hai."
elif pct_kw < red_cutoff:
    zone, color, msg = "🟠 ORANGE", "orange", "Moderate competition — targeted keywords se compete kiya ja sakta hai."
else:
    zone, color, msg = "🔴 RED", "red", "High competition — bohot saare keywords high search volume ke sath hain, established sellers dominate kar rahe hain."

st.markdown(f"### {zone} ZONE")
st.write(msg)
st.caption("Yeh heuristic hai (video ke framework pe based) — final decision profit margin, product variations, reviews/ratings, aur social presence dekh kar lein.")

st.divider()
st.subheader("4️⃣ Word count distribution")
st.caption("Zyada words wali (long-tail) keywords aksar kam competitive hoti hain.")

wc_dist = df["word_count"].value_counts().sort_index().reset_index()
wc_dist.columns = ["word_count", "count"]
fig = px.bar(wc_dist, x="word_count", y="count", title="Keywords by word count")
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("5️⃣ Matching keywords (high value — high volume + relevant)")
show_cols = ["keyword_phrase", "search_volume", "word_count"]
if has_relevancy:
    show_cols.insert(2, "relevancy")
if df["cerebro_iq_score"].notna().any():
    show_cols.append("cerebro_iq_score")

st.dataframe(
    matching.sort_values("search_volume", ascending=False)[show_cols],
    use_container_width=True, height=400
)

st.download_button(
    "⬇️ Matching keywords download karein (CSV)",
    matching[show_cols].to_csv(index=False),
    f"{niche}_master_kw_matching.csv"
)

st.divider()
st.info(
    "📸 **Competitor images/reviews/ratings** ke liye: yeh Market Analysis page pe niche select kar ke "
    "brand/ASIN comparison dekh sakte hain. Visual images abhi tak automate nahi hain (Amazon API access chahiye) — "
    "filhal Market Analysis se ASIN copy kar ke manually check karna hoga."
)
