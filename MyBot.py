import logging
import time
import os
import numpy as np
import random
from math import ceil, floor

import hlt
from hlt.task import Task
from hlt import constants
from hlt.positionals import Direction, Position
from hlt.utils import save_data, collect_data

game = hlt.Game()  # This game object contains the initial game state.

###################################
#                                 #
#       Pre-processing area       #
#                                 #
###################################

# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.


##########################################
#                                        #
#       End of Pre-processing area       #
#                                        #
##########################################

game.ready("DEV")  # Starts the 2 second per turn timer


def swarm_closest_enemy_dropoff(ships):
    matches = dict()

    for ship in ships:
        closest_enemy_dropoff = sorted(game_map.enemy_dropoffs, key=lambda d, ship=ship, game_map=game_map: game_map.calculate_distance(d, ship.position))[0]
        ring_positions = closest_enemy_dropoff.get_offset_ring(offset=2)
        matches[ship] = random.choice(ring_positions)

    return matches


def hunt_close_enemy2(ships):
    global game_map
    matches = dict()

    # Search with an expanding ring
    targets = []

    for y in range(game_map.height):
        for x in range(game_map.width):

            pos = Position(x, y)
            cell = game_map[pos]
            if cell.is_occupied and cell.ship.owner != me.id and cell.ship.halite_amount > 200:
                targets.append(cell)

    # Match all ships with all targets
    for ship in ships:
        best_target = (None, constants.INF)  # For now best => closest
        for cell in targets:
            distance = game_map.calculate_distance(ship.position, cell.position)
            if distance < best_target[1]:
                best_target = (cell, distance)

        if best_target[0] is not None:
            matches[ship] = best_target[0].position
            targets.pop(targets.index(best_target[0]))
        else:
            matches[ship] = None

    return matches


def weighted_cleanup2(ships):
    global game_map
    global me
    matches = dict()

    targets = []
    for y in range(game_map.height):
        for x in range(game_map.width):
            pos = Position(x, y)
            cell = game_map[pos]
            # if cell.halite_amount >= minimum and not cell.is_occupied:
            if not cell.is_occupied and not cell.is_claimed:
                cell_distance = max(1, game_map.calculate_distance(me.shipyard.position, pos))
                targets.append(
                    (cell, cell.halite_amount * (1 / cell_distance))
                )

    targets = sorted(targets, key=lambda t: t[1], reverse=True)[0: len(ships) * 2]
    # Match all ships with all targets
    for ship in ships:
        best_target = (None, constants.INF)  # For now best => closest
        for target in targets:
            cell, _ = target
            distance = game_map.calculate_distance(ship.position, cell.position)
            if distance < best_target[1]:
                best_target = (cell, distance)

        if best_target[0] is not None:
            matches[ship] = best_target[0].position
            targets.pop(targets.index(target))
            if best_target[1] >= game_map.width / 2:
                logging.debug(f"Traveling at least half the map: {best_target[1]}")
        else:
            matches[ship] = None

    return matches


def evaluate_can_move(ships):
    global game_map

    ignored_ships = []
    for ship in ships:
        if not game_map[ship].can_move():
            game_map.register_move(ship, Direction.Still)
        else:
            ignored_ships.append(ship)

    return ignored_ships


def evaluate_should_move(ships):
    global game_map

    minimum = 50
    average_halite_on_map = game_map.total_halite / (game_map.width * game_map.height)
    while average_halite_on_map <= minimum and minimum != 0:
        minimum /= 2

    ignored_ships = []
    for ship in ships:
        if not ship.task in [Task.EndgameHunt, Task.Deposit] and not game_map[ship].should_move(minimum):
            game_map.register_move(ship, Direction.Still)
        else:
            ignored_ships.append(ship)

    return ignored_ships


