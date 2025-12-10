import time
import board
import busio
import digitalio
import neopixel
import random

from adafruit_ssd1306 import SSD1306_I2C
import adafruit_adxl34x

# ================== HARDWARE SETUP ==================

# I2C bus shared by OLED display and ADXL345 accelerometer
i2c = busio.I2C(board.SCL, board.SDA)

# 128x64 OLED display over I2C
OLED_WIDTH = 128
OLED_HEIGHT = 64
oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)

# ADXL345 accelerometer (used for tilt control)
accel = adafruit_adxl34x.ADXL345(i2c)
accel.enable_tap_detection()  # optional, not required for gameplay

# Rotary encoder:
#   A phase -> D1  (we only use phase A for single-direction menu scrolling)
enc_a = digitalio.DigitalInOut(board.D1)
enc_a.direction = digitalio.Direction.INPUT
enc_a.pull = digitalio.Pull.UP

# Encoder push button -> D2
enc_button = digitalio.DigitalInOut(board.D2)
enc_button.direction = digitalio.Direction.INPUT
enc_button.pull = digitalio.Pull.UP  # idle = True, pressed = False

# NeoPixel strip for difficulty indication and feedback
PIXEL_PIN = board.D3
NUM_PIXELS = 8
pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=0.2, auto_write=True)

# ================== GAME CONSTANTS ==================

# Tilt threshold: how much tilt is required to trigger one move
TILT_THRESHOLD = 0.25

# Difficulty settings: movement cooldown and time per level
DIFFICULTIES = [
    {"name": "EASY",   "move_cooldown": 0.35, "time_limit": 40},
    {"name": "MEDIUM", "move_cooldown": 0.25, "time_limit": 30},
    {"name": "HARD",   "move_cooldown": 0.18, "time_limit": 20},
]

# NeoPixel colors
COLOR_OFF   = (0, 0, 0)
COLOR_EASY  = (0, 50, 0)
COLOR_MED   = (50, 30, 0)
COLOR_HARD  = (50, 0, 0)
COLOR_GOOD  = (0, 0, 50)
COLOR_FAIL  = (50, 0, 0)
COLOR_WIN   = (0, 50, 50)

# Maze rendering parameters (10x10 grid on 128x64 OLED)
CELL_SIZE = 6
MAZE_OFFSET_X = 4
MAZE_OFFSET_Y = 4


# ================== MAZE GENERATION ==================
# Maze cell values:
#   0 = path, 1 = wall, 2 = start, 3 = goal


def generate_maze(width, height, wall_density, wiggle_prob):
    """
    Generate a simple maze with:
      - solid walls on the border
      - a guaranteed path from start (2) to goal (3)
      - extra walls added randomly based on wall_density
      - some path "wiggle" controlled by wiggle_prob
    """
    # Start with all open cells
    maze = [[0 for _ in range(width)] for _ in range(height)]

    # Add solid border walls
    for x in range(width):
        maze[0][x] = 1
        maze[height - 1][x] = 1
    for y in range(height):
        maze[y][0] = 1
        maze[y][width - 1] = 1

    start = (1, 1)
    goal = (width - 2, height - 2)

    # Build a main path from start to goal with a bias towards right/down
    path = []
    x, y = start
    path.append((x, y))

    max_steps = width * height * 5  # safety limit

    while (x, y) != goal and len(path) < max_steps:
        need_right = (x < goal[0])
        need_down = (y < goal[1])

        candidates = []

        # Primary directions toward goal
        if need_right:
            candidates.append((x + 1, y))
        if need_down:
            candidates.append((x, y + 1))

        # Optional side moves to make the path less straight
        if random.random() < wiggle_prob:
            side_moves = []
            if x > 1:
                side_moves.append((x - 1, y))
            if x < width - 2:
                side_moves.append((x + 1, y))
            if y > 1:
                side_moves.append((x, y - 1))
            if y < height - 2:
                side_moves.append((x, y + 1))
            if side_moves:
                candidates.append(random.choice(side_moves))

        if not candidates:
            break

        nx, ny = random.choice(candidates)
        nx = max(1, min(width - 2, nx))
        ny = max(1, min(height - 2, ny))

        if (nx, ny) != path[-1]:
            path.append((nx, ny))
            x, y = nx, ny

    # Mark main path as open
    for (px, py) in path:
        maze[py][px] = 0

    # Collect all inner cells that are not on the path
    all_cells = [
        (cx, cy)
        for cy in range(1, height - 1)
        for cx in range(1, width - 1)
        if (cx, cy) not in path
    ]

    # CircuitPython doesn't have random.shuffle, so we implement a Fisher–Yates shuffle
    n = len(all_cells)
    for i in range(n - 1, 0, -1):
        j = random.randint(0, i)
        all_cells[i], all_cells[j] = all_cells[j], all_cells[i]

    # Turn a fraction of those cells into walls
    num_walls = int(len(all_cells) * wall_density)
    for i in range(num_walls):
        cx, cy = all_cells[i]
        maze[cy][cx] = 1

    # Place start and goal
    sx, sy = start
    gx, gy = goal
    maze[sy][sx] = 2
    maze[gy][gx] = 3

    return maze


