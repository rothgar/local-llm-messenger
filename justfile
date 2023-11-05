serve:
  cd app && uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --env-file .env \
    --reload \
    --reload-include default.ai \
    --log-config=log_conf.yaml
