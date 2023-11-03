serve:
  cd app && uvicorn main:app \
    --env-file .env \
    --reload \
    --reload-include default.ai \
    --log-config=log_conf.yaml
