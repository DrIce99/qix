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

# Costanti di Stato
STATE_MAIN_MENU = 0
STATE_PLAY_MENU = 1
STATE_OPTIONS_MENU = 2
STATE_PLAYING = 3

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        
        self.px_x = x * CELL_SIZE
        self.px_y = y * CELL_SIZE
        
        self.trail = []
        self.is_outside = False
        
        self.is_moving = False
        self.move_timer = 0
        self.move_delay = 4  # Velocità di movimento (ripristinata a 4 per fluidità)
        self.prev_x, self.prev_y = x, y
        self.target_x, self.target_y = x, y
        
        # Direzione di movimento continua
        self.current_dx = 0
        self.current_dy = 0
        
        self.facing = 'DOWN'
        self.draw_offset_x = 0
        self.draw_offset_y = 0

    def try_move(self, dx, dy, game):
        """Tenta di iniziare un movimento verso una nuova cella"""
        nx, ny = self.x + dx, self.y + dy
        
        if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
            return False

        target_cell = game.grid[ny][nx]

        # 1. Rientro nel muro: chiude la scia
        if target_cell == WALL and self.is_outside:
            self.target_x, self.target_y = nx, ny
            self._start_animation()
            game.close_trail_pending = (nx, ny)
            return True

        # 2. Movimento nel vuoto: attiva lo stato is_outside per creare la scia
        if target_cell == EMPTY:
            self.target_x, self.target_y = nx, ny
            self.is_outside = True  # <-- FIX: Ora rileva correttamente che siamo fuori
            self._start_animation()
            return True

        # 3. Movimento sicuro all'interno dei muri
        if target_cell == WALL and not self.is_outside:
            self.target_x, self.target_y = nx, ny
            self._start_animation()
            return True

        return False

    def _start_animation(self):
        """Prepara e avvia l'interpolazione"""
        self.prev_x, self.prev_y = self.x, self.y
        self.is_moving = True
        self.move_timer = 0
        
        if self.target_x > self.prev_x: self.facing = 'RIGHT'
        elif self.target_x < self.prev_x: self.facing = 'LEFT'
        elif self.target_y > self.prev_y: self.facing = 'DOWN'
        elif self.target_y < self.prev_y: self.facing = 'UP'

    def update(self, game):
        # 1. Leggi l'input SEMPRE, anche durante l'animazione (Funziona da buffer!)
        if pyxel.btn(pyxel.KEY_W) or pyxel.btn(pyxel.KEY_UP):    self.current_dx, self.current_dy = 0, -1
        elif pyxel.btn(pyxel.KEY_S) or pyxel.btn(pyxel.KEY_DOWN):  self.current_dx, self.current_dy = 0, 1
        elif pyxel.btn(pyxel.KEY_A) or pyxel.btn(pyxel.KEY_LEFT):  self.current_dx, self.current_dy = -1, 0
        elif pyxel.btn(pyxel.KEY_D) or pyxel.btn(pyxel.KEY_RIGHT): self.current_dx, self.current_dy = 1, 0

        # 2. Gestisci l'animazione in corso
        if self.is_moving:
            self.move_timer += 1
            t = min(self.move_timer / self.move_delay, 1.0)
            
            self.px_x = lerp(self.prev_x, self.target_x, t) * CELL_SIZE
            self.px_y = lerp(self.prev_y, self.target_y, t) * CELL_SIZE

            # Se l'animazione è finita, aggiorna la griglia e togli il blocco
            if self.move_timer >= self.move_delay:
                self.x, self.y = self.target_x, self.target_y
                self.is_moving = False
                
                if self.is_outside:
                    self.trail.append((self.x, self.y))
                    game.grid[self.y][self.x] = TRAIL
                
                if hasattr(game, 'close_trail_pending') and game.close_trail_pending:
                    game.close_trail()
                    game.close_trail_pending = None
                    self.is_outside = False
            else:
                # Se sta ancora interpolando, esci e non calcolare nuovi movimenti
                return

        # 3. Se non si sta muovendo (o ha appena finito), esegui il prossimo passo
        if self.current_dx != 0 or self.current_dy != 0:
            moved = self.try_move(self.current_dx, self.current_dy, game)
            if not moved:
                self.current_dx, self.current_dy = 0, 0

# Distanza di Manhattan (perfetta per le griglie)
def manhattan_dist(x1, y1, x2, y2):
    return abs(x1 - x2) + abs(y1 - y2)

