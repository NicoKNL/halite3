#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction, Position

# This library allows you to generate random numbers.
import random

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (# print statements) are reserved for the engine-bot communication.
import logging
import itertools
""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("R")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

FILL_RATIO = 0.75 # For now we accept 80% fill rate
directions = {"n": (0, 1),
              "e": (1, 0),
              "s": (0, -1),
              "w": (-1, 0)}

def closest_cell_with_ratio_fill(resource_map, resource_max, ship):
    minimum = 0.25 * (resource_max - ship.halite_amount) * FILL_RATIO
    current_offset = 0
    found = False
    pos = ship.position
    target = None

    logging.info(f"{minimum} | {resource_map[ship.position.x][ship.position.y]} | {ship.position}")
    for row in resource_map:
        logging.debug(f"{row}")
    if resource_map[ship.position.x][ship.position.y] >= minimum:
        found = True

    # Search with an expanding ring
    while not found and game_map.height and current_offset < game_map.width: # possible max search range
        logging.error(f"---------- CURRENT OFFSET: {current_offset}")

        offsets = list(range(-current_offset, current_offset + 1))
        offsets = [(x, y) for x in offsets for y in offsets]
        logging.info(f"Offsets: {offsets}")
        # # print(f"Offsets: {offsets}")

        for offset in offsets:
            # # print(f"offset: {offset}")
            cell_pos = game_map.normalize(Position(pos.x - offset[0], pos.y - offset[1]))
            # print(f"cell_pos: {cell_pos}")
            cell = resource_map[cell_pos.x][cell_pos.y]
            if not target and cell >= minimum:
                target = cell_pos
                found = True
            elif cell >= minimum and game_map.calculate_distance(ship.position, cell_pos) < game_map.calculate_distance(ship.position, target):
                target = cell_pos

        current_offset += 1

    if not target:
        target = ship.position
        logging.info("target not found!")

    else:
        logging.info(f"target found!: {target}")
    return target


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

    dropoffs = me.get_dropoffs()

    logging.info("Dropoffs: {}".format(dropoffs))

    # print("Building resource map...")
    # Build the resource map
    resource_map = []
    resource_max = 0
    for row in range(game_map.height):
        row_resources = []
        for col in range(game_map.width):
            cell = game_map[Position(row, col)]

            # Test if an enemy is already on this resource
            resources = 0
            if cell.is_occupied:
                logging.debug(f"SHIP DATA -------------------------------------- {cell.ship.owner} - {me.id}")
                if cell.ship.owner != me.id or Position(row, col) == me.shipyard.position:
                    cell.mark_unsafe(cell.ship)
                else:
                    resources = cell.halite_amount
                    if resources > resource_max:
                        resource_max = resources
            else:
                resources = cell.halite_amount
                if resources > resource_max:
                    resource_max = resources
            row_resources.append(resources)

        resource_map.append(row_resources)

    logging.debug(f"{resource_map}")

    new_ship_positions = []

    # print(f"SHIPS: {me.get_ships()}")
    all_ships = me.get_ships()
    random.shuffle(all_ships)
    for ship in all_ships:
        # For each of your ships, move randomly if the ship is on a low halite location or the ship is full.
        #   Else, collect halite.
        if ship.position == me.shipyard.position:
            # Find a safe way to get out of here
            dirs = ((-1, 0), (1, 0), (0, -1), (0, 1))
            new_dir = None
            for d in dirs:
                if game_map[me.shipyard.position.directional_offset(d)].is_empty:
                    new_dir = Direction.convert(d)

            if not new_dir: # Blocked on all sides...
                # TODO: this is a temporary workaround
                new_dir = Direction.convert(d)

        elif ship.halite_amount >= FILL_RATIO * constants.MAX_HALITE:
            # direction = random.choice(Direction.get_all_cardinals())
            logging.warning("SHIP AMOUNT CASE")
            new_dir = game_map.naive_navigate(ship, me.shipyard.position) #dropoffs[0]) # 1 dropoff for now
        else:
            # print("getting target")
            target = closest_cell_with_ratio_fill(resource_map, resource_max, ship)
            # print("getting direction")
            new_dir = game_map.naive_navigate(ship, target)
            # print(f"Direction: {new_dir}, {type(new_dir)}")
            # direction = random.choice(Direction.get_all_cardinals())

        logging.debug(f"New direction: {new_dir}")
        d = new_dir
        if type(d) is not tuple:
            d = directions[d]

        new_position = ship.position.directional_offset(d)

        if (new_position.x, new_position.y) not in new_ship_positions:
            new_ship_positions.append((new_position.x, new_position.y))
            command_queue.append(ship.move(new_dir))
        else:
            command_queue.append(ship.stay_still())

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    # print(f"{game.turn_number <= 200 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied}")
    if game.turn_number <= 200 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
        logging.info("Spawning new ship")
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
