# Maze Runner – Hardware Maze Game

## How the Game Works

**Maze Runner** is a tilt-controlled maze game running on a **Seeed XIAO ESP32-C3**.

1. On startup, the player uses the **rotary encoder** to select a difficulty:
   - `EASY`
   - `MEDIUM`
   - `HARD`

2. Each difficulty contains **10 procedurally generated maze levels**:
   - Mazes are 10×10 grids.
   - Wall density and path “wiggliness” increase with higher levels and higher difficulty.
   - There is always at least one valid path from start to goal.

3. After selecting a difficulty and pressing the encoder button, the game starts:
   - The **ADXL345 accelerometer** reads the board’s tilt.
   - Tilting left/right/up/down moves the player one cell in that direction (with a cooldown so it doesn’t move too fast).
   - Each level has a **time limit** based on difficulty. When the timer runs out, the game is over.
   - The game continues until:
     - The player clears all 10 levels (win), or  
     - Time runs out on any level (game over).

4. The **OLED display (128×64)** shows:
   - The maze layout (walls, path, start, goal).
   - The player’s current position.
   - On the right side:
     - Current level number.
     - Difficulty name.
     - Remaining time in seconds.

5. The **NeoPixel strip** gives visual feedback:
   - Shows difficulty color during the menu:
     - Easy: green tone  
     - Medium: amber/orange tone  
     - Hard: red tone  
   - Flashes blue on level clear.
   - Flashes red on game over.
   - Flashes cyan when all 10 levels are cleared (win).

---

## Additional Hardware

This project uses:

- **Seeed Studio XIAO ESP32-C3**
  - Runs all game logic and handles I/O.
- **128×64 I2C OLED Display**
  - I2C-connected; displays the maze and HUD.
- **ADXL345 Accelerometer**
  - Detects tilt direction for movement.
- **Rotary Encoder with Push Button**
  - Rotate: change difficulty in the menu.
  - Press: confirm selection and start the game.
- **NeoPixel (WS2812) LED Strip – 8 LEDs**
  - Indicates difficulty and game events via color and flashing patterns.
- **3.7V Li-ion Battery (optional)**
  - For portable, untethered play.
- **Power switch / simple power wiring (optional)**
  - To safely turn the device on/off when using a battery.

---

## Enclosure Design Thought Process

The enclosure is designed around three main goals: **playability**, **readability**, and **robustness**.

### 1. Playability (Tilt as Main Input)

- The device is treated like a small handheld console.
- Shape is sized so it can be comfortably held with two hands.
- Flat base and consistent orientation help the accelerometer read tilt in a stable way.
- The design avoids sharp edges so the player can freely tilt in any direction.

### 2. Readability (OLED + LEDs)

- The **OLED** is mounted on the front face, slightly angled for comfortable viewing.
- The maze occupies the left side; status info (level, difficulty, time) is on the right.
- The **NeoPixels** are placed along one edge or around the frame so:
  - They are clearly visible in peripheral vision.
  - They do not block or distract from the OLED content.

### 3. Controls Placement

- The **rotary encoder** is placed where the thumb can easily reach it:
  - Typically top-right or right edge of the device.
  - This makes difficulty selection quick and natural without blocking the screen.
- The **button** (encoder push) is used for “OK / Start”:
  - No extra buttons are needed, keeping the front panel simple and clean.

### 4. Internal Layout and Wiring

- The **XIAO ESP32-C3** is mounted on standoffs to avoid flex and stress on solder joints.
- The **ADXL345** is fixed firmly and as central as possible so:
  - Tilting the device corresponds cleanly to tilt readings.
  - Cable movement doesn’t create false accelerometer noise.
- Wires to the OLED, accelerometer, encoder, and NeoPixels are:
  - Routed to minimize crossing.
  - Given some slack but also strain-relief to avoid disconnection.

### 5. Battery and Portability

- The back of the enclosure contains a small compartment for the **3.7V Li-ion battery**.
- A removable panel or simple clip mechanism allows battery replacement or disconnect.
- The USB-C port on the XIAO remains accessible for:
  - Reprogramming.
  - Debugging.
  - Optional USB power instead of battery.

### 6. Durability and Aesthetics

- Enclosure walls are thick enough to survive repeated tilting, presses, and daily handling.
- Edges are slightly rounded for comfort.
- The overall look is:
  - Compact and minimal.
  - Clearly “handheld game” rather than a raw prototype board.

---