def lerp(a, b, t):
    """Interpolazione lineare tra a e b basata sul tempo t (da 0.0 a 1.0)"""
    return a + (b - a) * t

class BaseEnemy:    
    def __init__(self, x, y, speed_delay=6):
        # Posizione Logica
        self.x = x
        self.y = y
        
        # Posizione Visiva
        self.px_x = x * CELL_SIZE
        self.px_y = y * CELL_SIZE
        
        self.alive = True
        self.is_moving = False
        self.move_timer = 0
        self.move_delay = speed_delay
        
        self.prev_x, self.prev_y = x, y
        self.target_x, self.target_y = x, y
        
        # --- SPRITE READY ---
        self.facing = 'DOWN'
        self.draw_offset_x = 0
        self.draw_offset_y = 0
    
    def get_valid_moves(self, game):
        """Restituisce le direzioni valide (che non siano muri o bordi)"""
        moves = []
        for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
            nx, ny = self.x + dx, self.y + dy
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                if game.grid[ny][nx] != WALL:
                    moves.append((dx, dy))
        return moves

    def _start_animation(self, tx, ty):
        self.prev_x, self.prev_y = self.x, self.y
        self.target_x, self.target_y = tx, ty
        self.is_moving = True
        self.move_timer = 0
        
        if tx > self.prev_x: self.facing = 'RIGHT'
        elif tx < self.prev_x: self.facing = 'LEFT'
        elif ty > self.prev_y: self.facing = 'DOWN'
        elif ty < self.prev_y: self.facing = 'UP'

    def update(self, game):
        if not self.alive: return

        if self.is_moving:
            # Interpolazione visiva
            self.move_timer += 1
            t = min(self.move_timer / self.move_delay, 1.0)
            
            self.px_x = lerp(self.prev_x, self.target_x, t) * CELL_SIZE
            self.px_y = lerp(self.prev_y, self.target_y, t) * CELL_SIZE

            if self.move_timer >= self.move_delay:
                self.x, self.y = self.target_x, self.target_y
                self.is_moving = False
            return

        # Se è fermo (ha raggiunto la cella), l'IA decide la prossima mossa
        dx, dy = self.get_direction(game)
        
        if dx != 0 or dy != 0:
            nx, ny = self.x + dx, self.y + dy
            # Controlla che sia una mossa valida prima di animarla
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H and game.grid[ny][nx] != WALL:
                self._start_animation(nx, ny)
            else:
                # Se l'IA ha scelto un muro (es. è in trappola), la forziamo a stare ferma 
                # o a cambiare direzione nel prossimo frame (dipende da come implementi get_direction)
                pass

    def get_direction(self, game):
        return 0, 0 # Sovrascritto dalle classi figlie

# ---------------------------------------------------------
# 1. IL VAGABONDO (Random)
# Si muove a caso. Se sbatte, cambia direzione.
# ---------------------------------------------------------
class RandomEnemy(BaseEnemy):
    difficulty = 2
    type = "brandom"
    def get_direction(self, game):
        moves = self.get_valid_moves(game)
        if not moves: return 0, 0
        return random.choice(moves)


# ---------------------------------------------------------
# 2. IL CODARDO (Fleeer)
# Scappa dal giocatore quando lui è fuori dai muri.
# ---------------------------------------------------------
class FleeEnemy(BaseEnemy):
    difficulty = 1
    type = "fleeby"
    def get_direction(self, game):
        moves = self.get_valid_moves(game)
        if not moves: return 0, 0

        if game.player.is_outside:
            # Cerca la mossa che MASSIMIZZA la distanza dal giocatore
            best_moves = []
            max_dist = -1
            for dx, dy in moves:
                dist = manhattan_dist(self.x + dx, self.y + dy, game.player.x, game.player.y)
                if dist > max_dist:
                    max_dist = dist
                    best_moves = [(dx, dy)]
                elif dist == max_dist:
                    best_moves.append((dx, dy))
            return random.choice(best_moves)
        
        # Se il giocatore è al sicuro, si muove a caso
        return random.choice(moves)


