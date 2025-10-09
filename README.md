# put in .env :
APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=...;IngestionEndpoint=..."
AZUREAPPSERVICE_PUBLISHPROFILE=""
MODEL_DIR="./models/savedmodel"
MODEL_VERSION="dev"

## Local

python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m spacy download en_core_web_sm
uvicorn api.app:app --reload

## Tests
pytest -q

## CI/CD
- CI: lint & tests sur chaque push/PR
- CD: déploiement auto sur Azure App Service (branche main)
