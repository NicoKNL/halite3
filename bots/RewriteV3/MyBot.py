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
from math import ceil

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging
""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("RewriteV3")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))


def hunt_close_enemy(ship):
    global game_map

    current_offset = 1
    distance_limit = 5
    found = False
    ship_seen = False
    # Search with an expanding ring
    while not found and current_offset <= game_map.height:  # possible max search range
        offsets = list(range(-current_offset, current_offset + 1))
        offsets = [(x, y) for x in offsets for y in offsets]

        targets = []
        for offset in offsets:
            cell_pos = me.shipyard.position + Position(*offset)
            cell = game_map[cell_pos]
            if cell.is_occupied and cell.ship.owner != me.id:
                targets.append(cell_pos)

            if ship.position == cell_pos:
                ship_seen = True

        if targets:
            best_target = (None, constants.INF)  # For now best => closest
            for target in targets:
                distance = game_map.calculate_distance(ship.position, target)
                if distance < best_target[1] and distance < distance_limit:
                    best_target = (target, distance)
                    # logging.debug(f"{ship.id} best_target found: {best_target}")

            if best_target[0] is not None:
                # logging.debug(f"{ship.id} | Found!")
                found = True

        current_offset += 1
        if ship_seen:
            distance_limit *= 1.5

    # logging.debug(f"{ship.id} ?????????: {best_target} | {current_offset} | {targets} | {found}")

    return best_target[0]


def weighted_cleanup(ship):
    global game_map
    # TODO: Don't do this per ship, but once per game turn and figure out positions for each ship that way
    minimum = min(game_map.max_halite, 30)
    current_offset = 1
    running_sum = 0
    distance_limit = 5
    found = False
    ship_seen = False
    # Search with an expanding ring
    while not found and current_offset <= game_map.height:  # possible max search range
        offsets = list(range(-current_offset, current_offset + 1))
        offsets = [(x, y) for x in offsets for y in offsets]

        targets = []
        for offset in offsets:
            cell_pos = game_map.normalize(me.shipyard.position + Position(*offset))
            cell = game_map[cell_pos]
            if cell.halite_amount >= minimum and not cell.is_occupied:
                targets.append(cell_pos)

            if ship.position == cell_pos:
                ship_seen = True

        if targets:
            best_target = (None, constants.INF)  # For now best => closest
            for target in targets:
                distance = game_map.calculate_distance(ship.position, target)
                if distance < best_target[1] and distance < distance_limit:
                    best_target = (target, distance)
                    # logging.debug(f"{ship.id} best_target found: {best_target}")

            if best_target[0] is not None:
                # logging.debug(f"{ship.id} | Found!")
                found = True

        current_offset += 1
        if ship_seen:
            distance_limit *= 1.5

    # logging.debug(f"{ship.id} ?????????: {best_target} | {current_offset} | {targets} | {found}")

    return best_target[0]


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

    first_movers, gather_ships, deposit_ships, suicide_ships, hunting_ships = resolve_tasks(ships)

    for ship in first_movers:
        target = weighted_cleanup(ship)
        direction = game_map.navigate(ship.position, target, offset=2)
        move = ship.move(direction)
        game_map.register_move(ship, direction)
        command_queue.append(move)

    for ship in sorted(deposit_ships,
                       key=lambda ship: game_map.calculate_distance(me.shipyard.position, ship.position),
                       reverse=False):
        target = me.shipyard.position
        direction = game_map.navigate(ship.position, target, offset=0)
        move = ship.move(direction)
        game_map.register_move(ship, direction)
        command_queue.append(move)

    for ship in sorted(suicide_ships,
                       key=lambda ship: game_map.calculate_distance(me.shipyard.position, ship.position),
                       reverse=False):
        target = me.shipyard.position
        direction = game_map.navigate(ship.position, target, offset=0, ignore_dropoff=True)
        move = ship.move(direction)
        game_map.register_move(ship, direction)
        command_queue.append(move)

    for ship in sorted(hunting_ships,
                       key=lambda ship: game_map.calculate_distance(me.shipyard.position, ship.position),
                       reverse=True):
        target = hunt_close_enemy(ship)
        direction = game_map.navigate(ship.position, target, offset=0)
        move = ship.move(direction)
        game_map.register_move(ship, direction)
        command_queue.append(move)

    for ship in sorted(gather_ships,
                       key=lambda ship: game_map.calculate_distance(me.shipyard.position, ship.position),
                       reverse=True):
        # target = ship.position + Position(5, 5)  # Target to the north
        target = weighted_cleanup(ship)
        direction = game_map.navigate(ship.position, target, offset=1)
        move = ship.move(direction)
        game_map.register_move(ship, direction)
        command_queue.append(move)


def resolve_tasks(ships):
    global game_map
    first_movers = []
    gather_ships = []
    deposit_ships = []
    suicide_ships = []
    hunting_ships = []

    turns_remaining = constants.MAX_TURNS - game.turn_number
    for ship in ships:
        if game_map.calculate_distance(me.shipyard.position, ship.position) + 6 + ceil(len(me.get_ships()) / 10) >= turns_remaining:
            if ship.task == Task.EndgameHunt:
                hunting_ships.append(ship)
            elif ship.task == Task.Suicide:
                suicide_ships.append(ship)
            elif ship.halite_amount > 200:
                ship.set_task(Task.Suicide)
                suicide_ships.append(ship)
            else:
                ship.set_task(Task.EndgameHunt)
                hunting_ships.append(ship)

        elif ship.halite_amount >= 0.9 * constants.MAX_HALITE or (ship.task == Task.Deposit and ship.position != me.shipyard.position):
            ship.set_task(Task.Deposit)
            deposit_ships.append(ship)

        elif ship.position == me.shipyard.position or ship.task == Task.Gather:
            ship.set_task(Task.Gather)

            if ship.position == me.shipyard.position:
                first_movers.append(ship)
            else:
                gather_ships.append(ship)

    return first_movers, gather_ships, deposit_ships, suicide_ships, hunting_ships


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
    if game_map.total_halite / max(len(me.get_ships()), 1) > 6000 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied and not game_map[me.shipyard].is_claimed and game.turn_number <= constants.MAX_TURNS - 150:
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game_map.reset_claims()
    game.end_turn(command_queue)