# ---------------------------------------------------------
# 3. L'INSEGUITORE (Chaser)
# Ti insegue implacabilmente non appena esci dal muro.
# ---------------------------------------------------------
class ChaserEnemy(BaseEnemy):
    difficulty = 4
    type = "chase"
    def get_direction(self, game):
        moves = self.get_valid_moves(game)
        if not moves: return 0, 0

        if game.player.is_outside:
            # Cerca la mossa che MINIMIZZA la distanza dal giocatore
            best_moves = []
            min_dist = float('inf')
            for dx, dy in moves:
                dist = manhattan_dist(self.x + dx, self.y + dy, game.player.x, game.player.y)
                if dist < min_dist:
                    min_dist = dist
                    best_moves = [(dx, dy)]
                elif dist == min_dist:
                    best_moves.append((dx, dy))
            return random.choice(best_moves)
        
        return random.choice(moves)


# ---------------------------------------------------------
# 4. IL TAGLIATORE (Cutter / Interceptor)
# Cerca di raggiungere il punto più vicino della tua scia 
# per "tagliarti la strada".
# ---------------------------------------------------------
class CutterEnemy(BaseEnemy):
    difficulty = 8
    type = "hasami"
    def get_direction(self, game):
        moves = self.get_valid_moves(game)
        if not moves: return 0, 0

        if game.player.is_outside and game.player.trail:
            # Trova il punto della scia più vicino al nemico
            target_x, target_y = min(game.player.trail, key=lambda p: manhattan_dist(self.x, self.y, p[0], p[1]))
            
            # Ora muoversi verso quel punto specifico della scia
            best_moves = []
            min_dist = float('inf')
            for dx, dy in moves:
                dist = manhattan_dist(self.x + dx, self.y + dy, target_x, target_y)
                if dist < min_dist:
                    min_dist = dist
                    best_moves = [(dx, dy)]
                elif dist == min_dist:
                    best_moves.append((dx, dy))
            return random.choice(best_moves)
        
        return random.choice(moves)

class LevelManager:
    def __init__(self):
        self.current_level = 1
        self.total_score = 0
        
        # Definiamo le classi e le loro soglie di sblocco
        self.enemy_pool = [
            (FleeEnemy, 1),    # Sbloccato dal livello 1
            (RandomEnemy, 1),  # Sbloccato dal livello 1
            (ChaserEnemy, 3),  # Sbloccato dal livello 3
            (CutterEnemy, 6)   # Sbloccato dal livello 6
        ]

    def get_target_difficulty(self):
        # La difficoltà target cresce linearmente. 
        # Lvl 1 = 3, Lvl 2 = 4, Lvl 3 = 5, Lvl 6 = 8, ecc.
        return self.current_level + 2 

    def get_unlocked_enemies(self):
        # Restituisce solo le classi dei nemici sbloccate per il livello attuale
        return [cls for cls, unlock_lvl in self.enemy_pool if self.current_level >= unlock_lvl]

    def generate_wave(self, game_grid, grid_w, grid_h):
        """Genera la lista dei nemici per il livello corrente"""
        target = self.get_target_difficulty()
        unlocked = self.get_unlocked_enemies()
        
        wave = []
        current_score = 0
        
        # Algoritmo greedy per raggiungere il target esatto (o quasi)
        while current_score < target:
            # Filtra i nemici che non farebbero "sforare" troppo il target
            # Permettiamo uno sforzo massimo di +1 per evitare blocchi
            valid_choices = [e for e in unlocked if current_score + e.difficulty <= target + 1]
            
            if not valid_choices:
                # Fallback di sicurezza (non dovrebbe succedere con i nostri numeri)
                valid_choices = [unlocked[0]] 
                
            chosen_class = random.choice(valid_choices)
            wave.append(chosen_class)
            current_score += chosen_class.difficulty

        # Ora istanziamo i nemici in posizioni casuali valide (spazio EMPTY)
        enemies = []
        for enemy_class in wave:
            x, y = self.find_valid_spawn(game_grid, grid_w, grid_h)
            # Istanza con una leggera variazione di velocità per renderli unici
            speed_var = random.randint(-1, 1) 
            enemies.append(enemy_class(x, y, speed_delay=6 + speed_var))
            
        self.current_level += 1
        return enemies

    def find_valid_spawn(self, grid, grid_w, grid_h):
        """Trova una cella EMPTY casuale per non far nascere i nemici nei muri"""
        empty_cells = [(x, y) for y in range(grid_h) for x in range(grid_w) if grid[y][x] == 0] # 0 = EMPTY
        if not empty_cells:
            return grid_w // 2, grid_h // 2 # Fallback
        return random.choice(empty_cells)

