#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction, Position
from hlt.resource_tree import ResourceTree

# This library allows you to generate random numbers.
import random
from math import ceil

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (# print statements) are reserved for the engine-bot communication.
import logging
import itertools
import time

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

FILL_RATIO = 0.9  # For now we accept 80% fill rate
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
                    # logging.debug(f"pos: {pos} | {game_map.calculate_distance(ship.position, shipyard.position) <= 5} | {game_map[pos.x][pos.y].w}")
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
    minimum = min(0.25 * game_map.max_halite, 4 * (constants.MAX_HALITE - ship.halite_amount))
    logging.debug(f"res max: {game_map.max_halite} - minimum: {minimum}")
    current_offset = 1
    found = False
    pos = ship.position
    target = None

    # Search with an expanding ring
    while not found and current_offset <= game_map.height: # possible max search range
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

    if not target:
        target = ship.position
        logging.info("target not found!")

    else:
        logging.info(f"target found!: {target}")
    return target


def weighted_cleanup(game_map, ship, shipyard):
    # TODO: Don't do this per ship, but once per game turn and figure out positions for each ship that way
    minimum = 30
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
            cell_pos = game_map.normalize(shipyard.position + Position(*offset))
            cell = game_map[cell_pos]
            if cell.halite_amount >= minimum and not cell.is_occupied:
                targets.append(cell_pos)

            if ship.position == cell_pos:
                ship_seen = True

        if targets:
            best_target = (None, INF)  # For now best => closest
            for target in targets:
                distance = game_map.calculate_distance(ship.position, target)
                if distance < best_target[1] and distance < distance_limit:
                    best_target = (target, distance)
                    logging.debug(f"{ship.id} best_target found: {best_target}")

            if best_target[0] is not None:
                logging.debug(f"{ship.id} | Found!")
                found = True

        current_offset += 1
        if ship_seen:
            distance_limit *= 1.5

    logging.debug(f"{ship.id} ?????????: {best_target} | {current_offset} | {targets} | {found}")

    return best_target[0]


def dijkstra_a_to_b(game_map, source, target, offset=1, cheapest=True):
    if source == target:
        return Direction.Still

    dx = abs(target.x - source.x)
    dy = abs(target.y - source.y)

    xdir = 1 if target.x > source.x else -1
    ydir = 1 if target.y > source.y else -1

    # Valid x and y positions in range
    if xdir == 1:
        rx = range(source.x - offset, target.x + offset + 1)
    else:
        rx = range(target.x - offset, source.x + offset + 1)

    if ydir == 1:
        ry = range(source.y - offset, target.y + offset + 1)
    else:
        ry = range(target.y - offset, source.y + offset + 1)

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
                "previous": None
            }
            queue.append(position)

    # Dijkstra
    #   Calculating the cheapest path to each respective node in the grid
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

                # Calculate the cost of traveling to that neighbour
                if cheapest:
                    if game_map[pos].is_occupied:
                        neighbour_weight = INF
                    else:
                        neighbour_weight = neighbour.halite_amount
                else:
                    if game_map[pos].is_occupied:
                        neighbour_weight = 1
                    else:
                        neighbour_weight = INF - neighbour.halite_amount
                # neighbour_weight = neighbour.halite_amount if not game_map[pos].is_occupied else INF
                # logging.debug(f"Neighbour: {pos} | {neighbour_weight} | occupied: {game_map[pos].is_occupied} | ship id {game_map[pos].ship}")

                # Calculate the distance of the path to the neighbour
                dist_to_neighbour = distance_map[node]["distance"] + neighbour_weight

                # If path is shorter than any other current path to that neighbour, then we update the path to that node
                if dist_to_neighbour < distance_map[pos]["distance"]:
                    distance_map[pos]["distance"] = dist_to_neighbour
                    distance_map[pos]["previous"] = node

    # Traverse from the target to the source by following all "previous" nodes that we calculated
    path_node = target
    while path_node != source:
        prev_path_node = distance_map[path_node]["previous"]
        if prev_path_node == source:
            for d in Direction.get_all_cardinals(): #.values():
                if game_map.normalize(source.directional_offset(d)) == path_node:
                    return d

        path_node = prev_path_node


def safe_greedy_move(game_map, source, target):
    safe_moves = []

    # Evaluate if standing still is safe
    if game_map.position_is_safe(source):
        safe_moves.append(Direction.Still)

    # Evaluate if any of the cardinal directions are safe
    for direction in Direction.get_all_cardinals():
        new_position = game_map.normalize(source.directional_offset(direction))
        if game_map.position_is_safe(new_position):
            safe_moves.append(direction)

    # The scenario where we are fucked
    if not safe_moves:
        return Direction.Still

    # Else we greedily check which move brings us closest to our target
    closest_to_target = (None, INF)
    for direction in safe_moves:
        position = game_map.normalize(source.directional_offset(direction))
        distance = game_map.calculate_distance(position, target)
        if distance < closest_to_target[1]:
            closest_to_target = (direction, distance)

    # Returns direction
    return closest_to_target[0]


def distance_match(source, targets):
    target = None
    dist = 0

    for t in targets:
        t_dist = game_map.calculate_distance(source, t)
        if game_map.calculate_distance(source, t) > dist:
            dist = t_dist
            target = t

    logging.debug(f"targets A: {targets}")
    targets.pop(targets.index(target))
    logging.debug(f"targets B: {targets}")
    return targets, target


