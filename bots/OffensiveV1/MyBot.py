#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt
from hlt.task import Task
# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction, Position

# This library allows you to generate random numbers.
import random

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging
""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("OffensiveV1")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))


def evaluate_can_move(ships):
    global game_map
    global command_queue

    ignored_ships = []
    for ship in ships:
        if not game_map[ship].can_move():
            move = ship.stay_still()
            game_map.register_move(ship, Direction.Still)
            command_queue.append(move)
        else:
            ignored_ships.append(ship)

    return ignored_ships


def evaluate_other(ships):
    global game_map
    global command_queue

    second_pass_ships = []
    for ship in ships:
        if ship.has_focus and ship.has_target:
            logging.debug(f"#{ship.id} at {ship.position} || focus: {ship.focus} || target: {ship.target}")
            direction = game_map.navigate(ship.position, ship.target, offset=3)
            game_map.register_move(ship, direction)

            move = ship.move(direction)
            command_queue.append(move)
        else:
            second_pass_ships.append(ship)

    for ship in second_pass_ships:
        focus = game_map.enemy_bases[0]
        target = [t for t in focus.get_plus_cardinals() if not game_map[t].is_taken][0]
        ship.set_focus(focus)
        ship.set_target(target)
        game_map[target].take()

        direction = game_map.navigate(ship.position, target, offset=3)
        game_map.register_move(ship, direction)

        move = ship.move(direction)
        command_queue.append(move)


""" <<<Game Loop>>> """
while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []

    ships = me.get_ships()
    ships = evaluate_can_move(ships)
    evaluate_other(ships)

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if game_map.total_halite / max(len(me.get_ships()), 1) > 6000 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied and not game_map[me.shipyard].is_claimed and game.turn_number <= constants.MAX_TURNS - 150:
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game_map.reset_claims()
    game.end_turn(command_queue)






