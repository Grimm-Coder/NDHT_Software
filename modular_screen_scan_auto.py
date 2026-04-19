import pyautogui
import time
import os
import random
import string


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIDENCE = 0.8
CHECK_INTERVAL = 0.5

pyautogui.useImageNotFoundException(False)


def random_filename(length=12):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def wait_and_click(image_path, confidence=CONFIDENCE, offset_x=0, offset_y=0, message=None):
    """
    Waits for an image to appear on screen and clicks it.
    Optional offset allows clicking relative to found location.
    """
    while True:
        location = pyautogui.locateOnScreen(image_path, confidence=CONFIDENCE)

        if location is not None:
            x, y = pyautogui.center(location)
            pyautogui.click(x + offset_x, y + offset_y)
            if message:
                print(message)
            break

        time.sleep(CHECK_INTERVAL)


def run_scan(export_directory=r"C:\Users\gavin\Downloads\capstoneCodeRepo\capstone-software"):
    """
    Main automation function.
    Can be imported and called from another file.
    """

    startScan = os.path.join(SCRIPT_DIR, "startScan.png")
    stopScan = os.path.join(SCRIPT_DIR, "stopScan.png")
    repair = os.path.join(SCRIPT_DIR, "repair.png")
    denoise = os.path.join(SCRIPT_DIR, "denoising.png")
    simplify = os.path.join(SCRIPT_DIR, "simplify.png")
    append = os.path.join(SCRIPT_DIR, "append.png")
    apply = os.path.join(SCRIPT_DIR, "apply.png")
    yes = os.path.join(SCRIPT_DIR, "yes.png")

    filename = random_filename()

    time.sleep(1)
    wait_and_click(startScan, message="Start button clicked")
    time.sleep(5)

    wait_and_click(stopScan, confidence=CONFIDENCE - 0.15, message="Stop button clicked")
    wait_and_click(repair, message="Repair clicked")
    wait_and_click(denoise, message="Denoise clicked")
    wait_and_click(simplify, message="Simplify clicked")

    wait_and_click(append, offset_x=200, message="Append right-side clicked")

    pyautogui.write(filename, interval=0.05)

    wait_and_click(apply, message="Apply clicked")
    wait_and_click(apply, message="Apply clicked again")

    time.sleep(5)
    pyautogui.hotkey("ctrl", "e")

    wait_and_click(yes, message="Confirmation clicked")

    time.sleep(0.3)

    pyautogui.hotkey("alt", "d")
    pyautogui.write(export_directory, interval=0.03)
    pyautogui.press("enter")
    time.sleep(0.3)

    for _ in range(7):
        pyautogui.press("tab")
        time.sleep(0.05)

    pyautogui.write(filename + ".ply", interval=0.05)
    pyautogui.press("enter")

    print(f"Exported file: {filename}.ply")
    return filename + ".stl"

if __name__ == "__main__":
    while True:
        loc = pyautogui.locateOnScreen(r"C:\Users\grimm\OneDrive\Documents\Capstone Repository\capstone-software\startScan.png", confidence=CONFIDENCE)
        if not loc == None:
            print("found it!")
            break
        else:
            print("not found")
    run_scan()