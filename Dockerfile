FROM python:3.9.5-slim

WORKDIR /app

RUN apt-get update \
&& apt-get -y install g++ libpq-dev gcc unixodbc unixodbc-dev default-libmysqlclient-dev python3-dev \
&& apt-get -y install vim tmux curl wget net-tools # Debugging

COPY . /app/

RUN pip install pipenv
RUN pipenv sync

RUN export PYTHONPATH=./

EXPOSE 5000

# RUN pip install flask flask-socketio peewee psycopg2 pyparsing connexion six peewee-db-evolve mysql

# CMD ["tail", "-f", "/dev/null"]
CMD ["pipenv", "run", "bash", "start.sh", "-f", "/dev/null"]
