"""File containing all communication messages between backend and frontned"""

from abc import ABC


class IncomingMessage(object):
    """Represents an event in the game"""

    def __init__(self, name, message_template, reply=None):
        self.name = name
        self.message_template = message_template
        self.reply = reply


class OutgoingMessage(object):
    """Represents data sent from the server to (a) client(s)"""

    TO_PLAYER = "to_player"
    TO_GAME = "to_game"
    TO_SENDER = "to_sender"
    TO_OPTIONS = [TO_PLAYER, TO_GAME, TO_SENDER]
    TO_ANY = TO_OPTIONS

    def __init__(self, name=None, message_template=None, can_send_to: list = None):
        self.name = name
        self.message_template = message_template

        for receiver in can_send_to:
            assert receiver in self.TO_OPTIONS

        self.can_send_to = can_send_to


HEARTBEAT = OutgoingMessage(
    name="heartbeat",
    can_send_to=OutgoingMessage.TO_ANY,
    message_template={"data": "heartbeat", "count": "{integer}"},
)

ERROR_GENERIC = OutgoingMessage(
    name="error",
    can_send_to=OutgoingMessage.TO_ANY,
    message_template={
        "original_message": "{original_message}",
        "error": "{error message}",
    },
)

ERROR_GAME_NOT_FOUND = OutgoingMessage(
    name="error_game_not_found",
    can_send_to=OutgoingMessage.TO_ANY,
    message_template={
        "original_message": "{original_message}",
        "error": "Game Not Found",
    },
)

ERROR_GAME_ALREADY_JOINED = OutgoingMessage(
    name="error_game_already_joined",
    can_send_to=OutgoingMessage.TO_ANY,
    message_template={
        "original_message": "{original_message}",
        "error": "Already Joined",
    },
)

NOTIF_PLAY_CARD = OutgoingMessage(
    name="play_card",
    can_send_to=[OutgoingMessage.TO_PLAYER],
    message_template={
        "data": {
            "card_instance": "{details about the card to play}",
            "recipients": "{list of names of players who can receive this card}",
        },
    },
)

NOTIF_VOTE = OutgoingMessage(
    name="vote_cancel",
    can_send_to=[OutgoingMessage.TO_PLAYER],
    message_template={
        "data": {
            # The ID of the cancel status object is sent here - which is
            # required to perform the vote action
            "pending_vote": "{details about who to vote for cancellation}",
        },
    },
)

NOTIF_FINISHED_ROUND = OutgoingMessage(
    name="end_of_round",
    can_send_to=[OutgoingMessage.TO_GAME],
    message_template={"data": "Finished a round"},
)

NOTIF_END_GAME = OutgoingMessage(
    name="endgame",
    can_send_to=[OutgoingMessage.TO_GAME],
    message_template={
        "data": None,  # No message
        # TODO display winner here
    },
)

REPLY_ABOUT_GAME = OutgoingMessage(
    can_send_to=[OutgoingMessage.TO_SENDER, OutgoingMessage.TO_PLAYER],
    message_template={
        "original_message": "{original_message}",
        # TODO add more details
    },
)

REPLY_CREATED_GAME = OutgoingMessage(
    can_send_to=[OutgoingMessage.TO_SENDER],
    message_template={
        "original_message": "{original_message}",
        "data": "Create game: {game_name}",
    },
)

REPLY_JOINED_GAME = OutgoingMessage(
    can_send_to=[OutgoingMessage.TO_SENDER, OutgoingMessage.TO_PLAYER],
    message_template={
        "original_message": "{original_message}",
        "message": "Joined game {game_name}",
    },
)

ERROR_NO_QUEUED_CARD = OutgoingMessage(
    name="error_no_queued_card",
    can_send_to=[OutgoingMessage.TO_SENDER],
    message_template={
        "original_message": "{original_message}",
        "message": "No card queued",
    },
)

REPLY_QUEUED_CARD = OutgoingMessage(
    can_send_to=[OutgoingMessage.TO_SENDER],
    message_template={
        "original_message": "{original_message}",
        "data": "{dictionary_of_queued_card}",
    },
)

REPLY_PERFORMED_ACTION = OutgoingMessage(
    can_send_to=[OutgoingMessage.TO_SENDER],
    message_template={
        "original_message": "{original_message}",
        "action": "{action}",
    },
)

EVENT_ABOUT_GAME = IncomingMessage(
    name="about_game",
    message_template={"game": "{name_of_the_game}"},
    reply=[ERROR_GAME_NOT_FOUND, REPLY_ABOUT_GAME],
)

EVENT_JOIN_GAME = IncomingMessage(
    name="join_game",
    message_template={"game": "{name_of_the_game}", "player": "{name_of_the_player}"},
    reply=[ERROR_GAME_NOT_FOUND, ERROR_GAME_ALREADY_JOINED, REPLY_JOINED_GAME],
)

