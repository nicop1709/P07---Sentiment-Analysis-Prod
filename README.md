# P07 - Sentiment Analysis Prod

API FastAPI exposant un modèle de classification de sentiments (anglais) avec suivi via Azure Application Insights et déploiement automatisé sur Azure App Service.

---

## Structure du dépôt

- `api/` : application FastAPI (`api/app.py`) et logique de prédiction.
- `models/` : artefacts de modèles (dossier TensorFlow `savedmodel/` et pipeline `baseline_pipeline.joblib`).
- `streamlit_app.py` : interface Streamlit facultative pour tester l'API.
- `tests/` : tests automatisés (pytest).
- `.github/workflows/` : pipelines CI/CD GitHub Actions (`cicd_docker.yml`, `cd_azure.yml`).
- `Dockerfile`, `requirements*.txt`, etc.

---

## Prérequis

- macOS / Linux / WSL avec Python **3.9** (ou version compatible avec le modèle).
- Git, virtualenv (ou équivalent) et make (facultatif).
- Accès aux secrets Azure (voir section **CI/CD**).

---

## Installation locale

1. Cloner le dépôt :
   ```bash
   git clone <URL_DU_REPO>
   cd P07 - Sentiment Analysis Prod
   ```
2. Créer et activer l’environnement virtuel :
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # sous Windows : .venv\Scripts\activate
   ```
3. Installer les dépendances :
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
   Pour lancer les tests ou contribuer, installer aussi :
   ```bash
   pip install -r requirements-dev.txt
   python -m spacy download en_core_web_sm
   ```

---

## Configuration (.env)

Créer un fichier `.env` à la racine avec :

```
APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=...;IngestionEndpoint=..."
AZUREAPPSERVICE_PUBLISHPROFILE=""           # facultatif en local, requis pour CD GitHub Actions
MODEL_DIR="./models/savedmodel"             # dossier TensorFlow SavedModel
MODEL_JOBLIB_PATH="./models/savedmodel/baseline_pipeline.joblib"  # optionnel, sinon déduit
MODEL_VERSION="dev"
```

> **Important :** `APPLICATIONINSIGHTS_CONNECTION_STRING` est obligatoire même en local (utilisé pour initialiser le tracing). En cas d’absence, l’application ne démarre pas.

---

## Lancement de l’API locale pour test

Après activation de l’environnement virtuel et configuration du `.env` :

```bash
uvicorn api.app:app --reload
```

- API disponible sur `http://127.0.0.1:8000`.
- Documentation interactive Swagger/OpenAPI : `http://127.0.0.1:8000/docs`.
- L’application charge d’abord un modèle TensorFlow (`MODEL_DIR`), sinon un pipeline scikit-learn (`MODEL_JOBLIB_PATH`), sinon un fallback de démonstration.

---

## Documentation de l’API

### `POST /predict`

- **Entrée** (`application/json`) :
  ```json
  {
    "text": "The movie was awesome!"
  }
  ```
- **Réponse** (`200 OK`) :
  ```json
  {
    "sentiment": "positive",
    "score": 0.87,
    "model_version": "dev",
    "latency_ms": 34.21
  }
  ```
- `score` : probabilité que le texte soit positif (0 à 1).
- `sentiment` : `positive` si score ≥ 0.5 sinon `negative`.

**Exemple cURL**
```bash
curl -X POST http://127.0.0.1:8000/predict \
     -H "Content-Type: application/json" \
     -d '{"text": "I love this product!"}'
```

### `POST /feedback`

- **Entrée** :
  ```json
  {
    "text": "The movie was awesome!",
    "predicted": "positive",
    "score": 0.87,
    "is_valid": true,
    "model_version": "dev"
  }
  ```
- **Réponse** :
  ```json
  { "ok": true }
  ```
- Permet de remonter le feedback utilisateur. Un log `WARNING` est émis si `is_valid` est `false` pour faciliter la supervision.

---

## Tests automatisés

```bash
pytest -q
```

Les tests utilisent `requirements-dev.txt` et téléchargent le modèle spaCy `en_core_web_sm`.

---

## Pipelines CI/CD

### `cicd_docker.yml` (branche `master`)
- **CI** (pull request + push) :
  - Installation des dépendances (requirements-dev).
  - Téléchargement du modèle spaCy.
  - Exécution de pytest avec variables d’environnement de test (App Insights, version de modèle `ci`).
- **CD** (push sur `master`) :
  1. Construction d’une image Docker publiée sur GHCR (`ghcr.io/nicop1709/p07---sentiment-analysis-prod`).
  2. Déploiement de cette image sur Azure Web App via `azure/webapps-deploy@v3` (nécessite les secrets `AZURE_WEBAPP_NAME` et `AZUREAPPSERVICE_PUBLISHPROFILE`).

### `cd_azure.yml` (branche `main`)
- Pipeline alternatif déclenché sur chaque push `main`.
- Vérifie l’installation (pip install) puis publie le code sur Azure App Service via le package ZIP.

> **Synthèse :**
> - **Branches de référence** : `master` (flux Docker) et `main` (deployment ZIP).
> - **Secrets requis** : `AZURE_WEBAPP_NAME`, `AZUREAPPSERVICE_PUBLISHPROFILE`, ainsi que la chaîne App Insights (fournie dans les variables d’environnement lors des jobs).

---

## Déploiement manuel (hors CI/CD)

1. S’assurer que l’Azure Web App cible utilise Python compatible et qu’Application Insights est configuré.
2. Soit :
   - Déployer l’image Docker construite localement (`docker build`, `docker push`) puis l’assigner dans Azure.
   - Ou zipper le projet (`zip -r api.zip .`) et utiliser `az webapp deploy --resource-group ... --name ... --src-path api.zip`.
3. Mettre à jour les paramètres d’application sur Azure (variables du `.env`).

---

## Ressources complémentaires

- Documentation FastAPI : https://fastapi.tiangolo.com/
- Application Insights (Azure Monitor) : https://learn.microsoft.com/azure/azure-monitor/app/app-insights-overview
- GitHub Actions pour Azure App Service : https://learn.microsoft.com/azure/app-service/deploy-github-actions
