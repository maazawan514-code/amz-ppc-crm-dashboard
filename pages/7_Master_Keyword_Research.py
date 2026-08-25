import streamlit as st
import pandas as pd
import plotly.express as px
from db import init_db, read_table, list_niches, insert_df
from master_kw_parser import parse_master_kw_file, parse_raw_cerebro_asin_export, compute_competitor_scores, niche_verdict

init_db()
st.set_page_config(page_title="Master Keyword Research — Niche Evaluator", page_icon="🎯", layout="wide")
st.title("🎯 Master Keyword Research — Niche Evaluator")

tab_grid, tab_simple = st.tabs(["🏆 Competitor Rank Grid (exact template)", "📋 Simple Cerebro-based evaluator"])

# ---------------------------------------------------------------------------
# TAB 1: exact "Master Keyword Research" template — keyword x ASIN rank grid
# ---------------------------------------------------------------------------
with tab_grid:
    upload_mode = st.radio(
        "Upload type",
        ["🤖 Raw Cerebro export with tracked ASINs (fully automatic)", "📋 Manual Master KW Research template (.xlsx)"],
        help="Cerebro mein export se pehle 'Add ASINs to track' feature se apne top competitors ke ASIN add karein — "
             "phir seedha wahi CSV/XLSX upload karein, koi manual sheet banane ki zaroorat nahi."
    )

    with st.form("master_kw_upload"):
        c1, c2 = st.columns([2, 1])
        niche_grid = c1.text_input("Niche naam", "")
        if upload_mode.startswith("🤖"):
            grid_file = c2.file_uploader("Cerebro export (.csv / .xlsx)", type=["csv", "xlsx"])
        else:
            grid_file = c2.file_uploader("Master KW Research file (.xlsx)", type=["xlsx"])
        submitted_grid = st.form_submit_button("Upload & Save")

    if submitted_grid:
        if not niche_grid.strip():
            st.error("Pehle niche ka naam likhein.")
        elif not grid_file:
            st.error("Koi file select nahi hui.")
        else:
            try:
                if upload_mode.startswith("🤖"):
                    result = parse_raw_cerebro_asin_export(grid_file)
                else:
                    result = parse_master_kw_file(grid_file)
                grid_df = result["grid"]
                grid_df["niche"] = niche_grid.strip()
                grid_df["main_keyword"] = result["main_keyword"]
                n = insert_df("master_kw_grid", grid_df, grid_file.name)
                st.success(f"{n} rows save ho gaye '{niche_grid}' niche ke liye ({grid_df['keyword_phrase'].nunique()} keywords x {grid_df['asin'].nunique()} ASINs).")
                if grid_df["relevancy"].isna().all():
                    st.info("ℹ️ Is file mein Relevancy column nahi mila — filter thresholds mein Relevancy 0 par rakhein, "
                            "ya Cerebro se export karte waqt Relevancy column include karein (root keyword set kar ke) zyada accurate result ke liye.")
            except ValueError as e:
                st.error(str(e))

    st.divider()

    grid_niches = read_table("master_kw_grid")
    if grid_niches.empty:
        st.info("Abhi koi grid data nahi hai. Upar se file upload karein.")
    else:
        niche_options = sorted(grid_niches["niche"].dropna().unique())
        sel_niche = st.selectbox("Niche select karein", niche_options, key="grid_niche")
        grid = read_table("master_kw_grid", sel_niche)
        main_kw = grid["main_keyword"].iloc[0] if grid["main_keyword"].notna().any() else sel_niche

        st.markdown("#### Filter thresholds")
        fc1, fc2, fc3 = st.columns(3)
        rank_thresh = fc1.number_input("Organic Rank < (competitor 'ranks well' cutoff)", min_value=1, value=30)
        rel_thresh = fc2.number_input("Relevancy > (0 = sab keywords count)", min_value=0.0, value=0.0, step=0.5)
        sv_thresh = fc3.number_input("Search Volume > (0 = sab keywords count)", min_value=0, value=0, step=50)

        scores, total_sv, total_kw = compute_competitor_scores(grid, rank_thresh, rel_thresh, sv_thresh)
        verdict, red, orange, yellow, green = niche_verdict(scores)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total relevant keywords", total_kw)
        m2.metric("Total search volume", f"{total_sv:,.0f}")
        m3.metric("Competitors analyzed", len(scores))
        m4.metric("🔴/🟠/🟡/🟢", f"{red}/{orange}/{yellow}/{green}")

        st.markdown(f"### {verdict}")
        st.caption(
            "⚠️ Yeh classification sirf rank/search-volume coverage se calculate hui hai (data-driven estimate). "
            "Final decision reviews, ratings, price aur listing quality dekh kar bhi lein — wo is data mein nahi hai."
        )

        st.markdown("#### Competitor scorecard")
        st.dataframe(
            scores.rename(columns={
                "asin": "ASIN", "sv_captured": "SV Captured", "pct_sv": "% of Total SV",
                "kw_captured": "Keywords Captured", "pct_kw": "% of Total KW", "zone": "Zone", "color": ""
            }),
            use_container_width=True
        )

        st.markdown("#### Keyword x ASIN rank grid")
        pivot = grid.pivot_table(index="keyword_phrase", columns="asin", values="organic_rank", aggfunc="first")
        meta = grid.drop_duplicates(subset=["keyword_phrase"]).set_index("keyword_phrase")[["search_volume", "relevancy"]]
        display_df = meta.join(pivot).sort_values("search_volume", ascending=False)
        st.dataframe(display_df, use_container_width=True, height=450)

        from export_report import build_master_kw_report
        report_buf = build_master_kw_report(sel_niche, main_kw, grid, scores, total_sv, total_kw, verdict)
        st.download_button(
            "📊 Colored Excel report download karein (exact template format)",
            report_buf.getvalue(),
            f"{sel_niche}_master_keyword_research.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ---------------------------------------------------------------------------
# TAB 2: simple Cerebro-only evaluator (word count / COUNTIF, no ASIN grid)
# ---------------------------------------------------------------------------
with tab_simple:
    st.caption(
        "Agar aapke paas sirf Cerebro export hai (competitor ASIN rank grid nahi), yeh simpler evaluator use karein."
    )

    niches = list_niches()
    if not niches:
        st.info("Pehle Keyword Research page se Cerebro export upload karein.")
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
