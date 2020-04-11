FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7

COPY requirements.txt .

RUN pip install psycopg2

RUN pip install -r requirements.txt
