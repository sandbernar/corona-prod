FROM tiangolo/uwsgi-nginx-flask:python3.7

COPY requirements.txt ./
RUN pip install --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --trusted-host pypi.org  -r requirements.txt

ENV LISTEN_PORT 5005
EXPOSE 5005

ENV STATIC_URL /static
ENV STATIC_PATH /app/app/main/static
