import pyxel
import random

# Costanti della griglia
GRID_W, GRID_H = 32, 32
CELL_SIZE = 8
WIN_PERCENTAGE = 0.95

# Tipi di celle
EMPTY = 0
WALL = 1
TRAIL = 2

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.trail = []
        self.is_outside = False
        self.move_timer = 0
        self.move_delay = 4 # Velocità del giocatore

    def move(self, dx, dy, game):
        nx, ny = self.x + dx, self.y + dy
        
        # Controlla i limiti della mappa
        if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
            return

        target_cell = game.grid[ny][nx]

        # Se il giocatore torna su un muro mentre sta disegnando, chiude il ciclo
        if target_cell == WALL and self.is_outside:
            self.x, self.y = nx, ny
            self.is_outside = False
            game.close_trail()
            return

        # Se esce dal muro, inizia a disegnare
        if target_cell == EMPTY:
            self.x, self.y = nx, ny
            self.is_outside = True
            self.trail.append((nx, ny))
            game.grid[ny][nx] = TRAIL
            
        # Se si muove dentro i muri (safe zone)
        elif target_cell == WALL and not self.is_outside:
            self.x, self.y = nx, ny

    def update(self, game):
        self.move_timer += 1
        if self.move_timer < self.move_delay:
            return
        self.move_timer = 0

        dx, dy = 0, 0
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W): dy = -1
        elif pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S): dy = 1
        elif pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A): dx = -1
        elif pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D): dx = 1

        if dx != 0 or dy != 0:
            self.move(dx, dy, game)

class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.alive = True
        self.move_timer = 0
        self.move_delay = 6 # Leggermente più lenti del giocatore
        self.dx, self.dy = random.choice([(0,1), (0,-1), (1,0), (-1,0)])

    def update(self, game):
        if not self.alive:
            return

        self.move_timer += 1
        if self.move_timer < self.move_delay:
            return
        self.move_timer = 0

        # Semplice IA: va dritto, se sbatte cambia direzione
        nx, ny = self.x + self.dx, self.y + self.dy
        
        # Controlla se può muoversi (deve stare solo su EMPTY o TRAIL)
        # Se tocca il TRAIL mentre il giocatore è fuori, il giocatore muore (gestito nel game loop)
        if 0 <= nx < GRID_W and 0 <= ny < GRID_H and game.grid[ny][nx] != WALL:
            self.x, self.y = nx, ny
        else:
            # Cambia direzione casualmente
            self.dx, self.dy = random.choice([(0,1), (0,-1), (1,0), (-1,0)])

