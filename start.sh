export PYTHONPATH=$(pwd):$PYTHONPATH
[ -z "$DB_NAME" ] && export DB_NAME="tattleviralspiral"
[ -z "$DB_HOST" ] && export DB_HOST="127.0.0.1"
[ -z "$DB_PORT" ] && export DB_PORT=3306
[ -z "$DB_USERNAME" ] && export DB_USERNAME="root"
[ -z "$DB_PASSWORD" ] && export DB_PASSWORD="helloworld"
pipenv run python main_loop/websocket.py