def generate_maze_for_level(difficulty_idx, level_idx):
    """
    Generate a 10x10 maze for a specific difficulty and level index.

    Each difficulty has:
      - its own base wall density
      - its own base path "wiggle" probability
    Higher level_idx → more walls and more wiggle → harder maze.
    """
    width, height = 10, 10

    base_wall_density = [0.15, 0.30, 0.45]  # EASY / MEDIUM / HARD
    base_wiggle       = [0.10, 0.25, 0.40]

    delta_density = 0.03    # how much wall density grows per level
    delta_wiggle  = 0.02    # how much wiggle grows per level

    wall_density = base_wall_density[difficulty_idx] + level_idx * delta_density
    wiggle_prob  = base_wiggle[difficulty_idx]       + level_idx * delta_wiggle
    wall_density = min(0.70, wall_density)
    wiggle_prob  = min(0.70, wiggle_prob)

    # Use a fixed seed so the same difficulty+level always gives similar layout
    random.seed(1000 * difficulty_idx + level_idx)

    return generate_maze(width, height, wall_density, wiggle_prob)


# ================== COMMON HELPERS ==================


def set_difficulty_pixels(idx):
    """Set NeoPixels to reflect current difficulty."""
    if idx == 0:
        color = COLOR_EASY
    elif idx == 1:
        color = COLOR_MED
    else:
        color = COLOR_HARD
    for i in range(NUM_PIXELS):
        pixels[i] = color


def pixels_flash(color, times=3, delay=0.2):
    """Flash all pixels with a given color for feedback."""
    for _ in range(times):
        for i in range(NUM_PIXELS):
            pixels[i] = color
        time.sleep(delay)
        for i in range(NUM_PIXELS):
            pixels[i] = COLOR_OFF
        time.sleep(delay)


def find_start_and_goal(maze):
    """Return (start_pos, goal_pos) from the maze matrix."""
    start = None
    goal = None
    for y, row in enumerate(maze):
        for x, cell in enumerate(row):
            if cell == 2:
                start = (x, y)
            elif cell == 3:
                goal = (x, y)
    return start, goal


# ================== MENU (ENCODER-ONLY) ==================


def draw_menu(idx):
    """Draw the difficulty selection menu on OLED."""
    oled.fill(0)
    oled.text("Maze Runner", 0, 0, 1)
    oled.text("Rotate: NEXT", 0, 12, 1)
    oled.text("Press:  START", 0, 22, 1)
    for i, d in enumerate(DIFFICULTIES):
        mark = ">" if i == idx else " "
        oled.text("{} {}".format(mark, d["name"]), 0, 36 + i * 10, 1)
    oled.show()


