from hlt.positionals import Position


class Grid(object):
    def __init__(self, game_map):
        self.game_map = game_map
        self.grid = None
        self.max_w = 0

        self.build_grid()

    def build_grid(self):
        grid_cells = []
        for row in range(self.game_map.height):
            grid_row = []
            for col in range(self.game_map.width):
                game_cell = self.game_map[Position(row, col)]
                cell = Cell(row, col, game_cell.halite_amount)
                grid_row.append(cell)

                # Now that we are looping over the grid, we immediately also calculate max_w for efficiency reasons
                self.max_w = max(self.max_w, cell.w)

            grid_cells.append(grid_row)

        self.grid = grid_cells

        # # Test if an enemy is already on this resource
        # resources = 0
        # if cell.is_occupied:
        #     logging.debug(f"SHIP DATA -------------------------------------- {cell.ship.owner} - {me.id}")
        #     if cell.ship.owner != me.id or Position(row, col) == me.shipyard.position:
        #         cell.mark_unsafe(cell.ship)
        #     else:
        #         resources = cell.halite_amount
        #         if resources > resource_max:
        #             resource_max = resources
        # else:
        #     resources = cell.halite_amount
        #     if resources > resource_max:
        #         resource_max = resources
        # grid_row.append(resources)

        # resource_map.append(row_resources)


class Cell(object):
    def __init__(self, x, y, w):
        self.x = x
        self.y = y
        self.w = w

        self.pos = Position(self.x, self.y)
