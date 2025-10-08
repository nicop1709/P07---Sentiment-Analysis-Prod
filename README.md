# put in .env :
APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=...;IngestionEndpoint=..."

uvicorn api.app:app --reload --host 127.0.0.1 --port 8000
python -m spacy download en_core_web_sm 
