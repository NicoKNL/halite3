#!/bin/sh

./halite --replay-directory replays/ -vvv --width 32 --height 32 "python3 MyBot.py" "python3 ./bots/RewriteV5/MyBot.py"
