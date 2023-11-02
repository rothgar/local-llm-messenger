serve:
  uvicorn main:app --reload --reload-include 'default.ai' --reload-exclude '.git' --log-config=log_conf.yaml
