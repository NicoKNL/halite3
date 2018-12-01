#!/bin/sh

./halite --replay-directory replays/ -vvv --width 32 --height 32 --seed 1543701148 "python3 MyBot.py" "python3 MyBot_alt.py"