EVENT_CREATE_GAME = IncomingMessage(
    name="create_game",
    message_template={
        "game": "{name_of_the_game}",
        "players": "{comma_seperated_player_list}",
        "colors_filepath": "{backend_filepath_of_colors_json_obj}",
        "topics_filepath": "{backend_filepath_of_topics_json_obj}",
        "cards_filepath": "{backend_filepath_of_cards_json_obj}",
        "password": "{game_password}",  # Unused as of now
        "draw_fn_name": "{name_of_draw_function_already_defined_in_backend}",
    },
    reply=[REPLY_CREATED_GAME, ERROR_GENERIC],
)

EVENT_GET_QUEUED_CARD = IncomingMessage(
    name="get_queued_card",
    message_template={
        "game": "{name_of_the_game}",
        "player": "{name_of_the_player}",
    },
    reply=[ERROR_NO_QUEUED_CARD, ERROR_GAME_NOT_FOUND, REPLY_QUEUED_CARD],
)

PLAYER_ACTION_KEEP_CARD = IncomingMessage(
    name="player_action",
    message_template={
        "game": "{name_of_the_game}",
        "player": "{name_of_the_player}",
        "action": "keep_card",
        "kwargs": {"card_instance_id": "{ID of currently queued card}"},
    },
    reply=[ERROR_GENERIC, REPLY_PERFORMED_ACTION],
)

PLAYER_ACTION_DISCARD_CARD = IncomingMessage(
    name="player_action",
    message_template={
        "game": "{name_of_the_game}",
        "player": "{name_of_the_player}",
        "action": "discard_card",
        "kwargs": {"card_instance_id": "{ID of currently queued card}"},
    },
    reply=[ERROR_GENERIC, REPLY_PERFORMED_ACTION],
)

PLAYER_ACTION_PASS_CARD = IncomingMessage(
    name="player_action",
    message_template={
        "game": "{name_of_the_game}",
        "player": "{name_of_the_player}",
        "action": "pass_card",
        "kwargs": {
            "card_instance_id": "{ID of currently queued card to pass}",
            "to": "{name_of_card_recipient}",
        },
    },
    reply=[ERROR_GENERIC, REPLY_PERFORMED_ACTION],
)

PLAYER_ACTION_VIRAL_SPIRAL = IncomingMessage(
    name="player_action",
    message_template={
        "game": "{name_of_the_game}",
        "player": "{name_of_the_player}",
        "action": "viral_spiral",
        "kwargs": {
            "keep_card_instance_id": "{ID of card to keep - can be undefined/null}",
            "pass_card_instance_id": "{ID of card to pass}",
            # As of now, keep_card_instance_id should always be null.
            # Once we allow users to keep the current card and pass a different
            # (previously held) card, then keep_card_instance_id will be the
            # current card and pass_card_instance_id can be a previously held
            # card
        },
    },
    reply=[ERROR_GENERIC, REPLY_PERFORMED_ACTION],
)

PLAYER_ACTION_INITIATE_CANCEL = IncomingMessage(
    name="player_action",
    message_template={
        "game": "{name_of_the_game}",
        "player": "{name_of_the_player}",
        "action": "initiate_cancel",
        "kwargs": {
            "against": "{name of player to cancel for this round}",
        },
    },
    reply=[ERROR_GENERIC, REPLY_PERFORMED_ACTION],
)

PLAYER_ACTION_VOTE_CANCEL = IncomingMessage(
    name="player_action",
    message_template={
        "game": "{name_of_the_game}",
        "player": "{name_of_the_player}",
        "action": "vote_cancel",
        "kwargs": {
            "cancel_status_id": "{ID of cancel status (sent to client as a message)}",
            "vote": "{Boolean - True to cancel, false to not cancel}",
        },
    },
    reply=[ERROR_GENERIC, REPLY_PERFORMED_ACTION],
)

PLAYER_ACTION_FAKE_NEWS = IncomingMessage(
    # Convert a card to fake news
    name="player_action",
    message_template={
        "game": "{name_of_the_game}",
        "player": "{name_of_the_player}",
        "action": "fake_news",
        "kwargs": {
            "card_instance_id": "{ID of currently held card}",
            "fake_card_id": "{ID of fake card to immitate}",
            # All possible fake cards for a given card will be saved in the
            # backend for simplicity instead of generating new fake cards on
            # the fly. We can optimise this later.
            # TODO see if this works or whether we should generate fake cards
            # on the fly.
            # If we are generating fake cards on the fly, then we need to take
            # those details as kwargs here
        },
    },
    reply=[ERROR_GENERIC, REPLY_PERFORMED_ACTION],
)

PLAYER_ACTION_MARK_AS_FAKE = IncomingMessage(
    # Report a card as fake
    name="player_action",
    message_template={
        "game": "{name_of_the_game}",
        "player": "{name_of_the_player}",
        "action": "mark_as_fake",
        "kwargs": {"card_instance_id": "{ID of currently held card}"},
    },
    reply=[ERROR_GENERIC, REPLY_PERFORMED_ACTION],
)

PLAYER_ACTION_ENCYCLOPEDIA_SEARCH = IncomingMessage(
    # Search for a keyword in the encyclopedia
    name="player_action",
    message_template={
        "game": "{name_of_the_game}",
        "player": "{name_of_the_player}",
        "action": "encyclopedia_search",
        "kwargs": {"keyword": "{ID of currently held card}"},
    },
    reply=[ERROR_GENERIC],
)
