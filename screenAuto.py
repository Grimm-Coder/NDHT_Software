import pyautogui
import time
import os
import random
import string

#must be run in admin mode on windows

# Path to the reference image of the button
startScan = os.path.join(
    os.path.dirname(__file__),
    "startScan.png"
)

stopScan = os.path.join(
    os.path.dirname(__file__),
    "stopScan.png"
)


repair = os.path.join(
    os.path.dirname(__file__),
    "repair.png"
)

denoise = os.path.join(
    os.path.dirname(__file__),
    "denoising.png"
)

simplify = os.path.join(
    os.path.dirname(__file__),
    "simplify.png"
)

append= os.path.join(
    os.path.dirname(__file__),
    "append.png"
)

apply= os.path.join(
    os.path.dirname(__file__),
    "apply.png"
)

yes= os.path.join(
    os.path.dirname(__file__),
    "yes.png"
)




# --- config ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIDENCE = 0.95
CHECK_INTERVAL = 0.5
def random_filename(length=12):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length)) 

filename = random_filename()
# ----------------


pyautogui.useImageNotFoundException(False)

# print("Waiting for button to appear...")

while True:
    location = pyautogui.locateOnScreen(
        startScan,
        confidence=CONFIDENCE
    )

    if location is not None:
        center = pyautogui.center(location)
        pyautogui.click(center)
        print("Start button appeared and was clicked!")
        break

    time.sleep(CHECK_INTERVAL)
# pyautogui.moveRel(0, -100)    
time.sleep(5)
    
while True:
    location = pyautogui.locateOnScreen(
        stopScan,
        confidence=CONFIDENCE -0.15
    )

    if location is not None:
        center = pyautogui.center(location)
        pyautogui.click(center)
        print("Stop button appeared and was clicked!")
        break

    time.sleep(CHECK_INTERVAL)
    
while True:
    location = pyautogui.locateOnScreen(
        repair,
        confidence=CONFIDENCE
    )

    if location is not None:
        center = pyautogui.center(location)
        pyautogui.click(center)
        print("Stop button appeared and was clicked!")
        break

    time.sleep(CHECK_INTERVAL)
    
while True:
    location = pyautogui.locateOnScreen(
        denoise,
        confidence=CONFIDENCE
    )

    if location is not None:
        center = pyautogui.center(location)
        pyautogui.click(center)
        print("Denoise button appeared and was clicked!")
        break

    time.sleep(CHECK_INTERVAL)
    
while True:
    location = pyautogui.locateOnScreen(
        simplify,
        confidence=CONFIDENCE
    )

    if location is not None:
        center = pyautogui.center(location)
        pyautogui.click(center)
        print("Simplify button appeared and was clicked!")
        break

    time.sleep(CHECK_INTERVAL)
    
while True:
    location = pyautogui.locateOnScreen(
        append,
        confidence=CONFIDENCE
    )

    if location is not None:
        x, y = pyautogui.center(location)
        pyautogui.click(x + 200, y)
        print("Append button appeared and button to right was clicked!")
        break

    time.sleep(CHECK_INTERVAL)
    
    
pyautogui.write(filename, interval=0.05)

while True:
    location = pyautogui.locateOnScreen(
        apply,
        confidence=CONFIDENCE
    )

    if location is not None:
        center = pyautogui.center(location)
        pyautogui.click(center)
        print("Apply button appeared and was clicked!")
        break

    time.sleep(CHECK_INTERVAL)
    
while True:
    location = pyautogui.locateOnScreen(
        apply,
        confidence=CONFIDENCE
    )

    if location is not None:
        center = pyautogui.center(location)
        pyautogui.click(center)
        print("Apply button appeared and was clicked!")
        break

    time.sleep(CHECK_INTERVAL)

time.sleep(5)
pyautogui.hotkey("ctrl", "e")    

while True:
    location = pyautogui.locateOnScreen(
        yes,
        confidence=CONFIDENCE
    )

    if location is not None:
        center = pyautogui.center(location)
        pyautogui.click(center)
        print("Apply button appeared and was clicked!")
        break

    time.sleep(CHECK_INTERVAL)
    
time.sleep(0.3)

# Navigate to folder via address bar
pyautogui.hotkey("alt", "d")
pyautogui.write(r"C:\Users\gavin\Downloads\capstoneCodeRepo\capstone-software", interval=0.03)
pyautogui.press("enter")
time.sleep(0.3)

# Press Tab until filename box is selected
for _ in range(7):
    pyautogui.press("tab")
    time.sleep(0.05)

pyautogui.write(filename + ".stl", interval=0.05)
pyautogui.press("enter")