import pyautogui
import pygetwindow as gw
import os
import time
import threading
import win32gui
import win32con
import win32api
import win32process

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHECK_INTERVAL = 0.1
CONFIDENCE = 0.9

MAX_TRIES = 3

pyautogui.useImageNotFoundException(False)


def wait_and_click(image_path, confidence=CONFIDENCE, message=None):
    """
    Waits for an image to appear and clicks it.
    """
    while True:
        location = pyautogui.locateOnScreen(image_path, confidence=confidence)

        if location is not None:
            center = pyautogui.center(location)
            pyautogui.click(center)
            if message:
                print(message)
            break

        time.sleep(CHECK_INTERVAL)


def activate_window(window_title):
    """
    Brings the specified window to the foreground.
    """
    hwnd = win32gui.FindWindow(None, window_title)

    if not hwnd:
        return False

    # Restore if minimized
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    try:
        pyautogui.press("alt")
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        # Fallback to bypass focus restrictions
        current_thread = win32api.GetCurrentThreadId()
        target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)

        win32process.AttachThreadInput(current_thread, target_thread, True)
        win32gui.SetForegroundWindow(hwnd)
        win32process.AttachThreadInput(current_thread, target_thread, False)

    return True
    
def press_key(key):
    pyautogui.press(key)
    # print(f"{key} pressed")
    time.sleep(0.01)
    
from active_window_check import check_window_issame

def begin_measurements(
    window_title="Beijing TIME High Technology Ltd. DataView TIME5100",
):
    """
    Automates Leeb tester data export process.
    Must be run in admin mode on Windows.
    """

    if not activate_window(window_title):
        return None
    time.sleep(0.1)

    # Start online measurements
    press_key("alt")
    press_key("a")
    press_key("k")

from modular_screen_scan_auto import wait_and_click

def export_hardness_data(
        export_subfolder="test_files", 
        filename="data"
):
    saveAll = os.path.join(SCRIPT_DIR, "leeb_save_all.png")
    export_directory = SCRIPT_DIR

    # Save all measurements
    wait_and_click(saveAll, message="Save All clicked")

    # Stop online measurements
    press_key("alt")
    press_key("a")
    press_key("j")

    # Open data management
    press_key("alt")
    press_key("m")
    press_key("m")

    # Open print dialog
    press_key("alt")
    press_key("f")
    press_key("p")
    time.sleep(5)

    # Export to Excel
    pyautogui.hotkey("shift", "tab")
    time.sleep(0.01)
    pyautogui.hotkey("shift", "tab")
    time.sleep(0.01)
    press_key("enter")
    wait_and_click("leebExport.png")
    press_key("tab")
    press_key("enter")

    # File manager navigation
    time.sleep(1)
    pyautogui.hotkey("alt", "d")
    pyautogui.write(export_directory, interval=0.03)
    press_key("enter")
    time.sleep(0.3)

    # Navigate to filename field
    for _ in range(7):
        press_key("tab")
        time.sleep(0.05)

    pyautogui.write(filename, interval=0.05)
    press_key("enter")
    press_key("tab")
    press_key("enter")

    print(f"Export complete: {filename}.xlsx")
    return os.path.join(export_directory, filename + ".xlsx")

if __name__ == "__main__":
    begin_measurements()
    time.sleep(10)
    export_hardness_data()