class App:
    def __init__(self):
        pyxel.init(256, 256, title="Qix Clone - Conquista il Territorio")
        
        # 0: Nero, 1: Blu (Muri), 2: Rosso (Scia), 3: Verde (Player), 4: Viola (Nemici), 5: Bianco (Vuoto)
        self.grid = [[EMPTY for _ in range(GRID_W)] for _ in range(GRID_H)]
        self.setup_borders()
        
        self.player = Player(GRID_W // 2, 0)
        
        # INIZIALIZZAZIONI CORRETTE QUI:
        self.level_manager = LevelManager()
        self.level_transition_timer = 0
        
        # Generiamo la prima ondata dal LevelManager invece di scriverla a mano
        self.enemies = self.level_manager.generate_wave(self.grid, GRID_W, GRID_H)
        
        self.game_over = False
        self.game_won = False
        self.conquered = 0
        
        # Inizializza i gestori
        self.options = OptionsManager()
        self.menu = MenuManager(self.options)

        # Il gioco non parte subito, inizia dal menu
        self.game_started = False 
        
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
        if len(self.player.trail) < 1:
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
            self.level_transition_timer = 60

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

    def start_new_game(self):
        self.reset_game()

    def update(self):
        if self.menu.state == STATE_PLAYING:
            if not self.game_started:
                self.start_new_game() # Il tuo metodo di setup iniziale
                self.game_started = True
                
            if self.game_over or self.game_won:
                if pyxel.btnp(pyxel.KEY_R):
                    self.reset_game()
                
                if pyxel.btnp(pyxel.KEY_M) or pyxel.btnp(pyxel.KEY_ESCAPE):
                    self.menu.state = STATE_MAIN_MENU
                    self.game_started = False
                return
        
            # Gestione transizione di livello
            if self.level_transition_timer > 0:
                self.level_transition_timer -= 1
                if self.level_transition_timer == 0:
                    self.next_level()
                return

            self.player.update(self)
            for e in self.enemies:
                e.update(self)
                
            self.check_collisions()
        else:
            # Se siamo in un menu, il gioco è in pausa
            self.game_started = False
            self.menu.update()
        
    def reset_game(self):
        """Ripristina lo stato iniziale del gioco senza chiudere l'applicazione"""
        self.grid = [[EMPTY for _ in range(GRID_W)] for _ in range(GRID_H)]
        self.setup_borders()
        self.player = Player(GRID_W // 2, 0)
        self.level_manager = LevelManager()
        self.level_transition_timer = 0
        self.enemies = self.level_manager.generate_wave(self.grid, GRID_W, GRID_H)
        self.game_over = False
        self.game_won = False
        self.conquered = 0
        self.options.reset_unlocks() 

    def next_level(self):
        # 1. Resetta la griglia (lasciando solo i bordi)
        self.grid = [[0 for _ in range(GRID_W)] for _ in range(GRID_H)]
        self.setup_borders()
        
        # 2. Resetta il giocatore al centro/bordo
        self.player.x = GRID_W // 2
        self.player.y = 0
        self.player.is_outside = False
        self.player.trail = []
        
        # 3. Genera la nuova ondata di nemici (il LevelManager incrementa il livello internamente)
        self.enemies = self.level_manager.generate_wave(self.grid, GRID_W, GRID_H)
        
        display_lvl = self.level_manager.current_level - 1 
        self.options.update_unlocks(display_lvl)
        
        # 4. Resetta la percentuale di conquista
        self.conquered = 0 
    
    def draw(self):
        if self.menu.state == STATE_PLAYING:
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
                        pyxel.rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE, 3) # Verde scuro

            # Disegna il giocatore
            if not self.game_over:
                # Quando passerò agli sprite, basterà cambiare pyxel.rect con pyxel.blt
                # e usare self.player.facing per scegliere l'immagine
                draw_x = self.player.px_x + self.player.draw_offset_x
                draw_y = self.player.px_y + self.player.draw_offset_y
                pyxel.rect(draw_x, draw_y, CELL_SIZE, CELL_SIZE, 11) 

            # Disegna i nemici
            for e in self.enemies:
                if e.alive:
                    draw_x = e.px_x + e.draw_offset_x
                    draw_y = e.px_y + e.draw_offset_y
                    if e.type == "brandom":
                        pyxel.rect(draw_x, draw_y, CELL_SIZE, CELL_SIZE, 14) # Viola
                    elif e.type == "fleeby":
                        pyxel.rect(draw_x, draw_y, CELL_SIZE, CELL_SIZE, 15) # Rosa/Bianco
                    elif e.type == "chase":
                        pyxel.rect(draw_x, draw_y, CELL_SIZE, CELL_SIZE, 8)  # Rosso scuro
                    elif e.type == "hasami":
                        pyxel.rect(draw_x, draw_y, CELL_SIZE, CELL_SIZE, 4)  # Marrone/Verdone

            # UI: Livello e Percentuale di conquista (accorpati per non sovrapporsi)
            current_display_lvl = self.level_manager.current_level - 1
            pyxel.text(2, 2, f"LVL: {current_display_lvl}  CONQUERED: {int(self.conquered * 100)}%", 7)
            
            # Se è in transizione:
            if self.level_transition_timer > 0:
                if self.level_transition_timer % 10 < 5:
                    # Mostra il livello in arrivo
                    pyxel.text(100, 120, f"LEVEL {self.level_manager.current_level}!", 10)
            
            if self.game_over:
                pyxel.text(90, 120, "GAME OVER", 8)
                pyxel.text(65, 135, "R: RESTART   M: MENU", 7)
            elif self.game_won:
                pyxel.text(95, 120, "YOU WIN!", 10)
                pyxel.text(65, 135, "R: RESTART   M: MENU", 7)
        else:
            # Disegna i menu
            self.menu.draw()

# Interfaccia principale 

class OptionsManager:
    def __init__(self):
        # --- IMPOSTAZIONI GENERALI ---
        self.volume = 5  # Da 0 a 7 (standard Pyxel) o 0-100
        self.skin_index = 0
        self.max_skins = 1  # Diventerà 2 quando aggiungerai gli sprite

        # --- DEFINIZIONE PALETTE (Coppie di colori Pyxel 0-15) ---
        # Formato: (Colore Principale, Colore Secondario)
        self.player_palettes = [
            (11, 3),   # Base: Verde / Verde scuro
            (2, 4),  
            (10, 9),  
            (14, 8),  
            (5, 1),  
            (6, 12),  
            (15, 13),  
            (7, 0)  
        ]
        self.game_palettes = [
            (10, 9),  
            (14, 8),  
            (5, 1),  
            (6, 12),  
            (15, 13),  
            (7, 0), 
            (11, 3), 
            (2, 4) 
        ]
        self.enemy_palettes = [
            (2, 4),  
            (10, 9),  
            (14, 8),  
            (5, 1),  
            (6, 12),  
            (15, 13),  
            (7, 0),
            (11, 3)  
        ]

        # --- SELEZIONI ATTUALI (Indici) ---
        self.sel_player_pal = 0
        self.sel_game_pal = 0
        self.sel_enemy_pal = 0

        # --- STATO SBLOCCHI (True/False) ---
        self.unlocked_player = [True, False, False, False, False, False, False, False]
        self.unlocked_game = [True, False, False, False, False, False, False, False]
        self.unlocked_enemy = [True, False, False, False, False, False, False, False]

    def get_colors(self):
        """Restituisce tutti i colori attivi per il rendering"""
        p_col = self.player_palettes[self.sel_player_pal]
        g_col = self.game_palettes[self.sel_game_pal]
        e_col = self.enemy_palettes[self.sel_enemy_pal]
        
        return {
            'player': p_col[0], 'trail': p_col[1],
            'bg': g_col[0], 'wall': g_col[1],
            'enemy_group1': e_col[0], 'enemy_group2': e_col[1]
        }

    def can_select_palette(self, target_type, new_index):
        """
        Logica Anti-Mimesi: Impedisce di selezionare palette 
        che hanno lo stesso colore principale delle altre due categorie.
        """
        # Ottieni il colore principale della nuova selezione
        if target_type == 'player': new_col = self.player_palettes[new_index][0]
        elif target_type == 'game': new_col = self.game_palettes[new_index][0]
        else: new_col = self.enemy_palettes[new_index][0]

        # Controlla se è uguale al colore principale delle altre due
        other_cols = []
        if target_type != 'player': other_cols.append(self.player_palettes[self.sel_player_pal][0])
        if target_type != 'game': other_cols.append(self.game_palettes[self.sel_game_pal][0])
        if target_type != 'enemy': other_cols.append(self.enemy_palettes[self.sel_enemy_pal][0])

        return new_col not in other_cols

    def unlock_next_palette(self, target_type):
        """Chiamato quando il giocatore supera un livello milestone"""
        if target_type == 'player': unlocks = self.unlocked_player
        elif target_type == 'game': unlocks = self.unlocked_game
        else: unlocks = self.unlocked_enemy

        for i in range(len(unlocks)):
            if not unlocks[i]:
                unlocks[i] = True
                return i # Ritorna l'indice appena sbloccato
    
    def reset_unlocks(self):
        """Resetta gli sblocchi al livello iniziale (solo la prima palette sbloccata)"""
        # Crea una lista con True solo al primo elemento e False per tutti gli altri
        self.unlocked_player = [True] + [False] * (len(self.player_palettes) - 1)
        self.unlocked_game = [True] + [False] * (len(self.game_palettes) - 1)
        self.unlocked_enemy = [True] + [False] * (len(self.enemy_palettes) - 1)

    def update_unlocks(self, current_display_level):
        """Sblocca le palette in base al livello raggiunto (ogni 5 livelli)"""
        # Calcola quante palette aggiuntive devono essere sbloccate
        # Lvl 5 -> 1, Lvl 10 -> 2, Lvl 15 -> 3, ecc.
        additional_unlocks = current_display_level // 5
        
        # Sblocca fino all'indice calcolato (senza superare il massimo disponibile)
        max_idx = len(self.unlocked_player)
        for i in range(1, min(additional_unlocks + 1, max_idx)):
            self.unlocked_player[i] = True
            self.unlocked_game[i] = True
            self.unlocked_enemy[i] = True

class MenuManager:
    def __init__(self, options):
        self.options = options
        self.state = STATE_MAIN_MENU
        
        # Indici di selezione per i menu
        self.main_sel = 0
        self.play_sel = 0
        self.opt_sel = 0
        
        # Definizione voci menu opzioni
        self.opt_items = [
            {"name": "VOLUME", "type": "slider"},
            {"name": "SKIN", "type": "selector"},
            {"name": "PALETTE PLAYER", "type": "palette", "target": "player"},
            {"name": "PALETTE MONDO", "type": "palette", "target": "game"},
            {"name": "PALETTE NEMICI", "type": "palette", "target": "enemy"},
            {"name": "INDIETRO", "type": "action"}
        ]

    def update(self):
        # Input di navigazione base (cambio voce)
        if pyxel.btnp(pyxel.KEY_UP): self._change_selection(-1)
        if pyxel.btnp(pyxel.KEY_DOWN): self._change_selection(1)

        # Input di conferma/indietro
        if pyxel.btnp(pyxel.KEY_Z) or pyxel.btnp(pyxel.KEY_RETURN):
            self._confirm()
        if pyxel.btnp(pyxel.KEY_X) or pyxel.btnp(pyxel.KEY_ESCAPE):
            self._go_back()

        # Input laterale (Sinistra/Destra) per modificare i valori nelle Opzioni
        if self.state == STATE_OPTIONS_MENU:
            if pyxel.btnp(pyxel.KEY_LEFT): self._adjust_value(-1)
            if pyxel.btnp(pyxel.KEY_RIGHT): self._adjust_value(1)

    def _change_selection(self, direction):
        if self.state == STATE_MAIN_MENU:
            self.main_sel = (self.main_sel + direction) % 3
        elif self.state == STATE_PLAY_MENU:
            self.play_sel = (self.play_sel + direction) % 2
        elif self.state == STATE_OPTIONS_MENU:
            self.opt_sel = (self.opt_sel + direction) % len(self.opt_items)

    def _confirm(self):
        if self.state == STATE_MAIN_MENU:
            if self.main_sel == 0: self.state = STATE_PLAY_MENU
            elif self.main_sel == 1: self.state = STATE_OPTIONS_MENU
            elif self.main_sel == 2: pyxel.quit()
            
        elif self.state == STATE_PLAY_MENU:
            if self.play_sel == 0: 
                self.state = STATE_PLAYING
                # Qui dovrai chiamare il metodo per inizializzare una nuova partita
            # play_sel == 1 è "Continua" ed è disabilitato, quindi non fa nulla
            
        elif self.state == STATE_OPTIONS_MENU:
            item = self.opt_items[self.opt_sel]
            if item["type"] == "action": # INDIETRO
                self.state = STATE_MAIN_MENU

    def _go_back(self):
        if self.state == STATE_PLAY_MENU: self.state = STATE_MAIN_MENU
        elif self.state == STATE_OPTIONS_MENU: self.state = STATE_MAIN_MENU
        elif self.state == STATE_PLAYING: 
            # Pausa o torna al menu? Per ora torniamo al menu principale
            self.state = STATE_MAIN_MENU 

    def _adjust_value(self, direction):
        item = self.opt_items[self.opt_sel]
        
        if item["type"] == "slider":
            self.options.volume = max(0, min(7, self.options.volume + direction))
            
        elif item["type"] == "selector":
            self.options.skin_index = (self.options.skin_index + direction) % self.options.max_skins
            
        elif item["type"] == "palette":
            target = item["target"]
            if target == 'player': pals, sel, unl = self.options.player_palettes, 'sel_player_pal', self.options.unlocked_player
            elif target == 'game': pals, sel, unl = self.options.game_palettes, 'sel_game_pal', self.options.unlocked_game
            else: pals, sel, unl = self.options.enemy_palettes, 'sel_enemy_pal', self.options.unlocked_enemy

            current_idx = getattr(self.options, sel)
            new_idx = (current_idx + direction) % len(pals)
            
            # Controlla se è sbloccato
            if not unl[new_idx]: return 
            
            # Controlla la logica anti-mimesi
            if self.options.can_select_palette(target, new_idx):
                setattr(self.options, sel, new_idx)

    def draw(self):
        if self.state == STATE_MAIN_MENU: self._draw_main()
        elif self.state == STATE_PLAY_MENU: self._draw_play()
        elif self.state == STATE_OPTIONS_MENU: self._draw_options()

    def _draw_main(self):
        pyxel.cls(0)
        pyxel.text(100, 40, "QIX CLONE", 7)
        items = ["GIOCA", "OPZIONI", "ESCI"]
        for i, text in enumerate(items):
            col = 7 if i == self.main_sel else 5
            pyxel.text(110, 80 + i * 20, text, col)
            if i == self.main_sel: pyxel.text(100, 80 + i * 20, ">", 7)

    def _draw_play(self):
        pyxel.cls(0)
        pyxel.text(100, 40, "GIOCA", 7)
        items = ["NUOVA PARTITA", "CONTINUA"]
        for i, text in enumerate(items):
            # "Continua" è disabilitato (colore 5 e non selezionabile visivamente in modo attivo)
            col = 7 if i == self.play_sel else 5
            if i == 1: col = 5 # Sempre grigio per disabilitato
            pyxel.text(90, 80 + i * 20, text, col)
            if i == self.play_sel and i == 0: pyxel.text(80, 80 + i * 20, ">", 7)

    def _draw_options(self):
        pyxel.cls(0)
        pyxel.text(90, 10, "OPZIONI", 7)
        
        for i, item in enumerate(self.opt_items):
            y = 40 + i * 25
            col = 7 if i == self.opt_sel else 5
            pyxel.text(20, y, item["name"], col)
            if i == self.opt_sel: pyxel.text(10, y, ">", 7)

            # Disegna i controlli a destra
            val_x = 150
            if item["type"] == "slider":
                pyxel.text(val_x, y, f"< {self.options.volume} >", 7)
            elif item["type"] == "selector":
                pyxel.text(val_x, y, f"< SKIN {self.options.skin_index+1} >", 7)
                # Qui potresti disegnare l'anteprima dello sprite/quadrato al centro
            elif item["type"] == "palette":
                self._draw_palette_preview(item["target"], val_x, y, i == self.opt_sel)

    def _draw_palette_preview(self, target, x, y, is_selected):
        if target == 'player': pals, sel, unl = self.options.player_palettes, self.options.sel_player_pal, self.options.unlocked_player
        elif target == 'game': pals, sel, unl = self.options.game_palettes, self.options.sel_game_pal, self.options.unlocked_game
        else: pals, sel, unl = self.options.enemy_palettes, self.options.sel_enemy_pal, self.options.unlocked_enemy

        idx = sel
        is_unlocked = unl[idx]
        
        if not is_unlocked:
            pyxel.text(x, y, "[ BLOCCATO ]", 5)
            return

        c1, c2 = pals[idx]
        # Disegna i due quadratini colorati come anteprima
        pyxel.rect(x, y, 6, 6, c1)
        pyxel.rect(x + 10, y, 6, 6, c2)
        
        if is_selected:
            pyxel.text(x - 10, y, "<", 7)
            pyxel.text(x + 20, y, ">", 7)

App()