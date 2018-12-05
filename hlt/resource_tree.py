class ResourceTree(object):
    def __init__(self, parent, grid, halite_amount):
        self._xrange = range(grid[0][0].position.x, grid[len(grid)][len(grid)].position.x)
        self._yrange = range(grid[0][0].position.y, grid[len(grid)][len(grid)].position.y)

        self.size = len(grid)
        self.parent = parent
        self._grid = grid
        self.halite_amount = halite_amount
        self.children = None
        self._construct_children()

    def _construct_children(self):
        children = []
        if self.size % 2 == 0 and self.size > 1:
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
                    child = ResourceTree(self, subgrid, halite_amount)
                    children.append(child)
        else:
            for y in range(self.size):
                for x in range(self.size):
                    child = ResourceTree(self, [[self._grid[y][x]]], self._grid[y][x].halite_amount)
                    children.append(child)
        self.children = children

    def subtract(self, halite_amount):
        self.halite_amount -= halite_amount
        if self.parent:
            self.parent.subtract(halite_amount)

    def in_range(self, source):
        return source.x in self._xrange and source.y in self._yrange

    def follow_max(self):
        if self.size == 1:
            self.subtract(self.halite_amount)
            return self._grid[0][0].position
        else:
            max_halite = 0
            best_child = None
            for child in self.children:
                if child.halite_amount > max_halite:
                    max_halite = child.halite_amount
                    best_child = child
            return best_child.follow_max()
