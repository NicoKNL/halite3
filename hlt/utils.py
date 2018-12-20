import numpy as np
import os
from hlt.positionals import Position


def save_data(file_name, **kwargs):
    np.savez(f"{os.path.join(os.getcwd(), 'datasets')}{os.sep}{file_name}.npz", **kwargs)


def collect_data(file_name):
    global game_map
    global me

    halite = []
    distance = []
    penalized = []

    for y in range(game_map.height):
        halite_row = []
        distance_row = []
        penalized_row = []
        for x in range(game_map.width):
            pos = Position(x, y)
            cell = game_map[pos]

            # Halite amount
            halite_row.append(cell.halite_amount)

            # Distance
            cell_dist = max(0.00000001, game_map.calculate_distance(me.shipyard.position, pos) / game_map.width)
            distance_row.append(cell_dist)

            # Halite penalized for distance
            penalized_halite = cell.halite_amount * (1 / cell_dist)  #(1 - pow(cell_dist, 0.1))
            penalized_row.append(penalized_halite)

        # appending the rows to the main data arrays
        halite.append(halite_row)
        distance.append(distance_row)
        penalized.append(penalized_row)

    np.savez(f"{os.path.join(os.getcwd(), 'datasets')}{os.sep}{file_name}.npz", halite=halite, distance=distance, penalized=penalized)
