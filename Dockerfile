FROM python:3.9.5-slim

WORKDIR /app

RUN apt-get update \
&& apt-get -y install g++ libpq-dev gcc unixodbc unixodbc-dev default-libmysqlclient-dev python3-dev
&& apt-get -y install vim tmux # Debugging

# COPY Pipfile /app/
# COPY Pipfile.lock /app/
# COPY activate_env.sh /app/
COPY . /app/

RUN pip install flask flask-socketio peewee psycopg2 pyparsing connexion six peewee-db-evolve mysql

CMD ["tail", "-f", "/dev/null"]
