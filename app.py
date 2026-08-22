import streamlit as st
from db import init_db, row_counts, list_niches

st.set_page_config(page_title="Amazon PPC CRM Dashboard", page_icon="📊", layout="wide")
init_db()

st.title("📊 Amazon PPC CRM Dashboard")
st.caption("Keyword research • Rank tracking • Niche analysis • PPC performance • Search term analysis • Profit")

counts = row_counts()
niches = list_niches()

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Keywords (Cerebro)", counts.get("cerebro_keywords", 0))
c2.metric("Rank tracking rows", counts.get("keyword_rank_tracking", 0))
c3.metric("Market analysis rows", counts.get("market_analysis", 0))
c4.metric("PPC daily rows", counts.get("ppc_daily", 0))
c5.metric("Search term rows", counts.get("search_term_report", 0))
c6.metric("Niches tracked", len(niches))

st.divider()

st.markdown("""
### Kaise use karein

Sidebar mein se page choose karein aur apni Helium 10 / Amazon Ads exports upload karein — data
apne aap SQLite database (`ppc_crm.db`) mein save ho jayega, isliye har naya upload purani history
mein add hota jayega (tracking automatically build hoti hai).

| Page | Konsi file upload karein |
|---|---|
| **Keyword Research** | Helium 10 **Cerebro** export (.csv ya .xlsx) |
| **Rank Tracking** | Helium 10 **Rank Tracker** export, ya weekly KWs Tracker sheet |
| **Market / Niche Analysis** | Competitor ASIN comparison sheet (ASIN, Brand, Price, Sales, Revenue) |
| **PPC Daily Performance** | Aapka daily PPC tracker (Date, Ad Spend, ACOS, ROAS, TACOS, Profit...) |
| **Search Term Report** | Amazon Ads console se **Search Term Report** export |
| **Profit Calculator** | Per-ASIN cost breakdown sheet (Landed Cost, Referral Fee, PPC, FBA Fee...) |

Har page pe **niche** naam likhna zaroori hai (jaise "Bifold Wallet", "Crossbody Handbag") taake
saari niches ka data alag track ho sake, ek hi dashboard mein.
""")

if niches:
    st.info("Ab tak track ho rahi niches: " + ", ".join(niches))
else:
    st.warning("Abhi tak koi data upload nahi hua. Sidebar se koi bhi page khol kar apni pehli file upload karein.")
