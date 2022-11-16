echo "Starting viral spiral backend"
source activate_env.sh
# pipenv run python main_loop/websocket.py
pipenv run gunicorn -b 0.0.0.0:5000 -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 5 main_loop.websocket:app
