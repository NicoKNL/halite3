from hlt.positionals import Position
from enum import Enum


class Entity(Enum):
    NONE = 0
    FRIEND = 1
    ENEMY = 2
    SHIPYARD = 3
    # Enemy shipyard?
    # Additional dropoffs


class Grid(object):
    def __init__(self, game_map, player):
        self._game_map = game_map
        self._player = player

        self.grid = None
        self.max_w = 0

        self.build_grid()    # Initialization for the cells and self.max_w
        # self.connect_grid()  # Sets up the neighbour relations within each cell

    def build_grid(self):
        grid_cells = []
        for row in range(self._game_map.height):
            grid_row = []
            for col in range(self._game_map.width):
                game_cell = self._game_map[Position(row, col)]
                cell = Cell(game_cell, self._player)
                grid_row.append(cell)

                # Now that we are looping over the grid, we immediately also calculate max_w for efficiency reasons
                self.max_w = max(self.max_w, cell.w)

            grid_cells.append(grid_row)

        self.grid = grid_cells


class Cell(object):
    def __init__(self, game_cell, player): #x, y, w):
        self._game_cell = game_cell
        self._player = player

        self.pos = self._game_cell.position #Position(self.x, self.y)
        self.x = self.pos.x
        self.y = self.pos.y

        self.w = self._game_cell.halite_amount

        self.entity = self.get_entity()

        # Dijkstra support
        self.dist = None
        self.prev = None

    def get_entity(self):
        if self._game_cell.is_empty:
            return Entity.NONE

        elif self._game_cell.is_occupied:
            ship = self._game_cell.ship
            if ship.owner == self._player:
                return Entity.FRIEND
            else:
                return Entity.ENEMY

        else: # Shipyard (later on also dropoffs)
            if self._game_cell.structure.owner == self._player:
                return Entity.SHIPYARD
            else:
                return Entity.ENEMY

    def set_weight(self, w):
        self.w = w