def run_menu():
    """
    Difficulty selection menu.

    Uses a single encoder phase (A) with basic debouncing:
      - detect edges on A
      - wait 5 ms for stable level
      - count 2 stable edges as one “step”
    Button press starts the game with the selected difficulty.
    """
    enc_a_raw_last = enc_a.value
    enc_a_stable = enc_a.value
    last_bounce_time = time.monotonic()
    edge_count = 0

    button_last = enc_button.value

    def read_encoder_step_menu():
        """Return 1 when the encoder moves one detent (single direction)."""
        nonlocal enc_a_raw_last, enc_a_stable, last_bounce_time, edge_count
        now = time.monotonic()
        raw = enc_a.value

        # Detect change and restart debounce timer
        if raw != enc_a_raw_last:
            enc_a_raw_last = raw
            last_bounce_time = now

        # After debounce interval, check for stable new state
        if (now - last_bounce_time) > 0.005 and raw != enc_a_stable:
            enc_a_stable = raw
            edge_count += 1
            if edge_count >= 2:
                edge_count = 0
                return 1  # one menu step
        return 0

    def read_button_press_menu():
        """
        Return True when button transitions from unpressed -> pressed.
        Active-low input: pressed = False.
        """
        nonlocal button_last
        cur = enc_button.value
        pressed = (not cur) and button_last
        button_last = cur
        return pressed

    difficulty_idx = 0
    set_difficulty_pixels(difficulty_idx)
    draw_menu(difficulty_idx)

    print("MENU: single-phase debounced encoder running...")

    while True:
        step = read_encoder_step_menu()
        if step:
            # Cycle through EASY → MEDIUM → HARD → EASY...
            difficulty_idx = (difficulty_idx + 1) % len(DIFFICULTIES)
            set_difficulty_pixels(difficulty_idx)
            draw_menu(difficulty_idx)
            print("STEP ->", DIFFICULTIES[difficulty_idx])

        if read_button_press_menu():
            print("BUTTON PRESSED -> START", DIFFICULTIES[difficulty_idx])
            # Wait until button is released before starting the game
            while not enc_button.value:
                time.sleep(0.01)
            return difficulty_idx

        time.sleep(0.002)


# ================== GAMEPLAY (ACCEL + BUTTON) ==================


def draw_maze(maze, player_pos, level, difficulty_name, remaining_time):
    """
    Draw the maze on the left side of the screen and
    game status (HUD) on the right side.
    """
    oled.fill(0)

    # Draw maze grid
    for y, row in enumerate(maze):
        for x, cell in enumerate(row):
            px = MAZE_OFFSET_X + x * CELL_SIZE
            py = MAZE_OFFSET_Y + y * CELL_SIZE
            if cell == 1:
                oled.fill_rect(px, py, CELL_SIZE, CELL_SIZE, 1)
            elif cell == 3:
                oled.rect(px, py, CELL_SIZE, CELL_SIZE, 1)

    # Draw player
    if player_pos is not None:
        x, y = player_pos
        px = MAZE_OFFSET_X + x * CELL_SIZE + 1
        py = MAZE_OFFSET_Y + y * CELL_SIZE + 1
        oled.fill_rect(px, py, CELL_SIZE - 2, CELL_SIZE - 2, 1)

    # HUD on the right side
    HUD_X = 70
    oled.text("L{}".format(level + 1), HUD_X, 0, 1)
    oled.text(difficulty_name, HUD_X, 10, 1)
    oled.text("T:{:2d}s".format(int(remaining_time)), HUD_X, 22, 1)

    oled.show()


def get_tilt_direction(last_dir, last_move_time, move_cooldown):
    """
    Convert accelerometer reading into one logical move direction.

    Only allow one move every `move_cooldown` seconds.
    Pick the axis (X or Y) with the largest magnitude and compare against
    TILT_THRESHOLD to decide direction.
    """
    now = time.monotonic()

    # Movement cooldown
    if now - last_move_time < move_cooldown:
        return None, last_move_time, last_dir

    # Read accelerometer with basic retry in case of transient I2C errors
    x = y = z = 0.0
    ok = False
    for _ in range(3):
        try:
            x, y, z = accel.acceleration
            ok = True
            break
        except OSError as e:
            print("ACCEL ERROR, retrying...", e)
            time.sleep(0.01)

    if not ok:
        # Skip this frame, keep last movement time
        return None, last_move_time, last_dir

    print("ACC raw:", x, y, z)

    dir_candidate = None
    ax = x
    ay = y

    # Decide whether horizontal or vertical tilt is stronger
    if abs(ax) >= abs(ay):
        # Horizontal tilt
        if ax > TILT_THRESHOLD:
            dir_candidate = "RIGHT"
        elif ax < -TILT_THRESHOLD:
            dir_candidate = "LEFT"
    else:
        # Vertical tilt
        if ay > TILT_THRESHOLD:
            dir_candidate = "DOWN"
        elif ay < -TILT_THRESHOLD:
            dir_candidate = "UP"

    if dir_candidate is None:
        return None, last_move_time, last_dir

    print("DIR:", dir_candidate)
    # Return new direction and update last_move_time
    return dir_candidate, now, dir_candidate


