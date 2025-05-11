import os
from numpy import hstack, ndindex
import numpy as np
from grid import Grid
import random
import time
import copy

class Solver:
    def __init__(self, size, move_speed=0.1):
        self.size = size
        self.env = Grid(size)
        self.target = 1024
        self.move_speed = move_speed  # Speed of tile movement in seconds
        self.special_moves = {
            'rotate': 3,  # Number of rotations available
            'merge_all': 2,  # Number of merge_all moves available
            'double_tile': 2  # Number of double_tile moves available
        }
        
    def no_moves(self):
        if self.next_move_predictor()[1] == 0:
            return True 

    def next_move_predictor(self):
        directions = ['w', 's', 'a', 'd', 'r', 'm', 't']  # Added special move options
        next_score = {'w': 0, 's': 0, 'a': 0, 'd': 0, 'r': 0, 'm': 0, 't': 0} 

        for direction in directions:
            grid_copy = copy.deepcopy(self.env.grid)

            if direction == 'w':
                self.env.move_up(grid_copy)
            elif direction == 's':
                self.env.move_down(grid_copy)
            elif direction == 'a':
                self.env.move_left(grid_copy)
            elif direction == 'd':
                self.env.move_right(grid_copy)
            elif direction == 'r' and self.special_moves['rotate'] > 0:
                grid_copy = np.rot90(grid_copy)
            elif direction == 'm' and self.special_moves['merge_all'] > 0:
                self.merge_all_adjacent(grid_copy)
            elif direction == 't' and self.special_moves['double_tile'] > 0:
                self.double_random_tile(grid_copy)

            score = self.get_score(grid_copy)
            next_score[direction] = score

        print("Final predictions:", next_score)
        return max(next_score.items(), key=lambda x: x[1])

    def merge_all_adjacent(self, grid):
        """Merges all adjacent tiles with same value"""
        for i in range(self.size):
            for j in range(self.size-1):
                if grid[i][j] == grid[i][j+1] and grid[i][j] != 0:
                    grid[i][j] *= 2
                    grid[i][j+1] = 0

    def double_random_tile(self, grid):
        """Doubles the value of a random non-empty tile"""
        non_empty = [(i,j) for i in range(self.size) for j in range(self.size) if grid[i][j] != 0]
        if non_empty:
            i, j = random.choice(non_empty)
            grid[i][j] *= 2

    def expectimax(self, grid, depth, is_chance):
        if depth == 1 or self.env.is_full():
            return self.get_score(grid)

        if is_chance:
            empty_cells = self.get_empty_cells(grid)
            total_score = 0
            total_weight = 0
            for cell in empty_cells:
                x, y = cell
                new_grid = [row[:] for row in grid]
                new_grid[x][y] = 4  # Changed from 2 to 4
                score = self.expectimax(new_grid, depth - 1, is_chance=True)
                total_score += score * 0.9
                total_weight += 0.9
                new_grid[x][y] = 8  # Changed from 4 to 8
                score = self.expectimax(new_grid, depth - 1, is_chance=False)
                total_score += score * 0.1
                total_weight += 0.1
            return total_score / total_weight if total_weight > 0 else 0
        else:
            directions = ['w', 's', 'a', 'd']
            total_score = 0
            for direction in directions:
                new_grid = [row[:] for row in grid]
                if direction == 'w':
                    self.env.move_up(new_grid)
                elif direction == 's':
                    self.env.move_down(new_grid)
                elif direction == 'a':
                    self.env.move_left(new_grid)
                elif direction == 'd':
                    self.env.move_right(new_grid)
                score = self.expectimax(new_grid, depth - 1, is_chance=True)
                total_score += score
            return total_score / len(directions)

    def get_empty_cells(self, grid):
        return [(i, j) for i in range(self.size) for j in range(self.size) if grid[i][j] == 0]

    def score_adjacent_tiles(self, grid):
        """
        The function `score_adjacent_tiles` calculates the average of the scores obtained from counting and
        finding the mean of neighboring tiles on a grid.
        """
        return (self.score_count_neighbor(grid) + self.score_mean_neighbor(grid)) / 2

    def score_snake(self, grid, base_value=0.25):
        """
        The function `score_snake` calculates the score of a game grid in a snake-like game by combining
        values from different directions.
        """
        size = len(grid)
        rewardArray = np.array([base_value ** i for i in range(size ** 2)])

        score = 0
        for i in range(2):
            gridArray_horizontal = np.hstack(tuple(grid[j] if i % 2 == 0 else grid[j][::-1] for j in range(size)))
            score = max(score, np.sum(rewardArray * gridArray_horizontal))
            score = max(score, np.sum(rewardArray[::-1] * gridArray_horizontal))
            gridArray_vertical = np.hstack(tuple(grid[j][::-1] if i % 2 == 0 else grid[j] for j in range(size)))
            score = max(score, np.sum(rewardArray * gridArray_vertical))
            score = max(score, np.sum(rewardArray[::-1] * gridArray_vertical))

            grid = grid.T

        return score

    def score_mean_neighbor(self, newgrid):
        """
        Calculate the mean(average) of  tiles with the same values that are adjacent in a row/column.
        """
        horizontal_sum, count_horizontal = self.check_adjacent(newgrid)
        vertical_sum, count_vertical = self.check_adjacent(newgrid.T)
        if count_horizontal == 0 or count_vertical == 0:
            return 0
        return (horizontal_sum + vertical_sum) / (count_horizontal + count_vertical)

    def check_adjacent(self, grid):
        """
        Returns the sum and total number (count) of tiles with the same values that are adjacent in a row/column.
        """
        count = 0
        total_sum = 0
        for row in grid:
            previous = -1
            for tile in row:
                if previous == tile:
                    total_sum += tile
                    count += 1
                previous = tile
        return total_sum, count

    def score_count_neighbor(self, grid):
        _, horizontal_count = self.check_adjacent(grid)
        _, vertical_count = self.check_adjacent(grid.T)
        return horizontal_count + vertical_count

    def calculate_empty_tiles(self, grid):
        empty_tiles = 0
        for x, y in ndindex(grid.shape):
            if grid[x, y] == 0:
                empty_tiles += 1
        return empty_tiles

    def get_score(self, grid):
        grid = np.array(grid)
        adjacent_tiles_score = self.score_adjacent_tiles(grid)
        snake_score = self.score_snake(grid)
        empty_tiles = self.calculate_empty_tiles(grid)
        total_score = (adjacent_tiles_score + 3 * snake_score + empty_tiles) / 6
        return total_score

    def check_target_reached(self):
        for row in self.env.grid:
            if self.target in row:
                return True
        return False

    def run(self):
        while True:
            os.system("cls")
            
            # Check win/lose conditions
            if self.check_target_reached():
                self.env.render()
                print("\nTarget reached!")
                print("\nTOTAL SCORE:", self.env.score)
                input("\nPress Enter to exit...")
                break
                
            if self.env.is_full():
                self.env.render()
                print("\nTOTAL SCORE:", self.env.score)
                if self.env.flag and self.no_moves():
                    print("\n\nX---X---X  GAME OVER  X---X---X\n\n")
                input("\nPress Enter to exit...")
                break

            print("\nTOTAL SCORE:", self.env.score)
            print("\nSpecial moves remaining:")
            print(f"Rotate: {self.special_moves['rotate']}")
            print(f"Merge All: {self.special_moves['merge_all']}")
            print(f"Double Tile: {self.special_moves['double_tile']}")
            self.env.render()

            best_move = ''

            if self.env.flag == 1:
                print('\n\nGoing to predict next move')
                best_move, best_score = self.next_move_predictor()

                print("Next move should be:", best_move, "\nWith a score of:", best_score)
            self.env.flag = 1

            direction = best_move

            if direction == "w":
                self.env.move_up()
            elif direction == "s":
                self.env.move_down()
            elif direction == "a":
                self.env.move_left()
            elif direction == "d":
                self.env.move_right()
            elif direction == "r" and self.special_moves['rotate'] > 0:
                self.env.grid = np.rot90(self.env.grid).tolist()
                self.special_moves['rotate'] -= 1
            elif direction == "m" and self.special_moves['merge_all'] > 0:
                self.merge_all_adjacent(self.env.grid)
                self.special_moves['merge_all'] -= 1
            elif direction == "t" and self.special_moves['double_tile'] > 0:
                self.double_random_tile(self.env.grid)
                self.special_moves['double_tile'] -= 1
            
            self.env.generate_new_cell()
            

            time.sleep(self.move_speed)

if __name__ == "__main__":
    size = 8
    move_speed = 0.1  
    solver = Solver(size, move_speed)
    solver.run()
