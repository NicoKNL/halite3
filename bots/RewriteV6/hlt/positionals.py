from . import commands
from . import constants
import logging

class Direction:
    """
    Holds positional tuples in relation to cardinal directions
    """
    North = (0, -1)
    South = (0, 1)
    East = (1, 0)
    West = (-1, 0)

    Still = (0, 0)

    @staticmethod
    def get_all_cardinals():
        """
        Returns all contained items in each cardinal
        :return: An array of cardinals
        """
        return [Direction.North, Direction.South, Direction.East, Direction.West]

    @staticmethod
    def convert(direction):
        """
        Converts from this direction tuple notation to the engine's string notation
        :param direction: the direction in this notation
        :return: The character equivalent for the game engine
        """
        if direction == Direction.North:
            return commands.NORTH
        if direction == Direction.South:
            return commands.SOUTH
        if direction == Direction.East:
            return commands.EAST
        if direction == Direction.West:
            return commands.WEST
        if direction == Direction.Still:
            return commands.STAY_STILL
        else:
            raise IndexError

    @staticmethod
    def invert(direction):
        """
        Returns the opposite cardinal direction given a direction
        :param direction: The input direction
        :return: The opposite direction
        """
        if direction == Direction.North:
            return Direction.South
        if direction == Direction.South:
            return Direction.North
        if direction == Direction.East:
            return Direction.West
        if direction == Direction.West:
            return Direction.East
        if direction == Direction.Still:
            return Direction.Still
        else:
            raise IndexError


class Position:
    def __init__(self, x, y, normalize=True):
        self.x = x
        self.y = y

        if normalize:
            self.normalize()

    def normalize(self):
        self.x = self.x % constants.WIDTH
        self.y = self.y % constants.HEIGHT

    def directional_offset(self, direction):
        """
        Returns the position considering a Direction cardinal tuple
        :param direction: the direction cardinal tuple
        :return: a new position moved in that direction
        """
        return self + Position(*direction)

    def get_surrounding_cardinals(self):
        """
        :return: Returns a list of all positions around this specific position in each cardinal direction
        """
        return [self.directional_offset(current_direction) for current_direction in Direction.get_all_cardinals()]

    def get_plus_cardinals(self):
        positions = [self]
        positions.extend(self.get_surrounding_cardinals())
        return positions

    def get_3x3(self):
        positions = self.get_plus_cardinals()
        positions.extend([
            self + Position(-1, -1),
            self + Position(-1, 1),
            self + Position(1, -1),
            self + Position(1, 1)
        ])
        return positions

    def get_offset_ring(self, offset=1):
        offsets = list(range(-offset, offset + 1))
        ring = [(x, y) for x in offsets for y in offsets if (abs(x) == offset or abs(y) == offset)]
        position_ring = [self + Position(*offset) for offset in ring]
        logging.debug(f"RING RING: {position_ring}")
        return position_ring

    def __add__(self, other):
        return Position(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Position(self.x - other.x, self.y - other.y)

    def __iadd__(self, other):
        self.x += other.x
        self.y += other.y
        self.normalize()
        return self

    def __isub__(self, other):
        self.x -= other.x
        self.y -= other.y
        self.normalize()
        return self

    def __abs__(self):
        return Position(abs(self.x), abs(self.y))

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "{}({}, {})".format(self.__class__.__name__,
                                   self.x,
                                   self.y)

    def __hash__(self):
        return hash((self.x, self.y))
