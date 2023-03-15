# End to end testing

The file(s) for end to end testing currently are: `game-creator.py`, `viral-spiral-tester.py`, `encyclopedia-tester.py`, `mark-as-fake-tester.py`

Run the following commands before running any of the testing files:

```
pipenv shell
pip install selenium
pip install webdriver_manager
```

The file `game-creator.py` should run multiple instances of chrome on your browser and simulate the game with 4 players players playing.If you run the command: `python game-creator.py | tee output.txt` you will find the log of the game inside the `output.txt` file at the end of the game.

The file `viral-spiral-tester.py` is for testing the special power 'Viral Spiral'. It tests whether the viral spiral power is working successfully when 4 players are playing. In order to successfully run it, you need to first visit `constants.py` and change the values of the variable `VIRAL_SPIRAL_AFFINITY_COUNT` and `VIRAL_SPIRAL_BIAS_COUNT` to 0 (so that the powers are available to the players from the start). Running the command `python viral-spiral-tester.py | tee output.txt` will let you log the output the the file in `output.txt`.

The files `encyclopedia-tester.py` and `mark-as-fake-tester.py` are used to test the special powers 'Check Source/Encyclopedia Search' and 'Mark as Fake' respectively. Running them using the commands used for the previous files, replacing the file name wherever necessary, should give you the verdict on those features in the `output.txt` file.