class App:
    def __init__(self):
        pyxel.init(256, 256, title="Qix Clone - Conquista il Territorio")
        
        # 0: Nero, 1: Blu (Muri), 2: Rosso (Scia), 3: Verde (Player), 4: Viola (Nemici), 5: Bianco (Vuoto)
        self.grid = [[EMPTY for _ in range(GRID_W)] for _ in range(GRID_H)]
        self.setup_borders()
        
        self.player = Player(GRID_W // 2, 0)
        self.enemies = [Enemy(GRID_W // 4, GRID_H // 2), Enemy(GRID_W * 3 // 4, GRID_H // 2)]
        
        self.game_over = False
        self.game_won = False
        self.conquered = 0
        
        pyxel.run(self.update, self.draw)

    def setup_borders(self):
        for x in range(GRID_W):
            self.grid[0][x] = WALL
            self.grid[GRID_H-1][x] = WALL
        for y in range(GRID_H):
            self.grid[y][0] = WALL
            self.grid[y][GRID_W-1] = WALL

    def calculate_conquered(self):
        walls = sum(row.count(WALL) for row in self.grid)
        total = GRID_W * GRID_H
        self.conquered = walls / total

    def close_trail(self):
        # Se la scia è troppo corta, non ha creato un'area, la cancelliamo
        if len(self.player.trail) < 2:
            self.player.trail = []
            return

        # Trasformiamo temporaneamente la scia in muri per chiudere il perimetro
        for x, y in self.player.trail:
            self.grid[y][x] = WALL

        # Troviamo tutte le celle vuote
        empty_cells = [(x, y) for y in range(GRID_H) for x in range(GRID_W) if self.grid[y][x] == EMPTY]
        total_empty = len(empty_cells)

        if total_empty == 0:
            self.player.trail = []
            self.calculate_conquered()
            return

        # Algoritmo di Flood Fill per trovare le regioni
        # Partiamo da una cella vuota adiacente alla scia
        start_cell = None
        for tx, ty in self.player.trail:
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                nx, ny = tx+dx, ty+dy
                if 0 <= nx < GRID_W and 0 <= ny < GRID_H and self.grid[ny][nx] == EMPTY:
                    start_cell = (nx, ny)
                    break
            if start_cell: break

        if not start_cell:
            self.player.trail = []
            self.calculate_conquered()
            return

        # Flood fill per trovare la "Regione A"
        region_A = set()
        stack = [start_cell]
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in region_A: continue
            if self.grid[cy][cx] != EMPTY: continue
            
            region_A.add((cx, cy))
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                stack.append((cx+dx, cy+dy))

        # Determiniamo quale regione è più piccola
        if len(region_A) <= total_empty / 2:
            cells_to_fill = region_A
        else:
            # Se la regione A è quella grande, riempiamo tutto il resto (che è la regione piccola)
            cells_to_fill = set(empty_cells) - region_A

        # Riempiamo l'area più piccola e controlliamo i nemici
        for x, y in cells_to_fill:
            self.grid[y][x] = WALL
            for e in self.enemies:
                if e.x == x and e.y == y and e.alive:
                    e.alive = False # Nemico "mangiato"

        self.player.trail = []
        self.calculate_conquered()

        if self.conquered >= WIN_PERCENTAGE:
            self.game_won = True

    def check_collisions(self):
        # Controllo se un nemico tocca la scia o il giocatore (quando è fuori)
        if self.player.is_outside:
            for e in self.enemies:
                if not e.alive: continue
                # Nemico tocca il giocatore
                if e.x == self.player.x and e.y == self.player.y:
                    self.game_over = True
                # Nemico tocca la scia
                if (e.x, e.y) in self.player.trail:
                    self.game_over = True

    def update(self):
        if self.game_over or self.game_won:
            if pyxel.btnp(pyxel.KEY_R):
                pyxel.quit() # O reinizia il gioco resettando le variabili
            return

        self.player.update(self)
        for e in self.enemies:
            e.update(self)
            
        self.check_collisions()

    def draw(self):
        pyxel.cls(0) # Sfondo nero

        # Disegna la griglia
        for y in range(GRID_H):
            for x in range(GRID_W):
                cell = self.grid[y][x]
                if cell == EMPTY:
                    pyxel.rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE, 5) # Bianco
                elif cell == WALL:
                    pyxel.rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE, 1) # Blu
                elif cell == TRAIL:
                    pyxel.rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE, 2) # Rosso

        # Disegna il giocatore
        if not self.game_over:
            pyxel.rect(self.player.x * CELL_SIZE, self.player.y * CELL_SIZE, CELL_SIZE, CELL_SIZE, 3) # Verde

        # Disegna i nemici
        for e in self.enemies:
            if e.alive:
                pyxel.rect(e.x * CELL_SIZE + 1, e.y * CELL_SIZE + 1, CELL_SIZE - 2, CELL_SIZE - 2, 4) # Viola

        # UI: Percentuale di conquista
        pyxel.text(2, 2, f"CONQUERED: {int(self.conquered * 100)}%", 7)
        
        if self.game_over:
            pyxel.text(90, 120, "GAME OVER", 8)
            pyxel.text(80, 135, "Press R to quit", 7)
        elif self.game_won:
            pyxel.text(95, 120, "YOU WIN!", 10)
            pyxel.text(80, 135, "Press R to quit", 7)

App()