def evaluate_other(ships):
    global game_map

    first_movers, gather_ships, deposit_ships, suicide_ships, hunting_ships = resolve_tasks(ships)

    first_mover_targets = []
    if first_movers:
        first_mover_targets = weighted_cleanup2(first_movers)
    for ship in first_movers:
      # logging.debug(f"# {ship.id} ---------------- first movers")
        target = first_mover_targets[ship]

        if target is None:
            direction = Direction.Still
        else:
            direction = game_map.navigate(ship.position, target, offset=0, cheapest=False)
        # direction = game_map.safe_adjacent_move(ship.position)

      # logging.debug(f"DIRECTION FIRST MOVER: {direction}")
        game_map.register_move(ship, direction)

    for ship in sorted(deposit_ships,
                       key=lambda ship: game_map.calculate_distance(me.shipyard.position, ship.position),
                       reverse=False):
      # logging.debug(f"# {ship.id} ---------------- deposit ")
        target = me.shipyard.position
        direction = game_map.navigate(ship.position, target, offset=0)
        game_map.register_move(ship, direction)

    for ship in sorted(suicide_ships,
                       key=lambda ship: game_map.calculate_distance(me.shipyard.position, ship.position),
                       reverse=False):
      # logging.debug(f"# {ship.id} ---------------- suicide ")

        target = me.shipyard.position
        direction = game_map.navigate(ship.position, target, offset=1, ignore_dropoff=True)
        game_map.register_move(ship, direction)

    attack_targets = dict()
    if hunting_ships:
        attack_targets = swarm_closest_enemy_dropoff(hunting_ships)

    for ship in sorted(hunting_ships,
                       key=lambda ship: game_map.calculate_distance(me.shipyard.position, ship.position),
                       reverse=False):
      # logging.debug(f"# {ship.id} ---------------- hunting ")

        target = attack_targets[ship]

        if target is None:
            direction = Direction.Still
        else:
            direction = game_map.navigate(ship.position, target, offset=1, ignore_enemies=True)
        game_map.register_move(ship, direction)

    targets = []
    if gather_ships:
        targets = weighted_cleanup2(gather_ships)
    for ship in sorted(gather_ships,
                       key=lambda ship: game_map.calculate_distance(me.shipyard.position, ship.position),
                       reverse=True):
        # target = ship.position + Position(5, 5)  # Target to the north
        target = targets[ship]
        # logging.debug(f"TARGET: {target}")
        if target is None:
            direction = Direction.Still
        else:
            direction = game_map.navigate(ship.position, target, offset=1, cheapest=False)
        game_map.register_move(ship, direction)


def is_in_endgame(ship, cutoff):
    if ship.task == Task.EndgameHunt:
        return True

    turns_remaining = constants.MAX_TURNS - game.turn_number
    homing_dist = game_map.calculate_distance(me.shipyard.position, ship.position)
    estimated_homing_time = homing_dist + 6 + ceil(len(me.get_ships()) / 9)

    closest_enemy_dropoff = sorted(game_map.enemy_dropoffs, key=lambda d, ship=ship, game_map=game_map: game_map.calculate_distance(d, ship.position))[0]
    attack_dist = game_map.calculate_distance(closest_enemy_dropoff, ship.position)
    estimated_attacking_time = attack_dist + 4 + ceil(len(me.get_ships()) / 9)

    if estimated_attacking_time >= turns_remaining and ship.halite_amount <= cutoff:
        return True
    elif estimated_homing_time >= turns_remaining:
        return True
    else:
        return False


def resolve_tasks(ships):
    global game_map
    first_movers = []
    gather_ships = []
    deposit_ships = []
    suicide_ships = []
    hunting_ships = []

    turns_remaining = constants.MAX_TURNS - game.turn_number
    for ship in ships:
        if is_in_endgame(ship, 200):
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

        elif ship.halite_amount >= 0.95 * constants.MAX_HALITE or (ship.task == Task.Deposit and ship.position != me.shipyard.position):
            ship.set_task(Task.Deposit)
            deposit_ships.append(ship)

        elif ship.position == me.shipyard.position or ship.task == Task.Gather:
            ship.set_task(Task.Gather)

            if ship.position == me.shipyard.position:
                first_movers.append(ship)
            else:
                gather_ships.append(ship)

    return first_movers, gather_ships, deposit_ships, suicide_ships, hunting_ships


def execute_moves(ships):
    command_queue = []

    for ship in ships:
        command_queue.append(ship.move(ship.next_move))

    return command_queue

""" <<<Game Loop>>> """
while True:
    start = time.time()  # For timing the loop

    game.update_frame()
    me = game.me
    game_map = game.game_map

    game_map.reset_claims()

    command_queue = []
    ships = me.get_ships()
    logging.debug(f"Number of ships: {len(ships)}")
    # if game.turn_number == 6:
    #     time.sleep(3)
    ######################################
    #       FIRST SPAWN SHIPS ASAP       #
    ######################################
    claimed_by_four = sum([game_map[p].is_claimed for p in me.shipyard.position.get_surrounding_cardinals()]) == 4
    if claimed_by_four:
        logging.debug(f"Claimed by four!")

    if not claimed_by_four and game_map.total_halite / max(len(me.get_ships()), 1) > 4000 and me.halite_amount >= constants.SHIP_COST and game.turn_number <= ceil(0.66 * constants.MAX_TURNS):
        command_queue.append(me.shipyard.spawn())
        game_map[me.shipyard].claim = True

    ships = me.get_ships()
    ships = evaluate_can_move(ships)
    ships = evaluate_should_move(ships)
    evaluate_other(ships)

    # Send your moves back to the game environment, ending this turn.
    command_queue.extend(execute_moves(me.get_ships()))
    game.end_turn(command_queue)
    logging.debug(f"{time.time() - start} seconds")






