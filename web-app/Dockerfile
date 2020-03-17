FROM python:3.6

ENV FLASK_APP run.py

COPY run.py gunicorn-cfg.py requirements.txt config.py ./
RUN pip install -r requirements.txt

CMD ["gunicorn", "--config", "gunicorn-cfg.py", "run:app"]
