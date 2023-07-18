FROM python:3.11-slim-buster

WORKDIR /app

COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

COPY src /app
COPY data/layers /app/data/layers
COPY data/fallacies.json /app/data/fallacies.json
COPY scripts/run_bot.py /app/entrypoint.py
COPY configs /app/configs

CMD python entrypoint.py
