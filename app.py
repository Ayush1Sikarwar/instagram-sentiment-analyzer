import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json

from data_collector import data_collector
from sentiment_analyzer import batch_analyze
from utils import color_for, build_summary_json, top_words, orient_xticks

# ---------------------------- Page and CSS ----------------------------
st.set_page_config(page_title="Instagram Sentiment Analyzer", page_icon="📸", layout="wide")

st.markdown("""
<style>
    html, body, [class*="css"]  { font-size: 19px; line-height: 1.55; }
    .stButton>button, .stDownloadButton>button {
        font-size: 18px !important; border-radius: 10px !important;
        cursor: pointer !important; transition: transform .08s ease, filter .2s ease, box-shadow .2s ease;
        box-shadow: 0 0 0 rgba(0,0,0,0);
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        transform: translateY(-1px); filter: brightness(1.06); box-shadow: 0 6px 16px rgba(0,0,0,0.25);
    }
    .stSlider>div>div>div>div { height: 0.55rem !important; }
    @keyframes glowPulse { 0%{text-shadow:0 0 0 rgba(255,120,120,0);} 50%{text-shadow:0 0 12px rgba(255,120,120,.25),0 0 18px rgba(120,160,255,.25);} 100%{text-shadow:0 0 0 rgba(255,120,120,0);} }
    .big-title { font-size: 44px; font-weight: 800; color: #e7e7e7; letter-spacing: .2px; animation: glowPulse 2.4s ease-in-out infinite; display: inline-block; }
    .intro { font-size: 17px; color:#cfcfcf; background: rgba(100,140,180,0.15); padding:10px 14px; border-radius:10px; margin-bottom: 18px; }
    .metric {border-radius: 12px; padding: 16px 18px; color: #fff; background: #2b2b2b; font-size: 18px;}
    .side-note {font-size: 13px; color:#bfbfbf;}
    section.main > div:has(.element-container) .stAlert { margin-top: 8px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">📸 Instagram Sentiment Analyzer</div>', unsafe_allow_html=True)
st.markdown('<div class="intro">Analyze by hashtag, paste Instagram post URLs, or drop your own comments — instant multilingual sentiment with interactive visuals and exports.</div>', unsafe_allow_html=True)

# ---------------------------- Session State ----------------------------
if "sessions" not in st.session_state:
    st.session_state["sessions"] = {}
if "current_df" not in st.session_state:
    st.session_state["current_df"] = None
if "current_meta" not in st.session_state:
    st.session_state["current_meta"] = {"source": None, "label": None, "mode": None}

# ---------------------------- Sidebar (inputs shown before submit) ----------------------------
with st.sidebar:
    st.header("Controls")

    source_type = st.radio("Analyze by", ["Hashtag", "Post URLs", "Paste Comments"], horizontal=True)

    include_comments = True
    analyze_mode = "Both"
    label = None

    hashtag = None
    limit = 50
    url_text = ""
    pasted = ""

    if source_type == "Hashtag":
        hashtag = st.selectbox("Hashtag", options=data_collector.get_available_hashtags(), index=0)
        # Raise limit to 1000
        limit = st.slider("Number of posts", 5, 1000, 100, 5)
        include_comments = st.checkbox("Include comments", value=True)
        analyze_mode = st.radio("Analyze", ["Captions", "Comments", "Both"], horizontal=True)

    elif source_type == "Post URLs":
        st.write("Paste Instagram post URLs (one per line). Formats accepted:")
        st.markdown('<div class="side-note">https://www.instagram.com/p/XXXXXXXXXX/ • https://www.instagram.com/reel/XXXXXXXXXX/ • https://m.instagram.com/p/... • l.instagram.com/?u=https%3A%2F%2Fwww.instagram.com%2F...</div>', unsafe_allow_html=True)
        url_text = st.text_area("Post URLs", placeholder="https://www.instagram.com/p/XXXXXXXXXX/\nhttps://www.instagram.com/reel/XXXXXXXXXX/", height=180)
        include_comments = st.checkbox("Include comments", value=True)
        analyze_mode = st.radio("Analyze", ["Captions", "Comments", "Both"], horizontal=True)

    else:  # Paste Comments
        pasted = st.text_area("Paste comments (one per line, Hindi/English/Hinglish supported)",
                              placeholder="Kya mast reel hai yrr! 🔥\nNot impressed tbh\nयह बहुत अच्छा है!\nPretty decent but could be better.", height=220)
        analyze_mode = "Comments"

    run = st.button("Start Analysis", use_container_width=True)

# ---------------------------- Run or Reuse ----------------------------
if run:
    if source_type == "Hashtag":
        posts, comments = data_collector.collect_hashtag_data(hashtag, limit, include_comments=include_comments)
        label = f"#{hashtag}"
        if analyze_mode == "Captions": items = posts
        elif analyze_mode == "Comments": items = comments
        else: items = posts + comments

    elif source_type == "Post URLs":
        urls = [u.strip() for u in (url_text or "").splitlines() if u.strip()]
        if not urls:
            st.error("Please paste at least one Instagram post URL.")
            st.stop()
        shortcodes = [data_collector.extract_shortcode(u) for u in urls]
        valid = [c for c in shortcodes if c]
        if not valid:
            st.error("Couldn’t extract any valid post IDs. Each URL should look like https://www.instagram.com/p/XXXXXXXXXX/ or /reel/XXXXXXXXXX/. Subdomains m./www. and query params are fine.")
            st.stop()
        st.info(f"Detected {len(valid)} valid post link(s).")
        posts, comments = data_collector.collect_from_urls(urls, include_comments=include_comments)
        label = f"{len(posts)} URL post(s)"
        if analyze_mode == "Captions": items = posts
        elif analyze_mode == "Comments": items = comments
        else: items = posts + comments

    else:  # Paste Comments
        lines = [ln for ln in (pasted or "").splitlines() if ln.strip()]
        if not lines:
            st.error("Please paste at least one comment line.")
            st.stop()
        # Cap extremely large pastes for responsiveness
        if len(lines) > 1000:
            lines = lines[:1000]
            st.warning("Truncated to first 1000 comments for performance.")
        _, comments = data_collector.build_from_pasted_comments(lines)
        label = f"{len(comments)} pasted comment(s)"
        items = comments

    if not items:
        st.warning("No items to analyze. Try different inputs.")
        st.stop()

    # Analyze in batches for stability on large inputs
    with st.spinner("Analyzing sentiment..."):
        chunk = 400
        results_all = []
        for i in range(0, len(items), chunk):
            results_all.extend(batch_analyze(items[i:i+chunk]))

    df = pd.DataFrame(results_all)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Accuracy tweak: recalibrate final label with VADER/TextBlob ensemble
    def _refine(row):
        comp = float(row.get("vader_compound", 0))
        tb = float(row.get("textblob_polarity", 0))
        neutral_band = 0.06
        w = 0.6*comp + 0.4*tb
        if w >= neutral_band: return "Positive"
        if w <= -neutral_band: return "Negative"
        return "Neutral"
    df["sentiment"] = df.apply(_refine, axis=1)
    df["confidence"] = (df["vader_compound"].abs() * 0.6 + df["textblob_polarity"].abs() * 0.4).round(3)

    st.session_state["current_df"] = df.copy()
    st.session_state["current_meta"] = {"source": source_type, "label": label, "mode": analyze_mode}

# ---------------------------- Visualize ----------------------------
if st.session_state["current_df"] is not None:
    df = st.session_state["current_df"].copy()
    meta = st.session_state["current_meta"]
    label = meta["label"]
    analyze_mode = meta["mode"]

    st.success(f"Analyzed {len(df)} items • Source: {label} • Mode: {analyze_mode}")

    session_key = f"{meta['source']}|{label}|{analyze_mode}"
    st.session_state["sessions"][session_key] = df.copy()

    cmetric = st.columns(4)
    with cmetric[0]: st.markdown(f'<div class="metric">Total Items<br><span style="font-size:26px;font-weight:800;">{len(df)}</span></div>', unsafe_allow_html=True)
    with cmetric[1]:
        pct_pos = (df["sentiment"].eq("Positive").mean()*100) if len(df) else 0
        st.markdown(f'<div class="metric">Positive %<br><span style="font-size:26px;font-weight:800;">{pct_pos:.1f}%</span></div>', unsafe_allow_html=True)
    with cmetric[2]:
        pct_neg = (df["sentiment"].eq("Negative").mean()*100) if len(df) else 0
        st.markdown(f'<div class="metric">Negative %<br><span style="font-size:26px;font-weight:800;">{pct_neg:.1f}%</span></div>', unsafe_allow_html=True)
    with cmetric[3]:
        avgc = df["confidence"].mean() if len(df) else 0
        st.markdown(f'<div class="metric">Avg Confidence<br><span style="font-size:26px;font-weight:800;">{avgc:.2f}</span></div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        counts = df["sentiment"].value_counts()
        fig = px.pie(values=counts.values, names=counts.index, title="Sentiment Distribution",
                     color=counts.index, color_discrete_map={s: color_for(s) for s in counts.index})
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        lang_counts = df["language"].replace({"en": "EN", "hi": "HI", "mixed": "Mixed"})
        lang_ct = lang_counts.value_counts()
        fig2 = px.bar(x=lang_ct.index, y=lang_ct.values, title="Language Distribution")
        fig2.update_traces(marker_color=["#4c78a8"] * len(lang_ct))
        fig2.update_layout(yaxis_title="Count", xaxis_title="Language")
        fig2 = orient_xticks(fig2, angle=0)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### ⏱️ Sentiment Over Time")
    dft = df.sort_values("timestamp").copy()
    dft["sentiment_score"] = dft["sentiment"].map({"Positive": 1, "Neutral": 0, "Negative": -1})
    max_items = int(min(400, max(1, len(dft))))  # higher smoothing ceiling
    roll = st.slider("Smoothing window (items)", 1, max_items, min(25, max_items))
    dft["smoothed"] = dft["sentiment_score"].rolling(roll, min_periods=1).mean()
    figt = go.Figure()
    figt.add_scatter(x=dft["timestamp"], y=dft["smoothed"], mode="lines+markers",
                     name="Trend", line=dict(color="#6aa0ff", width=3), marker=dict(size=6))
    figt.update_layout(template="plotly_dark", height=380, yaxis_title="Sentiment (-1..1)", xaxis_title="Time")
    st.plotly_chart(figt, use_container_width=True)

    st.markdown("### ☁️ Top Words")
    cw1, cw2 = st.columns(2)
    pos_words = top_words(df.loc[df["sentiment"] == "Positive", "clean_text"], limit=30, keep_emojis=True)
    neg_words = top_words(df.loc[df["sentiment"] == "Negative", "clean_text"], limit=30, keep_emojis=True)
    with cw1:
        figpw = px.bar(x=list(pos_words.keys())[:30], y=list(pos_words.values())[:30],
                       title="Positive Words", color=list(pos_words.values())[:30], color_continuous_scale="Greens")
        figpw = orient_xticks(figpw, angle=-45)
        st.plotly_chart(figpw, use_container_width=True)
    with cw2:
        fignw = px.bar(x=list(neg_words.keys())[:30], y=list(neg_words.values())[:30],
                       title="Negative Words", color=list(neg_words.values())[:30], color_continuous_scale="Reds")
        fignw = orient_xticks(fignw, angle=-45)
        st.plotly_chart(fignw, use_container_width=True)

    st.markdown("### 🌐 Translations")
    with st.expander("Show translations for non-English items"):
        non_en = df[df["language"] != "en"]
        if len(non_en) == 0:
            st.info("No non-English items detected.")
        else:
            for _, r in non_en.iterrows():
                st.markdown(f"**{r['sentiment']} ({r['confidence']:.0%})** — {r['text']}")
                if r.get("translated_text"):
                    st.caption(f"Translation: {r['translated_text']}")
                st.divider()

    st.markdown("### 📥 Export")
    summary = build_summary_json(df, label)
    st.download_button("Download Summary JSON", data=json.dumps(summary, indent=2),
                       file_name=f"summary_{label.replace('#','')}.json", mime="application/json")

    st.markdown("### 🔄 Compare Saved Sessions")
    if st.session_state["sessions"]:
        keys = list(st.session_state["sessions"].keys())
        if len(keys) >= 2:
            k1 = st.selectbox("Session A", keys, index=0, key="cmp_a")
            k2 = st.selectbox("Session B", keys, index=1, key="cmp_b")
            if k1 != k2:
                dfa = st.session_state["sessions"][k1]
                dfb = st.session_state["sessions"][k2]
                comp = pd.DataFrame({
                    "Session": [k1, k2],
                    "Total": [len(dfa), len(dfb)],
                    "Positive%": [
                        round(dfa["sentiment"].eq("Positive").mean() * 100, 1),
                        round(dfb["sentiment"].eq("Positive").mean() * 100, 1)
                    ],
                    "Negative%": [
                        round(dfa["sentiment"].eq("Negative").mean() * 100, 1),
                        round(dfb["sentiment"].eq("Negative").mean() * 100, 1)
                    ],
                    "AvgConf": [round(dfa["confidence"].mean(), 2), round(dfb["confidence"].mean(), 2)]
                })
                st.dataframe(comp, use_container_width=True)
        else:
            st.info("Run at least two analyses to compare sessions.")
else:
    st.info("Use the sidebar to select a mode, enter input, and click Start Analysis. Results will persist while you tweak sliders.")