""" <<<Game Loop>>> """
while True:

    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    me = game.me
    game_map = game.game_map

    # Build the RESOURCE TREE
    logging.debug("building")
    tree = ResourceTree(game_map, game_map.total_halite)

    # tree_viz = ""
    # for row in tree.as_array():
    #     for val in row:
    #         tree_viz += '{:4}'.format(val)
    #     tree_viz += '\n'
    #
    # logging.debug(tree_viz)
    # logging.debug("--------------------------------------------")

    # tree._debug()
    # time.sleep(2)
    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    ship_queue = me.get_ships()
    command_queue = []

    new_ship_positions = []
    ship_position_map = []  # (ship, target)

    # First we check if we are at the end of the game and the ship needs to start coming home
    ship_queue_tmp = []
    for ship in ship_queue:
        if ship.should_turn_in(game_map, game.turn_number) and ship.can_move(game_map[ship]):
            target = me.shipyard.position
            new_dir = dijkstra_a_to_b(game_map, ship.position, target)

            # Final check if the move is actually safe as Dijkstra can result in an unsafe move when 1 unit away from target
            new_position = game_map.normalize(ship.position.directional_offset(new_dir))
            if not game_map.position_is_safe(new_position) and not new_position == me.shipyard.position:
                new_dir = safe_greedy_move(game_map, ship.position, target)
                new_position = game_map.normalize(ship.position.directional_offset(new_dir))

            # Already move the ship in the game map to help prevent collisions
            logging.debug(f"SHIP {ship.id} WANTS TO MOVE: {ship.position} - {new_dir}")
            game_map[ship].mark_safe()
            game_map[new_position].mark_unsafe(ship)

            # And finally add the command to the queue
            command_queue.append(ship.move(new_dir))
        else:
            ship_queue_tmp.append(ship)
    ship_queue = ship_queue_tmp

    # Evaluated all the ships that can't move
    ship_queue_tmp = []
    for ship in ship_queue:
        current_cell = game_map[ship]
        if not ship.can_move(current_cell):
            new_dir = Direction.Still
            command_queue.append(ship.move(new_dir))
        else:
            ship_queue_tmp.append(ship)
    ship_queue = ship_queue_tmp

    # Then evaluate all ships that don't want to move and are in a safe spot
    ship_queue_tmp = []
    for ship in ship_queue:
        current_cell = game_map[ship]
        logging.debug(f"SHOULD MOVE: {not ship.should_move(current_cell)} | {game_map.position_is_safe(current_cell)}")
        if not ship.should_move(current_cell) and not game_map.enemy_is_close(current_cell):
            new_dir = Direction.Still
            logging.debug(f"SHIP {ship.id} WANTS TO STAY: {ship.position} - {new_dir}")
            command_queue.append(ship.move(new_dir))
        else:
            ship_queue_tmp.append(ship)
    ship_queue = ship_queue_tmp

    # Finally start resolving all ships that CAN move, and want or should move
    target_candidates = []

    for _ in range(len(ship_queue)):
        logging.debug("--------------------------")
        logging.debug(f"shipyard pos: {me.shipyard.position}")
        target_candidates.append(tree.follow_max(game_map, me.shipyard.position))
        logging.debug(f"targets: {target_candidates}")
        logging.debug("--------------------------")

    # tree_viz = ""
    # for row in tree.as_array():
    #     for val in row:
    #         tree_viz += '{:4}'.format(val)
    #     tree_viz += '\n'
    #
    # logging.debug(tree_viz)
    # logging.debug("--------------------------------------------")
    #
    #
    #
    # a, b, c, d = tree.children_as_array()
    #
    # for each in [a, b, c, d]:
    #     c_viz = ""
    #     for row in each:
    #         for val in row:
    #             c_viz += '{:4}'.format(val)
    #         c_viz += '\n'
    #     logging.debug(c_viz)
    #     logging.debug("--------------------------------------------")
    #
    # time.sleep(3)

    for ship in ship_queue:
        current_cell = game_map[ship]
        if ship.halite_amount >= FILL_RATIO * constants.MAX_HALITE:
            # Case: We need to turn in our halite
            target = me.shipyard.position
            cheapest = True
        else:
            # Case: Gather more resources
            target_candidates, target = distance_match(ship.position, target_candidates)
            cheapest = False
            # target = weighted_cleanup(game_map, ship, me.shipyard)

        new_dir = dijkstra_a_to_b(game_map, ship.position, target, cheapest=cheapest)

        # Final check if the move is actually safe as Dijkstra can result in an unsafe move when 1 unit away from target
        new_position = game_map.normalize(ship.position.directional_offset(new_dir))
        if not game_map.position_is_safe(new_position):
            new_dir = safe_greedy_move(game_map, ship.position, target)
            new_position = game_map.normalize(ship.position.directional_offset(new_dir))

        # Already move the ship in the game map to help prevent collisions
        logging.debug(f"SHIP {ship.id} WANTS TO MOVE: {ship.position} - {new_dir}")
        game_map[ship].mark_safe()
        game_map[new_position].mark_unsafe(ship)

        # And finally add the command to the queue
        command_queue.append(ship.move(new_dir))

    # Spawning a ship
    if game.turn_number <= constants.MAX_TURNS - 150 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied and game_map.total_halite / max(game_map.ship_count, 1) > 4000 and game_map.ship_count < 37:
        command_queue.append(me.shipyard.spawn())

    # if game.turn_number > 10:
    #     time.sleep(2)
    # Sending moves to end the turn
    game.end_turn(command_queue)
