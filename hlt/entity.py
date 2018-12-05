import abc

from . import commands, constants
from .positionals import Direction, Position
from .common import read_input

from math import floor, ceil
import logging

class Entity(abc.ABC):
    """
    Base Entity Class from whence Ships, Dropoffs and Shipyards inherit
    """
    def __init__(self, owner, id, position):
        self.owner = owner
        self.id = id
        self.position = position

    @staticmethod
    def _generate(player_id):
        """
        Method which creates an entity for a specific player given input from the engine.
        :param player_id: The player id for the player who owns this entity
        :return: An instance of Entity along with its id
        """
        ship_id, x_position, y_position = map(int, read_input().split())
        return ship_id, Entity(player_id, ship_id, Position(x_position, y_position))

    def __repr__(self):
        return "{}(id={}, {})".format(self.__class__.__name__,
                                      self.id,
                                      self.position)


class Dropoff(Entity):
    """
    Dropoff class for housing dropoffs
    """
    pass


class Shipyard(Entity):
    """
    Shipyard class to house shipyards
    """
    def spawn(self):
        """Return a move to spawn a new ship."""
        return commands.GENERATE


class Ship(Entity):
    """
    Ship class to house ship entities
    """
    def __init__(self, owner, id, position, halite_amount):
        super().__init__(owner, id, position)
        self.halite_amount = halite_amount

    @property
    def is_full(self):
        """Is this ship at max halite capacity?"""
        return self.halite_amount >= constants.MAX_HALITE

    def make_dropoff(self):
        """Return a move to transform this ship into a dropoff."""
        return "{} {}".format(commands.CONSTRUCT, self.id)

    def can_move(self, cell):
        cost = floor(0.10 * cell.halite_amount)
        logging.debug(f"can move SHIP {self.id}? cell: {cell.halite_amount} | cost: {cost} | have: {self.halite_amount}")
        if cost > self.halite_amount:
            return False
        return True

    def should_move(self, cell):
        # staying_profit = ceil(0.25 * cell.halite_amount)
        min = 30
        # if staying_profit >= floor(0.5 * 0.25 * constants.MAX_HALITE):
        if cell.halite_amount >= min and self.halite_amount < constants.MAX_HALITE:
            return False
        return True

    def in_danger(self, game_map):
        for pos in self.position.get_surrounding_cardinals():
            if game_map[pos.x][pos.y].get_entity().owner != self.owner:
                return True
        return False

    def should_turn_in(self, game_map, current_turn):
        turns_left = constants.MAX_TURNS - current_turn
        turns_needed = game_map.calculate_distance(self.position, game_map.me.shipyard.position)

        if turns_left <= turns_needed + 6:
            return True
        return False

    def move(self, game_map, direction):
        """
        Return a move to move this ship in a direction without
        checking for collisions.
        """
        new_position = game_map.normalize(self.position.directional_offset(direction))
        game_map[new_position].mark_unsafe(self)

        logging.debug(f"{new_position} is now occupied? :{game_map[new_position].is_occupied}, {id(game_map[new_position])}")

        raw_direction = direction
        if not isinstance(direction, str) or direction not in "nsewo":
            raw_direction = Direction.convert(direction)
        return "{} {} {}".format(commands.MOVE, self.id, raw_direction)

    def stay_still(self):
        """
        Don't move this ship.
        """
        return "{} {} {}".format(commands.MOVE, self.id, commands.STAY_STILL)

    @staticmethod
    def _generate(player_id):
        """
        Creates an instance of a ship for a given player given the engine's input.
        :param player_id: The id of the player who owns this ship
        :return: The ship id and ship object
        """
        ship_id, x_position, y_position, halite = map(int, read_input().split())
        return ship_id, Ship(player_id, ship_id, Position(x_position, y_position), halite)

    def __repr__(self):
        return "{}(id={}, {}, cargo={} halite)".format(self.__class__.__name__,
                                                       self.id,
                                                       self.position,
                                                       self.halite_amount)
