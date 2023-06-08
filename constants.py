"""Constants. Used to configure the game"""

# Number of affinity topics in a game
NUM_AFFINITY_TOPICS = 2

# If the affinity towards any topic reaches this count, the player gains the
# viral spiral power
VIRAL_SPIRAL_AFFINITY_COUNT = 5
VIRAL_SPIRAL_BIAS_COUNT = 5

# If the affinity towards any topic reaches 3, the player receives the
# cancel power
CANCELLING_AFFINITY_COUNT = 1
# if true, cancel has the polling mechanic
CANCELLING_ALLOW_POLL = False
# If True, all players will be asked to vote instead of just the affinity
CANCEL_VOTE_ALL_PLAYERS = False

# If bias against any topic reaches 3, the player receives the fake news power
FAKE_NEWS_BIAS_COUNT = 0

ACTIVE_STR = "active"

# If a player reaches a number of points, they win and the game ends
PLAYER_WIN_SCORE = 7 # changed for a quicker game
# If the TBG reaches a number of points, the game ends
TGB_END_SCORE = 15

SOCKET_EVENT_ENC_SEARCH_RESULT = "encyclopedia_search_result"

# Game creation retries
GAME_CREATION_TOTAL_TRIES = 2
