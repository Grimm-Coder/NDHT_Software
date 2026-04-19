import pyautogui
import os
import random
import string

#must be run in admin mode on windows
# before running:
# connect leeb tester and key for software
# power on leeb tester
# open leeb tester software
# connect device (double check com port)
# (first time setup) do test set

import pygetwindow as gw
import time

import os

current_file_path = os.path.abspath(__file__)
current_directory = os.path.dirname(current_file_path)

window_title = "Beijing TIME High Technology Ltd. DataView TIME5100"   # Part of the window title

windows = gw.getWindowsWithTitle(window_title)

pyautogui.useImageNotFoundException(False)

saveAll = os.path.join(
    os.path.dirname(__file__),
    "leeb_save_all.png"
)

if windows:
    win = windows[0]
    if win.isMinimized:
        win.restore()      # Restore if minimized
    win.activate()         # Bring to front
    print("Window activated")
else:
    print("Window not found")

# start on line measurements
pyautogui.press("alt")
pyautogui.press("a")
pyautogui.press("k")

# test_not_done = True
# while(test_not_done):
time.sleep(20)

# after gone to all points, export data

# save measurements
while True:
    location = pyautogui.locateOnScreen(
        saveAll,
        confidence=0.9
    )

    if location is not None:
        center = pyautogui.center(location)
        pyautogui.click(center)
        print("Save all button appeared and was clicked!")
        break

    time.sleep(0.1)

# stop online measurements
pyautogui.press("alt")
pyautogui.press("a")
pyautogui.press("j")

# open data management
pyautogui.press("alt")
pyautogui.press("m")
pyautogui.press("m")

# open print dialogue
pyautogui.press("alt")
pyautogui.press("f")
pyautogui.press("p")
time.sleep(1)

# export to excel file
pyautogui.hotkey("shift", "tab")
pyautogui.hotkey("shift", "tab")
pyautogui.press("enter")
pyautogui.press("tab")
pyautogui.press("tab")
pyautogui.press("enter")
pyautogui.press("enter")

# in file manager, save file to correct name 
time.sleep(1)
pyautogui.hotkey("alt", "d")
pyautogui.write(current_directory + r"\test_files", interval=0.03)
pyautogui.press("enter")
time.sleep(0.3)
# navigating to file name box in fm then write name
for _ in range(7):
    pyautogui.press("tab")
    time.sleep(0.05)

pyautogui.write("data", interval=0.05)
pyautogui.press("enter")