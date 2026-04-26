"""Streamlit UI — blue/black theme, no emojis, AI song fetch."""

import os, sys
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from recommender import load_songs
from main import AgenticRecommendationWorkflow, USER_PROFILES, PLATFORM_LABELS, ALLOWED_RANKING_MODES
from ai_songs import fetch_via_gemini

st.set_page_config(page_title="Music Recommender", page_icon="M", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
*, html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp {
  background: #000;
  background-image:
    radial-gradient(ellipse 80% 55% at 50% -5%, rgba(0,90,255,0.38) 0%, transparent 68%),
    radial-gradient(ellipse 45% 35% at 92% 85%, rgba(0,150,255,0.2) 0%, transparent 55%);
}

section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #04051a 0%, #070a28 100%);
  border-right: 1px solid rgba(0,130,255,0.22);
}
section[data-testid="stSidebar"] * { color: #d8e8ff !important; }
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] b { color: #90bfff !important; }

section[data-testid="stSidebar"] .stButton > button {
  background: linear-gradient(135deg, #0055ff, #009fff) !important;
  color: #fff !important; border: none !important;
  border-radius: 10px !important; font-weight: 700 !important;
  letter-spacing: 0.04em !important;
  box-shadow: 0 4px 22px rgba(0,110,255,0.45) !important;
  transition: all 0.2s !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  box-shadow: 0 6px 32px rgba(0,160,255,0.65) !important;
  transform: translateY(-1px) !important;
}

.hero { text-align:center; padding:2.8rem 1rem 2rem; }
.hero h1 {
  font-size:3rem; font-weight:800; letter-spacing:-0.02em;
  background: linear-gradient(90deg, #4d9fff, #79c2ff, #00e0ff);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin:0 0 0.4rem;
}
.hero p { color:rgba(200,225,255,0.6); font-size:1rem; margin:0; }

.metric-row { display:flex; gap:0.8rem; flex-wrap:wrap; margin-bottom:1.8rem; }
.metric-card {
  flex:1; min-width:110px;
  background:linear-gradient(135deg,rgba(0,60,190,0.2),rgba(0,20,90,0.4));
  border:1px solid rgba(0,130,255,0.3); border-radius:12px;
  padding:1rem; text-align:center;
}
.metric-card .val { font-size:1.6rem; font-weight:700; color:#7dc4ff; }
.metric-card .lbl { font-size:0.7rem; color:rgba(170,210,255,0.7); margin-top:0.2rem; text-transform:uppercase; letter-spacing:0.06em; }

.song-card {
  background:linear-gradient(135deg,rgba(0,35,110,0.45),rgba(0,12,50,0.75));
  border:1px solid rgba(0,130,255,0.22); border-radius:16px;
  padding:1.4rem 1.6rem; margin-bottom:1rem; position:relative; overflow:hidden;
  transition:transform 0.2s, box-shadow 0.2s, border-color 0.2s;
}
.song-card:hover {
  transform:translateY(-3px);
  box-shadow:0 14px 50px rgba(0,90,255,0.28);
  border-color:rgba(0,170,255,0.5);
}
.song-card::before {
  content:''; position:absolute; top:0; left:0; right:0; height:3px;
  background:linear-gradient(90deg,#0055ff,#00d4ff);
}
.rank-badge {
  display:inline-flex; align-items:center; justify-content:center;
  width:2.1rem; height:2.1rem; border-radius:50%;
  background:linear-gradient(135deg,#0055ff,#00aaff);
  color:#fff; font-weight:800; font-size:0.82rem;
  margin-right:0.9rem; flex-shrink:0;
  box-shadow:0 2px 14px rgba(0,110,255,0.55);
}
.song-title { font-size:1.1rem; font-weight:700; color:#e8f4ff; }
.song-artist { color:rgba(170,210,255,0.75); font-size:0.88rem; margin-top:0.15rem; }
.score-pill {
  background:linear-gradient(90deg,rgba(0,85,255,0.22),rgba(0,180,255,0.22));
  border:1px solid rgba(0,150,255,0.45); border-radius:999px;
  padding:0.2rem 0.85rem; font-size:0.78rem; font-weight:700; color:#7dd8ff;
}
.tag-chip {
  display:inline-block;
  background:rgba(0,90,255,0.18); border:1px solid rgba(0,110,255,0.28);
  border-radius:999px; padding:0.12rem 0.58rem;
  font-size:0.7rem; color:rgba(170,215,255,0.9); margin:0.15rem 0.2rem 0 0;
}
.score-bar-bg { background:rgba(255,255,255,0.07); border-radius:999px; height:5px; margin-top:8px; }
.score-bar-fill { background:linear-gradient(90deg,#0055ff,#00d4ff); height:5px; border-radius:999px; }
.reason-text { font-size:0.8rem; color:rgba(160,200,255,0.8); margin-top:0.7rem; line-height:1.6; }

.platform-btn {
  display:inline-block; padding:0.32rem 0.88rem; border-radius:8px;
  font-size:0.76rem; font-weight:600; text-decoration:none !important;
  margin:0.25rem 0.3rem 0 0; transition:opacity 0.15s, transform 0.12s;
}
.platform-btn:hover { opacity:0.82; transform:translateY(-1px); }
.btn-spotify    { background:#1DB954; color:#000 !important; }
.btn-youtube    { background:#FF0000; color:#fff !important; }
.btn-apple      { background:#fc3c44; color:#fff !important; }
.btn-deezer     { background:#A238FF; color:#fff !important; }
.btn-soundcloud { background:#ff5500; color:#fff !important; }

.section-title {
  font-size:1.15rem; font-weight:700; color:#79c2ff;
  letter-spacing:-0.01em; margin:1.6rem 0 1rem;
}

.agent-box {
  background:linear-gradient(135deg,rgba(0,35,110,0.3),rgba(0,12,60,0.55));
  border:1px solid rgba(0,110,255,0.22); border-radius:12px;
  padding:1.2rem 1.5rem; margin-top:0.5rem;
}
.agent-box h4 { color:#79c2ff !important; margin:0 0 0.6rem; font-size:0.82rem; text-transform:uppercase; letter-spacing:0.08em; }
.agent-box p  { color:rgba(200,225,255,0.85) !important; font-size:0.85rem; line-height:1.65; margin:0; }

.pref-section {
  background:linear-gradient(135deg,rgba(0,35,130,0.18),rgba(0,12,65,0.4));
  border:1px solid rgba(0,110,255,0.2); border-radius:12px;
  padding:1.4rem 1.6rem; margin-top:1rem;
}

.empty-state { text-align:center; padding:6rem 2rem; }
.empty-state .icon { font-size:4rem; opacity:0.25; }
.empty-state p { color:rgba(160,200,255,0.5); font-size:1.05rem; margin-top:1rem; }

.stMetric label { color:rgba(170,210,255,0.7) !important; }
.stMetric [data-testid="stMetricValue"] { color:#7dc4ff !important; font-weight:700 !important; }
#MainMenu, footer, header { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
PLATFORM_BTN_CLASS = {"spotify":"btn-spotify","youtube_music":"btn-youtube","apple_music":"btn-apple","deezer":"btn-deezer","soundcloud":"btn-soundcloud"}
PLATFORM_ICONS     = {"spotify":"S","youtube_music":"YT","apple_music":"A","deezer":"D","soundcloud":"SC"}
GEMINI_MODELS      = ["gemini-3-flash-preview","gemini-3.1-flash-lite-preview","gemini-3.1-pro-preview","gemini-2.5-flash-lite","gemini-2.0-flash-lite-001"]
ALL_GENRES         = ["pop","rock","lofi","rap","hip-hop","jazz","electronic","indie pop","indie","synthwave","ambient","rnb","classical","metal","country","latin","funk pop","new wave"]
ALL_MOODS          = sorted({"happy","chill","intense","focused","melancholic","euphoric","groovy","dark","relaxed","energetic","moody","playful","reflective","determined"})
ALL_DECADES        = [1970,1980,1990,2000,2010,2020]
ALL_TAGS           = ["happy","chill","high_energy","low_energy","dance","uplifting","acoustic","lyrical","moody","intense","dark","groovy","focused"]
PROFILE_LABELS     = {"alex_pop_happy":"Alex — Pop / Happy","maya_lofi_chill":"Maya — Lofi / Chill","ryan_rap_intense":"Ryan — Rap / Intense","__custom__":"Custom Personality"}

@st.cache_data(show_spinner=False)
def get_songs():
    return load_songs(str(ROOT / "data" / "songs.csv"))

def invalidate_songs():
    get_songs.clear()

def score_bar_html(score:float, max_score:float=1.5)->str:
    pct = min(int(score/max_score*100),100)
    return f'<div class="score-bar-bg"><div class="score-bar-fill" style="width:{pct}%"></div></div>'

def render_song_card(rank:int, item:dict)->None:
    song  = item["song"]
    score = item["score"]
    links = item.get("links",{})
    tags  = [t.strip() for t in song.get("detailed_mood_tags","").split("|") if t.strip()]
    tag_html  = "".join(f'<span class="tag-chip">{t}</span>' for t in tags[:6])
    link_html = "".join(
        f'<a href="{url}" target="_blank" class="platform-btn {PLATFORM_BTN_CLASS.get(p,"")}">'
        f'{PLATFORM_ICONS.get(p,p)} {PLATFORM_LABELS.get(p,p) if p not in PLATFORM_LABELS else PLATFORM_LABELS[p]}</a>'
        for p,url in links.items()
    )
    platform_names = {"spotify":"Spotify","youtube_music":"YouTube Music","apple_music":"Apple Music","deezer":"Deezer","soundcloud":"SoundCloud"}
    link_html = "".join(
        f'<a href="{url}" target="_blank" class="platform-btn {PLATFORM_BTN_CLASS.get(p,"")}">'
        f'{platform_names.get(p,p)}</a>'
        for p,url in links.items()
    )
    st.markdown(f"""
    <div class="song-card">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:0.5rem;">
        <div style="display:flex;align-items:center;">
          <span class="rank-badge">#{rank}</span>
          <div>
            <div class="song-title">{song['title']}</div>
            <div class="song-artist">{song['artist']} &nbsp;&middot;&nbsp; <span style="color:#50aaff">{song.get('genre','')}</span></div>
          </div>
        </div>
        <span class="score-pill">Score: {score:.3f}</span>
      </div>
      {score_bar_html(score)}
      <div style="margin-top:0.8rem;">{tag_html}</div>
      <div class="reason-text">{item['explanation']}</div>
      <div style="margin-top:0.9rem;">{link_html}</div>
    </div>""", unsafe_allow_html=True)

def render_agent_panel(report)->None:
    p,c = report.planner, report.checker
    conf   = c.get("confidence",0.0)
    quality= "Pass" if c.get("quality_pass",True) else "Fail"
    gemini = "Active" if report.used_gemini else "Fallback"
    st.markdown('<div class="section-title">Agent Run Report</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    cols[0].metric("Gemini",    gemini)
    cols[1].metric("Quality",   quality)
    cols[2].metric("Confidence",f"{conf:.0%}")
    cols[3].metric("Retries",   report.retries)
    c1,c2 = st.columns(2)
    with c1:
        st.markdown(f"""<div class="agent-box"><h4>Planner</h4>
<p><b>Mode:</b> {p.get('selected_mode','—')}<br>
<b>Top-K:</b> {p.get('selected_top_k','—')}<br>
<b>Penalty:</b> {p.get('selected_artist_penalty','—')}<br>
<b>Reason:</b> {p.get('reason','—')}</p></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="agent-box"><h4>Checker</h4>
<p><b>Retry mode:</b> {c.get('retry_mode','—')}<br>
<b>Retry penalty:</b> {c.get('retry_artist_penalty','—')}<br>
<b>Reason:</b> {c.get('reason','—')}</p></div>""", unsafe_allow_html=True)

def render_chart(items:list, user_prefs:dict)->None:
    try:
        import pandas as pd
        feats=["energy","valence","danceability","acousticness","instrumentalness","liveness","speechiness"]
        rows=[{"Song":(s:=i["song"])["title"][:16],**{f:float(s.get(f,0)) for f in feats}} for i in items[:5]]
        rows.append({"Song":"Target","energy":user_prefs.get("target_energy",0.5),"valence":user_prefs.get("target_valence",0.6),
            "danceability":user_prefs.get("target_danceability",0.6),"acousticness":0.8 if user_prefs.get("likes_acoustic") else 0.2,
            "instrumentalness":user_prefs.get("target_instrumentalness",0.25),"liveness":user_prefs.get("target_liveness",0.45),
            "speechiness":user_prefs.get("target_speechiness",0.25)})
        df=pd.DataFrame(rows).set_index("Song")
        st.markdown('<div class="section-title">Audio Feature Comparison</div>',unsafe_allow_html=True)
        st.bar_chart(df[feats],height=300)
    except Exception:
        pass

def personality_editor()->dict:
    st.markdown('<div class="section-title" style="font-size:1rem;margin-top:0;">Build Your Personality</div>',unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        genre  = st.selectbox("Genre",ALL_GENRES,key="c_genre")
        mood   = st.selectbox("Mood",ALL_MOODS,key="c_mood")
        decade = st.select_slider("Target Era",options=ALL_DECADES,value=2020,key="c_decade")
    with c2:
        energy       = st.slider("Energy",       0.0,1.0,0.70,0.01,key="c_energy")
        valence      = st.slider("Valence",      0.0,1.0,0.65,0.01,key="c_valence")
        danceability = st.slider("Danceability", 0.0,1.0,0.65,0.01,key="c_dance")
    c3,c4=st.columns(2)
    with c3:
        tempo      = st.slider("Tempo (BPM)",  60,200,120,key="c_tempo")
        tempo_tol  = st.slider("Tempo Tolerance",5,50,20,key="c_tol")
        popularity = st.slider("Popularity",   0,100,75,key="c_pop")
    with c4:
        instrumentalness = st.slider("Instrumentalness",0.0,1.0,0.20,0.01,key="c_instr")
        liveness         = st.slider("Liveness",        0.0,1.0,0.50,0.01,key="c_live")
        speechiness      = st.slider("Speechiness",     0.0,1.0,0.10,0.01,key="c_speech")
    likes_acoustic = st.toggle("Likes Acoustic",value=False,key="c_acoustic")
    preferred_tags = st.multiselect("Preferred Tags",ALL_TAGS,default=["happy","dance","uplifting"],key="c_tags")
    return {"favorite_genre":genre,"favorite_mood":mood,"target_energy":energy,"likes_acoustic":likes_acoustic,
            "target_valence":valence,"target_danceability":danceability,"target_tempo_bpm":tempo,
            "tempo_tolerance":tempo_tol,"target_popularity":popularity,"target_release_decade":decade,
            "target_instrumentalness":instrumentalness,"target_liveness":liveness,
            "target_speechiness":speechiness,"preferred_tags":preferred_tags}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Settings")
    st.divider()

    st.markdown("**Profile**")
    profile_choice = st.selectbox("profile",list(PROFILE_LABELS.keys()),
                                  format_func=lambda x:PROFILE_LABELS[x],
                                  label_visibility="collapsed")
    st.divider()
    st.markdown("**Mode**")
    mode           = st.selectbox("mode",["auto"]+sorted(ALLOWED_RANKING_MODES),label_visibility="collapsed")
    top_k          = st.slider("Recommendations",1,10,5)
    artist_penalty = st.slider("Artist Diversity Penalty",0.0,0.3,0.06,0.01)
    st.divider()
    st.markdown("**Platforms**")
    chosen_platforms = st.multiselect("platforms",list(PLATFORM_LABELS.keys()),
                                      default=["spotify","youtube_music","apple_music"],
                                      format_func=lambda x:PLATFORM_LABELS[x],
                                      label_visibility="collapsed")
    st.divider()
    st.markdown("**Gemini AI**")
    use_gemini   = st.toggle("Enable Gemini",value=bool(os.getenv("GEMINI_API_KEY")))
    gemini_model = st.selectbox("Model",GEMINI_MODELS,label_visibility="collapsed",disabled=not use_gemini)
    max_retries  = st.slider("Max Retries",1,5,3,disabled=not use_gemini)
    st.divider()
    show_diag  = st.toggle("Agent Diagnostics",value=True)
    show_chart = st.toggle("Feature Chart",value=True)
    st.divider()

    # AI Song Fetch
    st.markdown("**Expand Song Library**")
    fetch_genre = st.selectbox("Genre to fetch",ALL_GENRES,key="fg")
    fetch_mood  = st.selectbox("Mood to fetch", ALL_MOODS, key="fm")
    fetch_count = st.slider("Songs to generate",5,50,15,key="fc")
    fetch_btn   = st.button("Fetch Songs via AI",use_container_width=True, disabled=not use_gemini)
    st.divider()
    run_btn = st.button("Get Recommendations",use_container_width=True,type="primary")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>Music Recommender</h1>
  <p>Agentic AI &mdash; Plan &rarr; Rank &rarr; Check &rarr; Deliver</p>
</div>""", unsafe_allow_html=True)

# ── Custom personality ────────────────────────────────────────────────────────
custom_prefs = None
if profile_choice == "__custom__":
    with st.container():
        st.markdown('<div class="pref-section">',unsafe_allow_html=True)
        custom_prefs = personality_editor()
        st.markdown('</div>',unsafe_allow_html=True)
    st.divider()

# ── Session state ─────────────────────────────────────────────────────────────
for k in ("results","report","prefs_used"):
    if k not in st.session_state:
        st.session_state[k] = None

# ── AI Song Fetch ─────────────────────────────────────────────────────────────
if fetch_btn:
    api_key = os.getenv("GEMINI_API_KEY","")
    if not api_key:
        st.warning("Gemini API key not found in .env")
    else:
        with st.spinner(f"Asking Gemini to generate {fetch_count} {fetch_genre} songs..."):
            try:
                new_rows = fetch_via_gemini(fetch_genre, fetch_mood, fetch_count, api_key, gemini_model)
                invalidate_songs()
                if new_rows:
                    st.success(f"Added {len(new_rows)} new songs to the library!")
                else:
                    st.info("No new songs were added (may already exist).")
            except Exception as exc:
                st.error(f"Fetch failed: {exc}")

# ── Recommend ─────────────────────────────────────────────────────────────────
if run_btn:
    with st.spinner("Agents thinking..."):
        try:
            songs     = get_songs()
            platforms = chosen_platforms or ["spotify","youtube_music","apple_music"]
            workflow  = AgenticRecommendationWorkflow(use_gemini=use_gemini,gemini_model=gemini_model)
            if profile_choice=="__custom__" and custom_prefs:
                USER_PROFILES["__custom__"] = custom_prefs
            results = workflow.run(songs=songs,profile_name=profile_choice,ranking_mode=mode,
                                   top_k=top_k,artist_penalty=artist_penalty,
                                   platforms=platforms,max_retries=max_retries)
            st.session_state.results   = results
            st.session_state.report    = workflow.last_report
            st.session_state.prefs_used= custom_prefs if profile_choice=="__custom__" else USER_PROFILES.get(profile_choice,{})
        except Exception as exc:
            st.error(f"Error: {exc}")

# ── Results ───────────────────────────────────────────────────────────────────
if st.session_state.results:
    results    = st.session_state.results
    report     = st.session_state.report
    prefs_used = st.session_state.prefs_used or {}

    avg   = sum(r["score"] for r in results)/len(results)
    top   = max(r["score"] for r in results)
    total = len(get_songs())
    gnrs  = len({r["song"].get("genre","") for r in results})

    st.markdown(f"""
    <div class="metric-row">
      <div class="metric-card"><div class="val">{len(results)}</div><div class="lbl">Results</div></div>
      <div class="metric-card"><div class="val">{top:.3f}</div><div class="lbl">Top Score</div></div>
      <div class="metric-card"><div class="val">{avg:.3f}</div><div class="lbl">Avg Score</div></div>
      <div class="metric-card"><div class="val">{total}</div><div class="lbl">Library Size</div></div>
      <div class="metric-card"><div class="val">{gnrs}</div><div class="lbl">Genres</div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-title">Your Recommendations</div>',unsafe_allow_html=True)
    for rank,item in enumerate(results,1):
        render_song_card(rank,item)

    if show_chart:
        render_chart(results,prefs_used)
    if show_diag and report:
        st.divider()
        render_agent_panel(report)

else:
    st.markdown("""
    <div class="empty-state">
      <div class="icon">M</div>
      <p>Pick a profile and click <strong>Get Recommendations</strong> to start.</p>
    </div>""", unsafe_allow_html=True)
