echo "Starting viral spiral backend"
source activate_env.sh
pipenv run python main_loop/websocket.py
