# app_streamlit.py (extrait) — remplace ton bloc central par ceci

import os, time, requests
import streamlit as st

DEFAULT_API_BASE = os.getenv("API_BASE_URL", "https://p07-sentiment-api-eqf8h8akbeameqax.westeurope-01.azurewebsites.net").rstrip("/")
st.set_page_config(page_title="P07 Sentiment", page_icon="💬", layout="centered")

# ---- state ----
if "last_pred" not in st.session_state:
    st.session_state.last_pred = None  # dict: {text, sentiment, score, model_version, latency_ms}

with st.sidebar:
    st.header("⚙️ Paramètres")
    #api_base = st.text_input("API base URL", DEFAULT_API_BASE).rstrip("/")
    api_base =  st.selectbox("API base URL",[DEFAULT_API_BASE,"http://127.0.0.1:8000"]).rstrip("/")
timeout_s = 20
st.title("💬 Analyse de sentiment (P07)")
txt = st.text_area("Texte à analyser", height=160, placeholder="Tape ou colle ton texte ici…")


def _url(path: str) -> str:
    return f"{api_base}{path if path.startswith('/') else '/' + path}"

@st.cache_data(show_spinner=False, ttl=60)
def predict_api(text: str, timeout: float = 8.0):
    last_err = None
    for attempt in range(3):
        try:
            r = requests.post(_url("/predict"), json={"text": text}, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            last_err = f"HTTP {r.status_code}: {r.text[:200]}"
        except requests.RequestException as e:
            last_err = str(e)
        time.sleep(0.3 * (attempt + 1))
    raise RuntimeError(f"Appel API /predict en échec: {last_err}")

def send_feedback(text: str, predicted: str, score: float, is_valid: bool, model_version=None):
    try:
        r = requests.post(_url("/feedback"), json={
            "text": text,
            "predicted": predicted,
            "score": float(score),
            "is_valid": bool(is_valid),
            "model_version": model_version
        }, timeout=5)
        return r.ok
    except requests.RequestException:
        return False

# ---- actions ----
col_btn = st.columns([1,1,2])
go = col_btn[0].button("🔎 Analyser", type="primary", use_container_width=True, key="analyze")
reset = col_btn[1].button("↺ Reset", use_container_width=True, key="reset")

if reset:
    st.cache_data.clear()
    st.session_state.last_pred = None
    st.toast("Réinitialisé ✅")

if go:
    if not txt.strip():
        st.warning("Ajoute du texte à analyser.")
    else:
        with st.spinner("Appel API…"):
            try:
                res = predict_api(txt.strip(), timeout=timeout_s)
            except Exception as e:
                st.error(f"Échec d'appel à l’API : {e}")
            else:
                # mémorise le dernier résultat pour les boutons de feedback
                st.session_state.last_pred = {
                    "text": txt.strip(),
                    "sentiment": res.get("sentiment"),
                    "score": float(res.get("score", 0.0)),
                    "model_version": res.get("model_version", "?"),
                    "latency_ms": float(res.get("latency_ms", 0.0)),
                }

# ---- rendu du dernier résultat + feedback (persiste après re-run) ----
if st.session_state.last_pred:
    lp = st.session_state.last_pred
    if lp["score"]>0.5:
        confiance = lp["score"]
    else:
        confiance = 1-lp["score"]
    pos = (lp["sentiment"] == "positive")

    st.info("😊 **Positif**" if pos else "☹️ **Négatif**")
    st.metric("Score (confiance)", f'{confiance:.1%}')
    st.caption(f'Modèle: {lp["model_version"]} • Latence: {lp["latency_ms"]:.0f} ms')

    fb_col = st.columns(2)
    if fb_col[0].button("👍 Correct", use_container_width=True, key="fb_ok"):
        ok = send_feedback(lp["text"], lp["sentiment"], lp["score"], True, lp["model_version"])
        st.toast("Feedback envoyé ✅" if ok else "Échec envoi feedback ❌")
    if fb_col[1].button("👎 Incorrect", use_container_width=True, key="fb_ko"):
        ok = send_feedback(lp["text"], lp["sentiment"], lp["score"], False, lp["model_version"])
        st.toast("Feedback envoyé ✅" if ok else "Échec envoi feedback ❌")
