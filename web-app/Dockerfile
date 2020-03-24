# FROM python:3.6

# ENV FLASK_APP run.py

# COPY requirements.txt ./
# RUN pip install -r requirements.txt
# COPY config.py run.py gunicorn-cfg.py ./

# CMD ["gunicorn", "--config", "gunicorn-cfg.py", "run:app"]

FROM tiangolo/uwsgi-nginx-flask:python3.7

COPY requirements.txt ./
RUN pip install -r requirements.txt

ENV LISTEN_PORT 5005
ENV STATIC_PATH /app/base/static
EXPOSE 5005
