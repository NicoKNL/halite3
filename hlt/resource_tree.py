class Node(object):
    def __init__(self, parent, grid, halite_amount):
        self.size = len(grid)
        self.parent = parent
        self._grid = grid
        self.halite_amount = halite_amount
        self.children = None
        self._construct_children()

    def _construct_children(self):
        children = []
        if self.size % 2 == 0:
            halfsize = self.size / 2
            subgrid = []
            halite_amount = 0
            for i in range(2):
                for j in range(2):
                    for y in range(halfsize):
                        row = []
                        for x in range(halfsize):
                            cell = self.grid[j*halfsize + y][i*halfsize + x]
                            halite_amount += cell.halite_amount
                            row.append(cell)
                        subgrid.append(row)
                    child = Node(self, subgrid, halite_amount)
                    children.append(child)
        self.children = children

    def subtract(self, halite_amount):
        self.halite_amount -= halite_amount
        if self.parent:
            self.parent.subtract(halite_amount)


class ResourceTree(object):
    def __init__(self, game_map):
        self._tree = Node(None, game_map, game_map.halite)

    def close_max(self, ):