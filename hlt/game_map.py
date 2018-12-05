import queue

from . import constants
from .entity import Entity, Shipyard, Ship, Dropoff
from .player import Player
from .positionals import Direction, Position
from .common import read_input
import logging

class MapCell:
    """A cell on the game map."""
    def __init__(self, position, halite_amount):
        self.position = position
        self.halite_amount = halite_amount
        self.travel_weight = 0
        self.distance_multiplier = 1
        self.bonus = False
        self.ship = None
        self.structure = None

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

    def mark_unsafe(self, ship):
        """
        Mark this cell as unsafe (occupied) for navigation.

        Use in conjunction with GameMap.naive_navigate.
        """
        self.ship = ship

    def mark_safe(self):
        self.ship = None

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
    def __init__(self, cells, width, height, me):
        self.me = me  # Player object
        self.width = width
        self.height = height
        self._cells = cells
        self._move_map = None

        self.max_halite = 0
        self.total_halite = 0
        self.ship_count = 0

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

    def position_is_safe(self, source):
        if not isinstance(source, Position):
            source = source.position

        if self[source].is_occupied:
            if source == self.me.shipyard.position and self[source].ship.owner != self.me.id:
                return True
            else:
                return False

        for pos in source.get_surrounding_cardinals():
            if self[pos].is_occupied:
                if self[pos].ship.owner != self.me.id:
                    return False
        return True

    def enemy_is_close(self, source):
        if not isinstance(source, Position):
            source = source.position

        for pos in source.get_surrounding_cardinals():
            if self[pos].is_occupied:
                if self[pos].ship.owner != self.me.id:
                    return True
        return False

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

    @staticmethod
    def _generate(me):
        """
        Creates a map object from the input given by the game engine
        :return: The map object
        """
        map_width, map_height = map(int, read_input().split())
        game_map = [[None for _ in range(map_width)] for _ in range(map_height)]
        for y_position in range(map_height):
            cells = read_input().split()
            for x_position in range(map_width):
                game_map[y_position][x_position] = MapCell(Position(x_position, y_position),
                                                           int(cells[x_position]))
        return GameMap(game_map, map_width, map_height, me)

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
                self[Position(x, y)].bonus = False  # Reset bonus

        for _ in range(int(read_input())):
            cell_x, cell_y, cell_energy = map(int, read_input().split())
            self[Position(cell_x, cell_y)].halite_amount = cell_energy
            logging.debug(f"({cell_x}, {cell_y}): {cell_energy}")

        # Recalculating max_halite in field
        self.max_halite = 0  # Reset
        self.total_halite = 0  # Reset
        logging.debug(f"Resetting max halite: {self.max_halite}")
        for y in range(self.height):
            for x in range(self.width):
                self.max_halite = max(self.max_halite, self[Position(x, y)].halite_amount)
                self.total_halite += self[Position(x, y)].halite_amount

        logging.debug(f"Calculated max halite: {self.max_halite}")

    def _update_bonuses(self):
        offsets = [(x, y) for x in range(-4, 5) for y in range(-4, 5)]
        for y in range(self.height):
            for x in range(self.width):
                enemy_ships = 0
                for offset in offsets:
                    cell = self[Position(x + offset[0], y + offset[1])]
                    if cell.is_occupied:
                        if cell.ship.owner != self.me:
                            enemy_ships += 1

                if enemy_ships >= 2:
                    self[Position(x, y)].bonus = True

    def _update_distance_multipliers(self):
        for y in range(self.height):
            for x in range(self.width):
                cell = self[Position(x, y)]
                # TODO: Also consider dropoffs
                distance = self.calculate_distance(cell.position, self.me.shipyard.position)
                cell.distance_multiplier = distance

    def _update_unsafe_cells(self):
        # Construct array with all shipyard related positions to prevent getting owned by a cheese strat
        # TODO: Include dropoffs when implemented
        shipyard_positions = self.me.shipyard.position.get_surrounding_cardinals()
        shipyard_positions.append(self.me.shipyard.position)

        self.ship_count = 0  # Reset

        # Figure out where the enemy ships are
        enemy_ships = []
        for y in range(self.height):
            for x in range(self.width):
                if self[Position(x, y)].is_occupied:
                    ship = self[Position(x, y)].ship
                    if ship.owner != self.me.id and ship.position not in shipyard_positions:
                        enemy_ships.append(ship)

                    if ship.owner == self.me.id:
                        self.ship_count += 1

        # Mark the areas around the relevant enemy ships as containing an enemy as well
        offsets = [(x, y) for x in range(-1, 2) for y in range(-1, 2)]
        for ship in enemy_ships:
            for offset in offsets:
                position = self.normalize(Position(x + offset[0], y + offset[1]))
                # Only mark positions which are not already marked as occupied as I do not want to override my ships
                if not self[position].is_occupied:
                    self[position].mark_unsafe(ship)

    def _update_move_map(self):
        move_map = [[None for x in range(self.width)] for y in range(self.height)]
        for y in range(self.height):
            for x in range(self.width):
                cell = self[Position(x, y)]
                if cell.is_occupied:
                    ship = cell.ship
                    if (ship.owner == self.me.id and not ship.can_move(cell)) or ship.owner != self.me.id:
                        move_map[y][x] = ship
        self._move_map = move_map

    def register_move(self, ship, target):
        self._move_map[target.y][target.x] = ship