import os, requests, streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Test Sentiment API")
st.title("Test Sentiment API")

txt = st.text_area("Entrez un texte (tweet)", height=140, placeholder="Votre texte ici…")
if st.button("Prédire"):
    if not txt.strip():
        st.warning("Merci d'entrer un texte.")
    else:
        with st.spinner("Prédiction en cours…"):
            r = requests.post(f"{API_URL}/predict", json={"text": txt})
        if r.ok:
            out = r.json()
            st.markdown(f"**Sentiment :** `{out['sentiment']}`  |  **score**: {out['score']:.3f}  |  **latence**: {out['latency_ms']:.1f} ms")
            valid = st.radio("La prédiction vous paraît-elle pertinente ?", ["Oui", "Non"], horizontal=True, index=0)
            if st.button("Envoyer le feedback"):
                fb = {
                    "text": txt,
                    "predicted": out["sentiment"],
                    "score": out["score"],
                    "is_valid": (valid == "Oui"),
                    "model_version": out["model_version"]
                }
                fr = requests.post(f"{API_URL}/feedback", json=fb)
                st.success("Feedback envoyé. Merci !")
        else:
            st.error(f"Erreur API: {r.status_code} - {r.text}")
