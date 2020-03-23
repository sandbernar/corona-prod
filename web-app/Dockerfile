# FROM python:3.6

# ENV FLASK_APP run.py

# COPY requirements.txt ./
# RUN pip install -r requirements.txt
# COPY config.py run.py gunicorn-cfg.py ./

# CMD ["gunicorn", "--config", "gunicorn-cfg.py", "run:app"]

FROM tiangolo/uwsgi-nginx-flask:python3.7

RUN apt-get install curl autoconf automake libtool pkg-config
RUN git clone https://github.com/openvenues/libpostal
RUN mkdir /postal
RUN cd libpostal && ./bootstrap.sh && ./configure --datadir=/postal && make && make install && ldconfig

COPY requirements.txt ./
RUN pip install -r requirements.txt

ENV LISTEN_PORT 5005
EXPOSE 5005
