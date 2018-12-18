import queue
import logging
from math import floor

from . import constants
from .entity import Entity, Shipyard, Ship, Dropoff
from .player import Player
from .positionals import Direction, Position
from .common import read_input
from .task import Task

class MapCell:
    """A cell on the game map."""
    def __init__(self, position, halite_amount):
        self.position = position
        self.halite_amount = halite_amount
        self.ship = None
        self.structure = None
        self.claim = None

    @property
    def is_claimed(self):
        return self.claim is not None

    @property
    def is_empty(self):
        """
        :return: Whether this cell has no ships or structures
        """
        return self.ship is None and self.structure is None

    @property
    def is_occupied(self):
        """
        :return: Whether this cell has any ships
        """
        return self.ship is not None

    @property
    def has_structure(self):
        """
        :return: Whether this cell has any structures
        """
        return self.structure is not None

    @property
    def structure_type(self):
        """
        :return: What is the structure type in this cell
        """
        return None if not self.structure else type(self.structure)

    def release_claim(self):
        self.claim = None

    def mark_claimed(self, ship):
        self.claim = ship

    def mark_safe(self):
        self.ship = None

    def mark_unsafe(self, ship):
        """
        Mark this cell as unsafe (occupied) for navigation.

        Use in conjunction with GameMap.naive_navigate.
        """
        self.ship = ship

    def can_move(self):
        if not self.ship:
            raise RuntimeError("No ship in this cell!")
        cost = floor(0.10 * self.halite_amount)
        if cost > self.ship.halite_amount:
            return False
        return True

    def should_move(self, minimum):
        if self.halite_amount >= minimum and self.ship.halite_amount < constants.MAX_HALITE:
            return False
        return True

    def __eq__(self, other):
        return self.position == other.position

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return 'MapCell({}, halite={})'.format(self.position, self.halite_amount)


