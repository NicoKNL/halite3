from hlt.game_map import GameMap
from hlt.positionals import Position
import logging


class ResourceTree(object):
    def __init__(self, grid, halite_amount, parent=None):
        logging.debug(grid)
        if isinstance(grid, GameMap):
            grid = grid.as_array()

        self._xrange = range(grid[0][0].position.x, grid[len(grid) - 1][len(grid) - 1].position.x)
        self._yrange = range(grid[0][0].position.y, grid[len(grid) - 1][len(grid) - 1].position.y)

        self.size = len(grid)
        self._grid = grid
        self.parent = parent
        self.children = None

        self.halite_amount = halite_amount
        self.center = self._calculate_center()
        self._construct_children()
        # self._debug()

    def _calculate_center(self):
        x = (self._grid[0][0].position.x + self._grid[self.size - 1][self.size - 1].position.x) // 2
        y = (self._grid[0][0].position.y + self._grid[self.size - 1][self.size - 1].position.y) // 2
        return Position(x, y)

    def _construct_children(self):
        children = []
        if self.size % 2 == 0:

            halfsize = self.size // 2
            halite_amount = 0
            for i in range(2):
                for j in range(2):
                    subgrid = []
                    for y in range(halfsize):
                        row = []
                        for x in range(halfsize):
                            cell = self._grid[j*halfsize + y][i*halfsize + x]
                            halite_amount += cell.halite_amount
                            row.append(cell)
                        subgrid.append(row)
                    child = ResourceTree(subgrid, halite_amount, parent=self)
                    children.append(child)
        elif self.size > 1:
            for y in range(self.size):
                for x in range(self.size):
                    child = ResourceTree([[self._grid[y][x]]], self._grid[y][x].halite_amount, parent=self)
                    children.append(child)
        else:
            pass

        self.children = children

    def extract(self, position):
        if self.size == 1:
            self._subtract(self.halite_amount)
        else:
            for child in self.children:
                if child.in_range(position):
                    child.extract(position)

    def _subtract(self, halite_amount, initial=False):
        if (initial):
            self.halite_amount -= halite_amount // 4
        else:
            self.halite_amount -= halite_amount
        if self.parent:
            self.parent._subtract(halite_amount)

    def in_range(self, source):
        return source.x in self._xrange and source.y in self._yrange

    def follow_max(self, game_map, source):
        # logging.debug(f"center: {self.center} - {source} - {game_map.calculate_distance(source, self.center)}")
        # logging.debug(f"self.size: {self.size} : {self.halite_amount}")
        if self.size == 1:
            self._subtract(self.halite_amount, initial=True)
            return self._grid[0][0].position
        else:
            max_halite = 0
            best_child = None
            # logging.debug(f"self.children: {self.children} | {self._grid}")

            for child in self.children:
                distance_penalty = game_map.calculate_distance(source, self.center)
                if child.halite_amount * pow(0.9, distance_penalty) >= max_halite:
                    max_halite = child.halite_amount
                    best_child = child
            return best_child.follow_max(game_map, source)

    def _debug(self):
        for y in range(self.size):
            logging.debug(self._grid[y])
