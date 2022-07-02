# viral-spiral-backend

All command examples are from the repo root

## Running locally

### Prerequisites
- Install postgresql locally
- Create a database called "tattleviralspiral"
    - You can do this by running `psql -U postgres` and then `create databaset tattleviralspiral`
- Install python3 and create a virtualenv
```
python3 -m venv ./venv
```
- Activate the environment
```
source ./activate_env.sh
```
- Install dependencies
```
pip install -r requirements.txt
```
- Initialize the db
```
python setup.py
```

## Run the server
- Activate the environment and run the server
```
source ./activate_env.sh
python main_loop/websocket.py
```
- Make sure you see no errors on the console

## Connect the clients
- Open your browser to `localhost:5000`
- Fill up the create_game form. You should see "created game <gamename>" in the
  console tab
- For each player, you'll need a separate tab with `localhost:5000` open. You
  can reuse this tab for the first player
- For each player, join the game
- Rest of it should be intuitive.