class GameMap:
    """
    The game map.

    Can be indexed by a position, or by a contained entity.
    Coordinates start at 0. Coordinates are normalized for you
    """
    def __init__(self, cells, width, height, my_id):
        self.width = width
        self.height = height
        self._cells = cells

        self.me = my_id
        self.max_halite = 0
        self.total_halite = 0

    def __getitem__(self, location):
        """
        Getter for position object or entity objects within the game map
        :param location: the position or entity to access in this map
        :return: the contents housing that cell or entity
        """
        if isinstance(location, Position):
            location = self.normalize(location)
            return self._cells[location.y][location.x]
        elif isinstance(location, Entity):
            return self._cells[location.position.y][location.position.x]
        return None

    def calculate_distance(self, source, target):
        """
        Compute the Manhattan distance between two locations.
        Accounts for wrap-around.
        :param source: The source from where to calculate
        :param target: The target to where calculate
        :return: The distance between these items
        """
        source = self.normalize(source)
        target = self.normalize(target)
        resulting_position = abs(source - target)
        return min(resulting_position.x, self.width - resulting_position.x) + \
            min(resulting_position.y, self.height - resulting_position.y)

    def normalize(self, position):
        """
        Normalized the position within the bounds of the toroidal map.
        i.e.: Takes a point which may or may not be within width and
        height bounds, and places it within those bounds considering
        wraparound.
        :param position: A position object.
        :return: A normalized position object fitting within the bounds of the map
        """
        return Position(position.x % self.width, position.y % self.height)

    @staticmethod
    def _get_target_direction(source, target):
        """
        Returns where in the cardinality spectrum the target is from source. e.g.: North, East; South, West; etc.
        NOTE: Ignores toroid
        :param source: The source position
        :param target: The target position
        :return: A tuple containing the target Direction. A tuple item (or both) could be None if within same coords
        """
        return (Direction.South if target.y > source.y else Direction.North if target.y < source.y else None,
                Direction.East if target.x > source.x else Direction.West if target.x < source.x else None)

    def get_unsafe_moves(self, source, destination):
        """
        Return the Direction(s) to move closer to the target point, or empty if the points are the same.
        This move mechanic does not account for collisions. The multiple directions are if both directional movements
        are viable.
        :param source: The starting position
        :param destination: The destination towards which you wish to move your object.
        :return: A list of valid (closest) Directions towards your target.
        """
        source = self.normalize(source)
        destination = self.normalize(destination)
        possible_moves = []
        distance = abs(destination - source)
        y_cardinality, x_cardinality = self._get_target_direction(source, destination)

        if distance.x != 0:
            possible_moves.append(x_cardinality if distance.x < (self.width / 2)
                                  else Direction.invert(x_cardinality))
        if distance.y != 0:
            possible_moves.append(y_cardinality if distance.y < (self.height / 2)
                                  else Direction.invert(y_cardinality))
        return possible_moves

    def register_move(self, ship, direction):
        new_position = ship.position.directional_offset(direction)

        if self[new_position].has_structure and ship.task == Task.Suicide:
            return

        if self[new_position].is_claimed: # and not direction == Direction.Still:
            pass
          # logging.debug(f"    #{ship.id} is trying to claim: {new_position} but already claimed by: {self[new_position].claim}")
            # raise RuntimeError("Already claimed!")
        self[new_position].mark_claimed(ship)

    def naive_navigate(self, ship, destination):
        """
        Returns a singular safe move towards the destination.

        :param ship: The ship to move.
        :param destination: Ending position
        :return: A direction.
        """
        # No need to normalize destination, since get_unsafe_moves
        # does that
        for direction in self.get_unsafe_moves(ship.position, destination):
            target_pos = ship.position.directional_offset(direction)
            if not self[target_pos].is_occupied:
                self[target_pos].mark_unsafe(ship)
                return direction

        return Direction.Still

    def navigate(self, source, target, offset=1, ignore_dropoff=False, cheapest=True):
        direction = self.dijkstra_a_to_b(source, target, offset=offset, cheapest=cheapest)
        new_position = source.directional_offset(direction)
      # logging.debug(f"#{self[source].ship.id} || source: {source} and target: {target} and new position: {new_position}")

        structures = self.get_neighbouring_structures(new_position, friendly=True, enemy=ignore_dropoff)
        structure_positions = [s.position for s in structures]

        # Allows for the endgame crashing on the dropoff, and ignore enemies when they are on my dropoff
        if new_position in structure_positions:
          # logging.debug(f"new position in structure positions")
          # logging.debug(self[source].ship.task)
          # logging.debug(ignore_dropoff)
            if ignore_dropoff or (self[new_position].is_occupied and self[new_position].ship.owner != self.me):
              # logging.debug(f"ignore dropoff: {ignore_dropoff} or new position is occupied and the ship is NOT owned by me")
                return direction
            elif not self[new_position].is_claimed:
              # logging.debug(f"Position just isn't claimed")
                return direction
            else:
              # logging.debug(f"I need to make a greedy move")
                return self.safe_greedy_move(source, target)

        # In order to ignore the cheese strategy where they wait in front of your dropoff
        structure_cardinals = []
        for s in structure_positions:
            structure_cardinals.extend(s.get_surrounding_cardinals())

        if self[new_position].is_occupied:
          # logging.debug(f"new position is occupied")

            if new_position in structure_cardinals:
              # logging.debug(f"new position in structure cardinals")
                if self[new_position].ship.owner != self.me and not self[new_position].is_claimed:
                  # logging.debug(f"returning same direction")
                    return direction
                elif self[new_position].ship.owner == self.me and not self[new_position].is_claimed:
                  # logging.debug(f"I own the ship there and the position is not yet claimed")
                    return direction
                else:
                  # logging.debug(f"returning greedy move")
                    return self.safe_greedy_move(source, target)
            else:
                if self[new_position].ship.owner == self.me and not self[new_position].is_claimed:
                  # logging.debug(f"I own that ship and the position is NOT claimed")
                    return direction
                elif self[source].ship.task == Task.EndgameHunt and not self[new_position].is_claimed:
                  # logging.debug(f"Ships task is EngameHunt and the new position is NOT claimed")
                    return direction
                elif self[new_position].ship.owner == self.me and not self[new_position].is_claimed:
                  # logging.debug(f"I own the ship there and the position is not yet claimed")
                    return direction
                else:
                  # logging.debug(f"Making a safe greedy move")
                    return self.safe_greedy_move(source, target)
        else:
          # logging.debug(f"new position is NOT occupied")

            if not self[new_position].is_claimed:
              # logging.debug(f"new position is NOT claimed")
                return direction
            else:
              # logging.debug(f"new position is claimed however")
                return self.safe_greedy_move(source, target)

    def get_neighbouring_structures(self, position, friendly=True, enemy=False):
        positions = position.get_plus_cardinals()
        structures = []
        for pos in positions:
            if self[pos].has_structure:
                structure = self[pos].structure
                if (friendly and structure.owner == self.me) or (enemy and structure.owner != self.me):
                    structures.append(structure)
        return structures

    def dijkstra_a_to_b(self, source, target, offset=1, cheapest=True):
        if source == target:
            return Direction.Still

        min_x = min(source.x, target.x)
        max_x = max(source.x, target.x)

        min_y = min(source.y, target.y)
        max_y = max(source.y, target.y)

        dx = max_x - min_x
        dy = max_y - min_y

        dx_wrapped = self.width - dx
        dy_wrapped = self.height - dy

        if dx < dx_wrapped:
            rx = range(min_x - offset, max_x + offset + 1)
        else:
            rx = range(max_x - offset, min_x + self.width + offset + 1)

        if dy < dy_wrapped:
            ry = range(min_y - offset, max_y + offset + 1)
        else:
            ry = range(max_y - offset, min_y + self.height + offset + 1)

        rx = [x % self.width for x in rx]
        ry = [y % self.height for y in ry]

        # initialize distances
        distance_map = {
            source: {
                "distance": 0,
                "previous": None}
        }
        queue = [source]

        for x in rx:
            for y in ry:
                pos = Position(x, y)
                if pos == source:
                    continue

                distance_map[pos] = {
                    "distance": constants.INF * 32,
                    "previous": None
                }
                queue.append(pos)

        # Dijkstra
        #   Calculating the cheapest path to each respective node in the grid
        while len(queue):
            # Take the item in the queue with the lowest distance and remove it from the queue
            node = sorted(queue, key=lambda position: distance_map[position]["distance"])[0]
            queue.pop(queue.index(node))

            # For each neighbouring position
            for pos in node.get_surrounding_cardinals():
                # validate cell is within search bounds
                if pos.x in rx and pos.y in ry:
                    neighbour = self[pos]

                    # Calculate the cost of traveling to that neighbour
                    if (neighbour.is_occupied and neighbour.ship.owner != self.me) or neighbour.is_claimed:
                        neighbour_weight = constants.INF
                    else:
                        if cheapest:
                            neighbour_weight = neighbour.halite_amount
                        else:
                            neighbour_weight = max(1, constants.MAX_HALITE - neighbour.halite_amount)
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
                for d in Direction.get_all_cardinals():  # .values():
                    if source.directional_offset(d) == path_node:
                        return d

            path_node = prev_path_node

    def safe_greedy_move(self, source, target):
        safe_moves = []

        if not self[source].is_claimed:
            safe_moves.append(Direction.Still)

        # Evaluate if any of the cardinal directions are safe
        for direction in Direction.get_all_cardinals():
            new_position = self.normalize(source.directional_offset(direction))
            if not self[new_position].is_claimed:
                if (self[new_position].is_occupied and self[new_position].ship.owner == self.me) or not self[new_position].is_occupied:
                    safe_moves.append(direction)

        # The scenario where we are fucked
        if not safe_moves:
          # logging.debug(f"NO SAFE MOVES: {source}")
            self[source].release_claim()
            return Direction.Still

        # Else we greedily check which move brings us closest to our target
        closest_to_target = (None, constants.INF)
        for direction in safe_moves:
            position = source.directional_offset(direction)
            distance = self.calculate_distance(position, target)
            if distance < closest_to_target[1]:
                closest_to_target = (direction, distance)

        # Returns direction
        return closest_to_target[0]

    def reset_claims(self):
        for y in range(self.height):
            for x in range(self.width):
                self[Position(x, y)].release_claim()

    def clear_cheese(self):
        for y in range(self.height):
            for x in range(self.width):
                position = Position(x, y)
                cell = self[position]
                if cell.has_structure and cell.structure.owner == self.me:
                  # logging.debug(f"Found structure of myself!")
                    surroundings = position.get_3x3()
                  # logging.debug(f"surroundings: {surroundings}")
                    for neighbour_pos in surroundings:
                        neighbour = self[neighbour_pos]
                        if neighbour.is_occupied and neighbour.ship.owner != self.me:
                          # logging.debug(f"found ship: {neighbour.ship} || {neighbour.ship.owner} || {self.me}")
                            neighbour.mark_safe()

    @staticmethod
    def _generate(my_id):
        """
        Creates a map object from the input given by the game engine
        :return: The map object
        """
        map_width, map_height = map(int, read_input().split())
        game_map = [[None for _ in range(map_width)] for _ in range(map_height)]
        for y_position in range(map_height):
            cells = read_input().split()
            for x_position in range(map_width):
                game_map[y_position][x_position] = MapCell(Position(x_position, y_position,
                                                                    normalize=False),
                                                           int(cells[x_position]))
        return GameMap(game_map, map_width, map_height, my_id)

    def _update(self):
        """
        Updates this map object from the input given by the game engine
        :return: nothing
        """
        # Mark cells as safe for navigation (will re-mark unsafe cells
        # later)
        for y in range(self.height):
            for x in range(self.width):
                self[Position(x, y)].ship = None

        for _ in range(int(read_input())):
            cell_x, cell_y, cell_energy = map(int, read_input().split())
            self[Position(cell_x, cell_y)].halite_amount = cell_energy

        # Recalculating max_halite in field
        self.max_halite = 0  # Reset
        self.total_halite = 0  # Reset

        for y in range(self.height):
            for x in range(self.width):
                self.max_halite = max(self.max_halite, self[Position(x, y)].halite_amount)
                self.total_halite += self[Position(x, y)].halite_amount
