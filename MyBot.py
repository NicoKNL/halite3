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
game.ready("Dijkstra fix")

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


def evaluate_should_move(ships):
    global game_map
    global command_queue

    ignored_ships = []
    for ship in ships:
        if not game_map[ship].should_move(30):
            move = ship.stay_still()
            game_map.register_move(ship, Direction.Still)
            command_queue.append(move)
        else:
            ignored_ships.append(ship)

    return ignored_ships


def evaluate_other(ships):
    global game_map
    global command_queue

    for ship in ships:
        if ship.position == me.shipyard.position:
            ship.set_task(Task.Gather)

        if ship.halite_amount > 0.9 * constants.MAX_HALITE:
            ship.set_task(Task.Deposit)

        if ship.task == Task.Gather:
            target = ship.position + Position(5, 5)  # Target to the north
            direction = game_map.safe_navigate(ship.position, target)
            move = ship.move(direction)
            game_map.register_move(ship, direction)
            command_queue.append(move)

        if ship.task == Task.Deposit:
            target = me.shipyard.position
            direction = game_map.safe_navigate(ship.position, target)
            move = ship.move(direction)
            game_map.register_move(ship, direction)
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
    ships = evaluate_should_move(ships)
    evaluate_other(ships)

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if len(me.get_ships()) < 100 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:  # and game.turn_number <= 200 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)






