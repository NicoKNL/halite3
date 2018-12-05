#!/bin/sh

./halite --replay-directory replays/ -vvv --width 64 --height 64 "python3 MyBot.py" "python3 MyBot_alt/MyBot_alt.py" "python3 MyBot_alt2/MyBot_alt2.py" "python3 MyBot_alt3/MyBot_alt3.py"