def try_move(maze, player_pos, direction):
    """Attempt to move one step in the maze; cancel if we hit a wall."""
    x, y = player_pos
    if direction == "LEFT":
        nx, ny = x - 1, y
    elif direction == "RIGHT":
        nx, ny = x + 1, y
    elif direction == "UP":
        nx, ny = x, y - 1
    elif direction == "DOWN":
        nx, ny = x, y + 1
    else:
        return player_pos

    if 0 <= ny < len(maze) and 0 <= nx < len(maze[0]):
        if maze[ny][nx] != 1:  # not a wall
            return (nx, ny)
    return player_pos


def is_at_goal(player_pos, goal_pos):
    """Return True if player has reached the goal."""
    return player_pos == goal_pos


def wait_button_press_and_release():
    """Block until the button is pressed and then released."""
    while enc_button.value:
        time.sleep(0.01)
    while not enc_button.value:
        time.sleep(0.01)


def run_game(difficulty_idx):
    """
    Run a full game session for the selected difficulty.

    The player must clear 10 procedurally-generated levels.
    Control:
      - Tilt device to move in the maze
      - Reach the goal before time runs out
      - NeoPixels flash on win / loss
    """
    diff = DIFFICULTIES[difficulty_idx]
    print("GAME: start with difficulty", diff["name"])

    # Reset NeoPixels and show difficulty color
    for i in range(NUM_PIXELS):
        pixels[i] = COLOR_OFF
    set_difficulty_pixels(difficulty_idx)

    move_cooldown = diff["move_cooldown"]
    time_limit = diff["time_limit"]

    total_levels = 10
    level_idx = 0

    while level_idx < total_levels:
        # Generate maze for this difficulty + level index
        maze = generate_maze_for_level(difficulty_idx, level_idx)

        start, goal = find_start_and_goal(maze)
        player_pos = start
        goal_pos = goal

        level_start_t = time.monotonic()
        last_move_time = level_start_t - move_cooldown  # allow immediate first move
        last_tilt_dir = None

        state = "PLAYING"

        while state == "PLAYING":
            now = time.monotonic()
            elapsed = now - level_start_t
            remaining = time_limit - elapsed

            if remaining <= 0:
                state = "GAME_OVER"
                break

            # Tilt-based movement
            direction, last_move_time, last_tilt_dir = get_tilt_direction(
                last_tilt_dir, last_move_time, move_cooldown
            )
            if direction is not None:
                player_pos = try_move(maze, player_pos, direction)

            if is_at_goal(player_pos, goal_pos):
                state = "LEVEL_CLEAR"
                break

            draw_maze(maze, player_pos, level_idx, diff["name"], remaining)
            time.sleep(0.01)

        if state == "GAME_OVER":
            pixels_flash(COLOR_FAIL, times=3, delay=0.15)
            oled.fill(0)
            oled.text("GAME OVER", 20, 20, 1)
            oled.text("Press Btn", 20, 40, 1)
            oled.show()
            wait_button_press_and_release()
            return  # back to menu

        if state == "LEVEL_CLEAR":
            pixels_flash(COLOR_GOOD, times=2, delay=0.12)
            level_idx += 1  # next level

    # All 10 levels cleared
    pixels_flash(COLOR_WIN, times=4, delay=0.15)
    oled.fill(0)
    oled.text("ALL 10 LEVELS", 6, 20, 1)
    oled.text("CLEARED! YOU WIN!", 0, 36, 1)
    oled.show()
    wait_button_press_and_release()


# ================== MAIN LOOP ==================

while True:
    diff_idx = run_menu()   # encoder + button only
    run_game(diff_idx)      # accelerometer + button only
