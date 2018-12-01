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
from math import ceil

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (# print statements) are reserved for the engine-bot communication.
import logging
import itertools
import time

from grid import Grid
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
INF = 99999999
directions = {"n": (0, -1),
              "e": (1, 0),
              "s": (0, 1),
              "w": (-1, 0)}

ship_actions = {}
ship_directions = {}


def shipyard_cleanup(game_map, ship, shipyard):
    if ship in ship_actions.keys():
        action = not ship_actions[ship]
    else:
        action = True

    ship_actions[ship] = action

    if ship in ship_directions.keys():
        turn_in = ship_directions[ship]
    elif ship.position == shipyard.position:
        turn_in = False
    else:
        turn_in = False

    ship_directions[ship] = turn_in

    if action:
        if turn_in:
            target = shipyard.position
        else:
            target = ship.position
            max_value = game_map[target.x][target.y].w
            staying_value = max_value // 4
            moving_cost = max_value // 10

            if moving_cost < ship.halite_amount or moving_cost == 0:
                for d in directions.values():
                    pos = game_map.normalize(ship.position.directional_offset(d))
                    logging.debug(f"pos: {pos} | {game_map.calculate_distance(ship.position, shipyard.position) <= 5} | {game_map[pos.x][pos.y].w}")
                    if game_map.calculate_distance(pos, shipyard.position) <= 5:
                        w = game_map[pos.x][pos.y].w
                        if (w // 4) - moving_cost > staying_value and w > max_value:
                            max_value = w
                            target = pos

                if game_map.calculate_distance(ship.position, shipyard.position) == 5:
                    ship_directions[ship] = True  # Start turning in
    else:
        target = ship.position

    logging.debug(f"decision: {target}")
    return target


def closest_cell_with_ratio_fill(game_map, ship):
    t = time.time()

    minimum = min(0.75 * game_map.max_halite, 4 * (constants.MAX_HALITE - ship.halite_amount))
    logging.debug(f"res max: {game_map.max_halite} - minimum: {minimum}")
    current_offset = 1
    found = False
    pos = ship.position
    target = None


    t_new = time.time()
    logging.info(f"CLOSEST CELL FUNC - setup - {t_new - t}")

    # Search with an expanding ring
    while not found and current_offset <= game_map.height: # possible max search range
        logging.error(f"---------- CURRENT OFFSET: {current_offset}")
        t_new = time.time()
        logging.info(f"CLOSEST CELL FUNC - expanding - {t_new - t}")

        offsets = list(range(-current_offset, current_offset + 1))
        offsets = [(x, y) for x in offsets for y in offsets]

        for offset in offsets:
            # # print(f"offset: {offset}")
            cell_pos = game_map.normalize(Position(pos.x - offset[0], pos.y - offset[1]))
            # print(f"cell_pos: {cell_pos}")
            cell = game_map[cell_pos]
            if not target and cell.halite_amount >= minimum:
                target = cell_pos
                found = True
            elif cell.halite_amount >= minimum and game_map.calculate_distance(ship.position, cell_pos) < game_map.calculate_distance(ship.position, target):
                target = cell_pos

        current_offset += 1

    t_new = time.time()
    logging.info(f"CLOSEST CELL FUNC - done expanding - {t_new - t}")

    if not target:
        target = ship.position
        logging.info("target not found!")

    else:
        logging.info(f"target found!: {target}")
    return target


def dijkstra_a_to_b(game_map, source, target, offset=1):
    t = time.time()

    # offset expands the grid bounds upon which we execute dijkstra. By having 1, we can always go around 1 other ship.
    # Assume a and b are only positions, not cells from the grid
    source_cell = game_map[source]
    target_cell = game_map[target]

    # Edge case
    if source == target:
        return Direction.Still

    dx = abs(target.x - source.x)
    dy = abs(target.y - source.y)

    xdir = 1 if target.x > source.x else -1
    ydir = 1 if target.y > source.y else -1

    # Valid x and y positions in range
    if xdir == 1:
        rx = range(source.x, target.x+1)
    else:
        rx = range(target.x, source.x+1)

    if ydir == 1:
        ry = range(source.y, target.y+1)
    else:
        ry = range(target.y, source.y+1)

    # initialize distances
    distance_map = {
        source: {
            "distance": 0,
            "previous": None}
    }
    queue = [source]

    for offset_x in range(-offset, dx + offset + 1):
        for offset_y in range(-offset, dy + offset + 1):
            if offset_x == 0 and offset_y == 0:
                continue
            x = source.x + offset_x * xdir
            y = source.y + offset_y * ydir
            position = Position(x, y)
            distance_map[position] = {
                "distance": INF * 32,
                "previouis": None
            }
            # grid[x][y].dist = INF * 32  # As I'm also using INF for node weighting, this causes issues, hence I make this even larger
            # grid[x][y].prev = None
            queue.append(position)

    while len(queue):
        # Take the item in the queue with the lowest distance and remove it from the queue
        node = sorted(queue, key=lambda position: distance_map[position]["distance"])[0]
        queue.pop(queue.index(node))

        # For each neighbouring position
        for pos in node.get_surrounding_cardinals():
            pos = game_map.normalize(pos)  # Ensure position is in normalized coordinates

            # validate cell is within search bounds
            if pos.x in rx and pos.y in ry:
                neighbour = game_map[pos]
                neighbour_weight = neighbour.halite_amount if game_map[pos].is_occupied else INF

                # Calculate the distance of the path to the neighbour
                dist_to_neighbour = distance_map[node]["distance"] + neighbour_weight

                # If path is shorter than any other current path to that neighbour, then we update the path to that node
                if dist_to_neighbour < distance_map[pos]["distance"]:
                    distance_map[pos]["distance"] = dist_to_neighbour
                    distance_map[pos]["previous"] = node

    t_new = time.time()
    logging.info(f"DIJKSTRA A TO B - queue done - {t_new - t}")

    path_node = target

    # logging.debug(f"path node b: {b} | {path_node}")
    cycles = 0
    while path_node != source:  # and cycles < 200:
        cycles += 1
        t_new = time.time()
        logging.info(f"DIJKSTRA A TO B - traversing - {t_new - t}")
        # logging.debug(f"path node: {(path_node.x, path_node.y)} | {path_node.prev.pos} | {a}")
        prev_path_node = distance_map[path_node]["previous"]
        if prev_path_node == source:
            # logging.debug(f"Conversion: {(path_node.x, path_node.y)} and {(a.x, a.y)} | {(path_node.x - a.x, path_node.y - a.y)}")
            for d in directions.values():
                # logging.debug(f"dir test: {d} | {a.pos.directional_offset(d)} | {path_node.pos}")
                if game_map.normalize(source.directional_offset(d)) == path_node:
                    return Direction.convert(d)

        path_node = prev_path_node

    t_new = time.time()
    logging.info(f"DIJKSTRA A TO B - cycles - {t_new - t}")

""" <<<Game Loop>>> """
ship_count = 0
prev_t = time.time()

while True:
    t = time.time()
    logging.info(f"TURN {game.turn_number - 1}: {t - prev_t} seconds")
    prev_t = t
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    me = game.me
    game_map = game.game_map

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []

    # Build the resource map
    # grid = Grid(game_map, me)

    new_ship_positions = []
    ship_position_map = []  # (ship, target)
    all_ships = me.get_ships()
    for ship in all_ships:
        logging.info(f"==================== SHIP ID {ship.id} ==================")
        current_cell = game_map[ship]
        # Check if ship can and wants to move, OR, if the ship is in imminent danger from an enemy ship
        if (ship.can_move(current_cell) and ship.should_move(current_cell)) or not game_map.position_is_safe(ship):
            # Case: Ship is "full" above threshold
            if ship.halite_amount >= FILL_RATIO * constants.MAX_HALITE:
                new_dir = dijkstra_a_to_b(game_map, ship.position, me.shipyard.position)

            # Case: Gather more resources
            else:
                target = closest_cell_with_ratio_fill(game_map, ship)
                game_map[ship].ship = None
                game_map[target].mark_unsafe(ship)
                new_dir = dijkstra_a_to_b(game_map, ship.position, target)
                logging.debug(f"new dijkstra dir: {new_dir}")

        else:
            new_dir = dijkstra_a_to_b(game_map, ship.position, ship.position)

        d = new_dir
        if not isinstance(d, tuple):
            d = directions[d]

        new_position = game_map.normalize(ship.position.directional_offset(d))

        new_ship_positions.append(new_position)
        ship_position_map.append((ship, new_position, d))

    # Building ship command queue
    for s, p, d in ship_position_map:
        logging.debug(f"position combos: {[(s.position, p) for s, p, _ in ship_position_map]}")
        command_queue.append(s.move(d))

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    # print(f"{game.turn_number <= 200 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied}")
    if game.turn_number <= 200 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied and me.shipyard.position not in [p for _, p, __ in ship_position_map]:
        logging.info("Spawning new ship")
        command_queue.append(me.shipyard.spawn())
        ship_count += 1

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
