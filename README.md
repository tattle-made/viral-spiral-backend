# viral-spiral-backend

All command examples are from the repo root

## Running locally

### Prerequisites

- Install postgresql locally
- Create a database called "tattleviralspiral"
  - You can do this by running `psql -U postgres` and then `create databaset tattleviralspiral`
- Install python3 and create a virtualenv using pipenv

```
pipenv shell
```

- Activate the environment

```
pipenv shell
source ./activate_env.sh
```

- Install dependencies

```
pipenv sync
```

- Initialize the db

```
python setup.py
```

## Run the server

- Run the startup script

```
bash start.sh
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

# Communication with the server

All communication happens with sockets, using the [socket.io](https://socket.io/) framework. The flow is as follows:

We don't use any namespaces as of now. CORS might not be enabled on the server yet -
so if you can use some broser plugin to disable cors (not tested yet) that will
be great. I will look into enabling cors. The socket.io path is the default
path (basically for initialization, I didn't provide any path. You can check
out main_loop/templates/index.html for reference).

Actions (outgoing events):

1. Create a game (needs to be done only once. All game names are unique):
   - Event name: "create_game"
   - Example - `main_loop/index.html:95`
2. Join a game (needs to be done every time you re-load the socket):
   - Once you join a game, your client's session ID is stored in the backend
   - So if this client ID changes (might happen on a page refresh), you need
     to join the game again
   - Event name: "join_game"
   - Example: `main_loop/index.html:143`
3. Player action - this event is triggered whenever the player performs a card
   action
   - Action can be to keep a card or pass a card (more details in the examples)
   - TODO add more actions like initiate cancel player, vote cancel player,
     make fake news, etc -- actions for each of the special powers
     - Viral spiral action is a part of pass card
   - All these actions will be a part of this same event as of now.
   - Example: `main_loop/index.html:220`
     - To see the different types of actions, you can analyse the `data`
       variable in that command - and see how it changes when you fill out a
       form and select perform action
4. About game - returns information about this game
   - To be used to get the game state
   - Example: `main_loop/index.html:311`
5. Ping
   - Sample request that sends "my_ping" and the server returns "my_pong". Can
     be used to check the connection to the server
6. get queued card - get the card queued for the current player
   - Not being used in the frontend as of now since the play_card action gives
     this information
   - Python code: `main_loop/websocket.py:265`

Events (incoming events):

1. "connect" - Triggered on successful connection. `main_loop/index.html:258`
2. "play_card" - Reminder to play the card. `main_loop/index.html:266`
3. "about": Response to the "about game" action: `main_loop/index.html:288`
4. "whos_turn" - Triggered whenever a round starts - returns the data about
   who's turn it is. `main_loop/index.html:295`
5. "endgame" - Triggered when the game ends. `main_loop/index.html:301`
6. "text_response" - This is a generic event triggered. All data coming here
   goes into the `console` tab of the demo UI. `main_loop/index.html:261`
   - TODO create better specific events instead of using text_response
   - Following server events trigger this "text_response" event:
     - heartbeat every 10 seconds
     - Response to a `create_game` request
     - Response to a `load_game` request -- this action is not being used in
       the frontend. If you trigger a `join_game` it will automatically load
       the game.
     - Response to a `player_action` request
     - Response to a disconnect request
     - Response to a connect request
     - When a round finishes
     - Response to joining a game

# Running Using Docker

```
docker-compose up

docker ps //to confirm if the services are running
docker exec -it api /bin/sh
pipenv shell
python setup.py // one time thing to run database database migrations
./start.sh
```
If you are on windows and are running into the `source: not found` error while running the `./start.sh` command, then instead of it try running `python main_loop/websocket.py`