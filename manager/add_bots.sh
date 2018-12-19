#!/bin/bash
for bot in bots/mybot*
do
  if [ -f $bot ]
  then
    botname=${bot/bots\//}
    ./manager.py -A $botname -p $bot
  fi
done
