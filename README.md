# Amazon PPC CRM Dashboard — Keyword Research, Rank Tracking, Market Analysis, PPC Performance, Search Term Analysis, Profit Calculator

100% free tech stack. Sab kuch aapke apne laptop/database pe chalta hai — koi paid subscription nahi.

## Tech Stack (sab free)

| Layer | Tool |
|---|---|
| Language | Python 3 |
| Dashboard UI | Streamlit (free, open-source) |
| Data processing | pandas |
| Database | SQLite (`ppc_crm.db` — ek file, koi server setup nahi) |
| Charts | Plotly |
| Excel/CSV reading | openpyxl |
| Free deployment (optional) | Streamlit Community Cloud (share.streamlit.io) |

## Kaise chalayein (local)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Browser mein `http://localhost:8501` khul jayega.

## Google Colab / Jupyter mein chalane ke liye

Streamlit normally Colab mein directly nahi chalta (woh apna local server banata hai), lekin do options hain:

**Option A (recommended) — apne laptop pe chalayein.** Yeh sabse simple hai, upar wale commands se.

**Option B — Colab mein free tunnel se:**
```python
!pip install streamlit pandas plotly openpyxl -q
!wget -q -O cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
!chmod +x cloudflared
# apni saari .py files Colab mein upload karein, phir:
!streamlit run app.py &>/content/log.txt &
!./cloudflared tunnel --url http://localhost:8501
```
Yeh ek free public URL de dega jo aap kahin se bhi khol sakte hain.

## Free permanent deployment (taake laptop band hone pe bhi chale)

1. Yeh poora folder GitHub pe ek repo mein push karein (private repo bhi free hai)
2. [share.streamlit.io](https://share.streamlit.io) pe jayein, GitHub se login karein
3. "New app" → apni repo select karein → main file `app.py` batayein → Deploy
4. Free tier: 1 GB RAM, public URL, aapke data ke liye kaafi hai

**Note:** free tier pe deploy karte waqt `ppc_crm.db` reset ho sakta hai agar app sleep ho kar restart ho — is case mein data persist karne ke liye Google Sheets ko backend banana behtar hoga (agla step, agar chahiye to bata dein).

## Kaam kaise karta hai

Har page (sidebar mein) ek specific file-type accept karta hai. Upload karte hi data **SQLite database mein permanently save** ho jata hai (append hota hai, overwrite nahi) — isliye jitni baar aap naye exports upload karte jayenge, utni hi zyada history/tracking build hoti jayegi.

| Page | Kaunsi file upload karein | Kya milega |
|---|---|---|
| 🔍 Keyword Research | Helium 10 **Cerebro** export (.csv/.xlsx) | Search volume, CPR, competition, opportunity score |
| 📈 Rank Tracking | Helium 10 rank tracker export, ya weekly KWs Tracker sheet | Organic rank trend chart over time |
| 🏆 Market/Niche Analysis | Competitor ASIN comparison sheet | Revenue/price/sales by competitor, bubble chart |
| 💰 PPC Daily Performance | Daily PPC tracker (Date, Ad Spend, ACOS, ROAS, TACOS...) | Spend vs sales trend, ACOS/TACOS trend |
| 🔎 Search Term Report | Amazon Ads console Search Term Report export | Wasted spend, top converters, harvest candidates |
| 🧮 Profit Calculator | Per-ASIN cost breakdown sheet, ya manual entry | Profit per unit, margin % |

Har upload pe **niche ka naam** likhna zaroori hai (jaise "Bifold Wallet", "Glass Bottle") — isse saari niches ka data alag-alag track hota hai, ek hi dashboard mein.

## Column detection

Parsers (`parsers.py`) column headers ko **fuzzy match** karte hain — matlab agar Helium 10 ne apne export format mein thoda naam badla ("Search Volume" vs "SearchVolume"), tab bhi kaam karega. Agar koi file bilkul naya format ho aur detect na ho, error message exact bata dega ke kaunsa column nahi mila.

## Files

```
app.py                          — home page
db.py                           — SQLite storage layer
parsers.py                      — file parsing/normalization logic
pages/1_Keyword_Research.py
pages/2_Rank_Tracking.py
pages/3_Market_Analysis.py
pages/4_PPC_Daily_Performance.py
pages/5_Search_Term_Report.py
pages/6_Profit_Calculator.py
requirements.txt
```
