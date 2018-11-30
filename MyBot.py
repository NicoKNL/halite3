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


def shipyard_cleanup(resource_map, ship, shipyard):
    resource_map = resource_map.grid

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
            max_value = resource_map[target.x][target.y].w
            staying_value = max_value // 4
            moving_cost = max_value // 10

            if moving_cost < ship.halite_amount or moving_cost == 0:
                for d in directions.values():
                    pos = game_map.normalize(ship.position.directional_offset(d))
                    logging.debug(f"pos: {pos} | {game_map.calculate_distance(ship.position, shipyard.position) <= 5} | {resource_map[pos.x][pos.y].w}")
                    if game_map.calculate_distance(pos, shipyard.position) <= 5:
                        w = resource_map[pos.x][pos.y].w
                        if (w // 4) - moving_cost > staying_value and w > max_value:
                            max_value = w
                            target = pos

                if game_map.calculate_distance(ship.position, shipyard.position) == 5:
                    ship_directions[ship] = True  # Start turning in
    else:
        target = ship.position

    logging.debug(f"decision: {target}")
    return target


def closest_cell_with_ratio_fill(resource_map, ship):
    minimum = 0.25 * (resource_map.max_w - ship.halite_amount) * FILL_RATIO
    logging.debug(f"res max: {resource_map.max_w}")
    resource_map = resource_map.grid
    current_offset = 1
    found = False
    pos = ship.position
    target = None

    logging.info(f"min: {minimum} | have: {ship.halite_amount} | {resource_map[ship.position.x][ship.position.y]} | {ship.position}")
    # for row in resource_map:
    #     logging.debug(f"{row}")

    # Check if we CAN move
    if ceil(resource_map[ship.position.x][ship.position.y].w / 10.0) > ship.halite_amount:
        found = True
        target = ship.position

    # Search with an expanding ring
    while not found and current_offset < game_map.height and current_offset < game_map.width: # possible max search range
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
            if not target and cell.w >= minimum:
                target = cell_pos
                found = True
            elif cell.w >= minimum and game_map.calculate_distance(ship.position, cell_pos) < game_map.calculate_distance(ship.position, target):
                target = cell_pos

        current_offset += 1

    if not target:
        target = ship.position
        logging.info("target not found!")

    else:
        logging.info(f"target found!: {target}")
    return target


def dijkstra_a_to_b(grid, a, b, offset=1):
    # offset expands the grid bounds upon which we execute dijkstra. By having 1, we can always go around 1 other ship.
    # Assume a and b are only positions, not cells from the grid
    a = grid[a.x][a.y]
    b = grid[b.x][b.y]

    # Edge case
    if a.pos == b.pos:
        logging.debug(f"a pos: {a.pos} - b pos: {b.pos} - equal? {a.pos == b.pos}")
        return Direction.Still

    grid_width = len(grid[0])
    grid_height = len(grid)

    dx = abs(b.x - a.x)
    dy = abs(b.y - a.y)

    xdir = 1 if b.x > a.x else -1
    ydir = 1 if b.y > a.y else -1

    # Valid x and y positions in range
    if xdir == 1:
        rx = range(a.x, b.x+1)
    else:
        rx = range(b.x, a.x+1)

    if ydir == 1:
        ry = range(a.y, b.y+1)
    else:
        ry = range(b.y, a.y+1)

    # initialize distances
    a.dist = 0
    a.prev = None
    queue = [a]

    for offset_x in range(dx + 1):
        for offset_y in range(dy + 1):
            if offset_x == 0 and offset_y == 0:
                continue
            x = a.x + offset_x * xdir
            y = a.y + offset_y * ydir
            # logging.debug(f"-------------------------setting {(x, y)}")
            grid[x][y].dist = INF
            grid[x][y].prev = None
            queue.append(grid[x][y])

    while len(queue):
        # logging.debug(f"::QUEUE:: {queue}")
        # logging.debug(f"::QUEUE POS:: {[(q.x, q.y) for q in queue]}")
        node = sorted(queue, key=lambda n: n.dist)[0]
        # logging.debug(f"::QUEUE SRT:: {[(q.x, q.y) for q in queue]}")
        queue.pop(queue.index(node))

        # logging.debug(f"Starting on: {(node.x, node.y)}")
        for d in directions.values():
            neighbour_x = (node.x + d[0]) % grid_width
            neighbour_y = (node.y + d[1]) % grid_height

            logging.debug(f"{(a.x, a.y)} | {(b.x, b.y)} =>? {(neighbour_x, neighbour_y)}")
            # validate cell is within bounds
            if neighbour_x in rx and neighbour_y in ry:
                # logging.debug("entered")
                neighbour = grid[neighbour_x][neighbour_y]

                if neighbour == a:
                    # logging.debug("encountered root")
                    continue
                if node.prev:
                    if neighbour == node.prev:
                        # logging.debug("backtracking block")
                        continue

                # logging.debug("after root and backtracking check")
                alt_dist = node.dist + neighbour.tw
                if alt_dist < neighbour.dist or neighbour.dist == INF:
                    neighbour.dist = alt_dist
                    neighbour.prev = node

                logging.debug(f"{neighbour == b}")
                if neighbour == b:
                    logging.debug(f"{neighbour.prev} and {b.prev}")

    path_node = b

    logging.debug(f"path node b: {b} | {path_node}")
    cycles = 0
    while path_node != a and cycles < 40:
        logging.debug(f"path node: {(path_node.x, path_node.y)} | {path_node.prev} | {a}")
        prev_path_node = path_node.prev
        if prev_path_node == a:
            logging.debug(f"Conversion: {(path_node.x, path_node.y)} and {(a.x, a.y)} | {(path_node.x - a.x, path_node.y - a.y)}")
            for d in directions.values():
                logging.debug(f"dir test: {d} | {a.pos.directional_offset(d)} | {path_node.pos}")
                if game_map.normalize(a.pos.directional_offset(d)) == path_node.pos:
                    return Direction.convert(d)

        path_node = prev_path_node

    # TODO: workaround for the negative path weights I feel I is the issue for this algo right now.
    if cycles >= 40:
        return Direction.Still


""" <<<Game Loop>>> """
ship_count = 0

while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    logging.debug(f"GAME MAP SIZE: ({game_map.width}, {game_map.height})")

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []

    # dropoffs = me.get_dropoffs()
    # logging.info("Dropoffs: {}".format(dropoffs))

    # Build the resource map
    grid = Grid(game_map, me)

    new_ship_positions = []
    ship_position_map = []  # (ship, target)
    all_ships = me.get_ships()
    for ship in all_ships:
        logging.info(f"==================== SHIP ID {ship.id} ==================")
        current_cell = grid.grid[ship.position.x][ship.position.y]
        # Check if ship can and wants to move
        if ship.can_move(current_cell) and ship.should_move(current_cell):
            # Case: Ship is "full" above threshold
            if ship.halite_amount >= FILL_RATIO * constants.MAX_HALITE:
                new_dir = dijkstra_a_to_b(grid.grid, ship.position, me.shipyard.position)

            # Case: Gather more resources
            else:
                # Early game
                if game.turn_number < 0:  # < 125:
                    target = shipyard_cleanup(grid, ship, me.shipyard)

                # Mid and late game
                else:
                    target = closest_cell_with_ratio_fill(grid, ship)

                grid.grid[target.x][target.y].set_weight(-INF)
                new_dir = dijkstra_a_to_b(grid.grid, ship.position, target)
                logging.debug(f"new dijkstra dir: {new_dir}")

        else:
            new_dir = dijkstra_a_to_b(grid.grid, ship.position, ship.position)

        d = new_dir
        if not isinstance(d, tuple):
            d = directions[d]

        new_position = game_map.normalize(ship.position.directional_offset(d))
        grid.grid[new_position.x][new_position.y].set_weight(-INF)
        grid.grid[new_position.x][new_position.y].set_travel_weight(INF)

        new_ship_positions.append(new_position)
        ship_position_map.append((ship, new_position, d))

    # temporary solution to resolve collisions
    logging.debug("============= COLLISION SOLVER 1.0 =============")
    solved = False

    while not solved:
        collision_detected = False

        all_new_positions = [p for _, p, __ in ship_position_map]
        logging.debug(f"position combos: {[(s.position, p) for s, p, _ in ship_position_map]}")
        for s, p, _ in ship_position_map:
            logging.debug(f"testing: {p} | anpCount: {all_new_positions.count(p)}")
            logging.debug(f"{all_new_positions}")
            if all_new_positions.count(p) > 1:
                # Collision detected
                logging.debug("........ COLLISION DETECTED ..........")

                collision_detected = True

        if not collision_detected:
            logging.debug("============= COLLISIONS SOLVED!~~~ =============")

            solved = True
        else:
            tmp_map = []
            for s, p, d in ship_position_map:
                if all_new_positions.count(p) == 1:
                    tmp_map.append((s, p, d))
                else:
                    new_d = random.choice(Direction.get_all_cardinals())
                    new_p = game_map.normalize(s.position.directional_offset(new_d))

                    # See if we can make the move
                    moving_cost = grid.grid[s.position.x][s.position.y].w // 10
                    if moving_cost < s.halite_amount:
                        tmp_map.append((s, new_p, new_d))
                    else:
                        tmp_map.append((s, p, d))

            logging.debug(f"tmp: {[p for _, p, __ in tmp_map]}")

            ship_position_map = tmp_map

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
