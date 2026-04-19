import pyautogui
import pygetwindow as gw
import cv2
import numpy as np
import time
import os

SAVE_DIR = "screenshots"
os.makedirs(SAVE_DIR, exist_ok=True)

import win32gui
import pyautogui
import cv2
import numpy as np

def find_window_by_title(window_name):
    hwnds = []

    def enum_handler(hwnd, ctx):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if window_name.lower() in title.lower():
                hwnds.append(hwnd)

    win32gui.EnumWindows(enum_handler, None)
    return hwnds


def capture_window(window_name=None):
    if window_name is None:
        hwnd = win32gui.GetForegroundWindow()
    else:
        hwnds = find_window_by_title(window_name)
        if not hwnds:
            print(f"Window '{window_name}' not found")
            return None
        hwnd = hwnds[0]

    if not hwnd:
        return None

    # Get window rectangle (includes borders)
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)

    width = right - left
    height = bottom - top

    # Capture top third & left half of the window
    bbox = (left, top, width // 2, height // 3)

    screenshot = pyautogui.screenshot(region=bbox)
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    return img

def images_are_same(img1, img2, threshold=0.9995):
    # convert to grayscale
    g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # resize just in case
    if g1.shape != g2.shape:
        g2 = cv2.resize(g2, (g1.shape[1], g1.shape[0]))

    diff = cv2.absdiff(g1, g2)
    non_zero = np.count_nonzero(diff)
    similarity = 1 - (non_zero / diff.size)

    return similarity >= threshold, similarity

def check_window_issame(timeout, check_frequency = 1):
    previous = None
    count = 0
    time_start = time.time()
    curr_time = time_start
    while (curr_time - time_start) <= timeout:
        current = capture_window("Beijing TIME High Technology Ltd. DataView TIME5100")

        if current is None:
            time.sleep(check_frequency)
            continue

        if previous is None:
            previous = current
            continue

        same, similarity = images_are_same(previous, current)

        if same:
            print(f"[{count}] SAME (similarity {similarity:.4f})")
            # logic for same
        else:
            print(f"[{count}] DIFFERENT (similarity {similarity:.4f})")
            # logic for different
            cv2.imwrite(f"{SAVE_DIR}/change_{count}.png", current)
            return False

        previous = current
        count += 1
        time.sleep(check_frequency)
        curr_time = time.time()

    return True