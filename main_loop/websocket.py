import os
from threading import Lock, Thread
from flask import Flask, render_template, session, request, copy_current_request_context
from flask_socketio import (
    SocketIO,
    emit,
    join_room,
    leave_room,
    close_room,
    rooms,
    disconnect,
)

from models import Game, Player
from deck_generators import GENERATORS

from main_loop.base import GameRunner

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET")
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()


class WebsocketGameRunner(GameRunner):

    background_tasks = {}
    max_games = 3  # Allow maximum of 3 games to run in parallel

    def __init__(self, *args, name: str = None, **kwargs):
        self.socket_loop_count = 0
        self.name = name
        self.tread = thread
        super().__init__(*args, **kwargs)

    def do_round(self, *args, **kwargs):
        """Sleeps socket things"""
        socketio.sleep(10)
        super().do_round(*args, **kwargs)
        self.socket_loop_count += 1
        emit(
            "text_response",
            {"data": "Finished a round", "count": self.socket_loop_count},
            to=self.name,
        )

    def loop_async(self):
        """Runs the loop function in a thread"""
        self.thread = Thread(target=self.loop)
        self.thread.start()
        self.background_tasks[self.name] = self

    def exit(self):
        self.thread.join()
        self.background_tasks.pop(self.name)
        close_room(self.name)

    @classmethod
    def create_thread(cls, *args, **kwargs):
        """Passes on the arguments to the init function and runs it in a
        background thread"""
        runner = cls(*args, **kwargs)
        runner.loop_async()

    @classmethod
    def create(
        cls,
        name: str,
        players: list[str],
        colors: list[str],
        topics: list[str],
        draw_fn_name: str,
    ):
        game = Game.new(
            name=name,
            players=players,
            colors=colors,
            topics=topics,
        )
        draw_fn = GENERATORS.get(draw_fn_name)
        assert draw_fn
        cls.create_thread(name=name, game=game, draw_fn=draw_fn)

    @classmethod
    def get_by_name(cls, name):
        runner = cls.background_tasks.get(name)
        if runner:
            return runner


def background_thread():
    """Main Loop. Just sends an alive signal."""
    count = 0
    while True:
        socketio.sleep(10)
        count += 1
        socketio.emit(
            "text_response", {"data": "Server generated event", "count": count}
        )


@app.route("/")
def index():
    """Renders the main page of the game"""
    return render_template("index.html", async_mode=socketio.async_mode)


# @socketio.event
# def join_room(message):
#     join_room(message["room"])
#     session["receive_count"] = session.get("receive_count", 0) + 1
#     emit(
#         "text_response",
#         {"data": "In rooms: " + ", ".join(rooms()), "count": session["receive_count"]},
#     )


def join_game(message):
    """Takes a player name and game room name. Joins the game. The game needs
    to be created with another API"""
    game_name = message["game"]
    player_name = message["player"]
    runner = WebsocketGameRunner.get_by_name(game_name)
    if runner:
        join_room(game_name)
        emit("text_response", {"data": "Joined game {game_name}"})
    else:
        emit("text_response", {"data": "Room not found"})


def create_game(message):
    """Creates a game"""
    game_name = message["game"]
    players = message["players"].split(",")
    colors = message["colors"].split(",")
    topics = message["topics"].split(",")
    draw_fn_name = message["draw_fn_name"]
    WebsocketGameRunner.create(
        name=game_name,
        players=players,
        colors=colors,
        topics=topics,
        draw_fn_name=draw_fn_name,
    )


# @socketio.event
# def leave_room(message):
#     leave_room(message["room"])
#     session["receive_count"] = session.get("receive_count", 0) + 1
#     emit(
#         "text_response",
#         {"data": "In rooms: " + ", ".join(rooms()), "count": session["receive_count"]},
#     )


# @socketio.event
# def my_rooms(message):
#     emit(
#         "text_response",
#     )


# @socketio.on("close_room")
# def on_close_room(message):
#     session["receive_count"] = session.get("receive_count", 0) + 1
#     emit(
#         "text_response",
#         {
#             "data": "Room " + message["room"] + " is closing.",
#             "count": session["receive_count"],
#         },
#         to=message["room"],
#     )
#     close_room(message["room"])


@socketio.event
def game_action(message):
    session["receive_count"] = session.get("receive_count", 0) + 1
    game_name = message["room"]
    runner = WebsocketGameRunner.get_by_name(game_name)
    if runner:
        emit(
            "text_response",
            {"data": message["data"], "count": session["receive_count"]},
            to=request.sid,
        )
    emit(
        "text_response",
        {"data": message["data"], "count": session["receive_count"]},
        to=request.sid,
    )


@socketio.event
def disconnect_request():
    @copy_current_request_context
    def can_disconnect():
        disconnect()

    session["receive_count"] = session.get("receive_count", 0) + 1
    # for this emit we use a callback function
    # when the callback function is invoked we know that the message has been
    # received and it is safe to disconnect
    emit(
        "text_response",
        {"data": "Disconnected!", "count": session["receive_count"]},
        callback=can_disconnect,
    )


@socketio.event
def my_ping():
    emit("my_pong")


@socketio.event
def connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    emit("text_response", {"data": "Connected", "count": 0})


@socketio.on("disconnect")
def test_disconnect():
    print("Client disconnected", request.sid)


if __name__ == "__main__":
    socketio.run(app)
