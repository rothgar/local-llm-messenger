FROM python:3.12-bookworm

# don't create a venv with pipenv
ENV PIPENV_SYSTEM=1

COPY . /app
WORKDIR /app
RUN pip install pipenv
RUN pipenv install

CMD ["uvicorn", "--host", "0.0.0.0", "main:app"]
# CMD ["python3", "main.py"]
#CMD ["uvicorn", "main:app", "--reload ", "--reload-include", "'default.ai'", "--reload-exclude", "'.git'", "--log-config", "log_conf.yaml"]
