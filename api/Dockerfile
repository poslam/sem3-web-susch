FROM python:3.11-slim-buster

WORKDIR /api

COPY . /api

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-m", "uvicorn", "src.app:app", "--port", "8004", "--host", "0.0.0.0", "--reload"]