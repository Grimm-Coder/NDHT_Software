import sys
import rtde.rtde as rtde
import rtde.rtde_config as rtde_config
import time
import queue
import threading
import pyautogui
import os
import random
import string
import pandas as pd
import numpy as np
import math

import modular_hardness_auto as mha
from modular_surface_points import process_ply
from active_window_check import check_window_issame
from modular_hardness_auto import activate_window, begin_measurements, export_hardness_data
from transform_to_baseframe import transform_to_baseframe
from combine_data import create_combined_csv
from plot_hardness import plot_hardness_on_ply

# takes a 6 element list, representing a pose in the format [x, y, z, rx, ry, rz], in meters and radians, relative to robot base frame
pose_queue = queue.Queue()
keep_running = True
enable_force_bool = False
move_completed = queue.Queue(maxsize = 1)
contact_made = queue.Queue(maxsize = 1)
# takes 2 element list (e.g. [0.0, 0.0])
# index 0 = reset leeb tester (1.0 to extend, 0.0 to retract), index 1 = take test (1.0 to take test, 0.0 to reset solenoid)
tool_outputs = queue.Queue(maxsize=1)

ROBOT_HOST = "10.36.196.112"
ROBOT_PORT = 30004
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIDENCE = 0.95
CHECK_INTERVAL = 0.5
TOL = 0.0001       # tolerance applied to check with current pose against sent pose
# change to local export directory when have chance
EXPORT_DIRECTORY=r"C:\Users\grimm\OneDrive\Documents\Capstone Repository\capstone-software"
# X, Y, Z coordinates of scan box, in m
# index 0 = corner over L marker
# index 2 = corner opposite L marker
# index 1,3 = the other 2 corners (in any order)
WORK_PLANE = 180
MM_TO_M = 0.001
SCAN_PATH_WIDTH = 60
scan_bounding_box = [[-0.040, -0.410, WORK_PLANE*MM_TO_M, 0, 3.14, 0],
                     [-0.040, -0.515, WORK_PLANE*MM_TO_M, 0, 3.14, 0],
                     [0.080, -0.515, WORK_PLANE*MM_TO_M, 0, 3.14, 0],
                     [0.080, -0.410, WORK_PLANE*MM_TO_M, 0, 3.14, 0]]

pyautogui.useImageNotFoundException(False)

startScan = os.path.join(SCRIPT_DIR, "startScan.png")
stopScan = os.path.join(SCRIPT_DIR, "stopScan.png")
repair = os.path.join(SCRIPT_DIR, "repair.png")
denoise = os.path.join(SCRIPT_DIR, "denoising.png")
simplify = os.path.join(SCRIPT_DIR, "simplify.png")
append = os.path.join(SCRIPT_DIR, "append.png")
apply = os.path.join(SCRIPT_DIR, "apply.png")
yes = os.path.join(SCRIPT_DIR, "yes.png")
stopProcess = os.path.join(SCRIPT_DIR, "stopProcess.png")
reorientate = os.path.join(SCRIPT_DIR, "reorientate.png")

def random_filename(length=12):
    """
    Generates a random filename of specified length using letters and digits.
    
    Args:
        length (int): Length of the random filename. Default is 12.
        
    Returns:
        str: Random filename string.
    """
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def wait_and_click(image_path, confidence=CONFIDENCE, offset_x=0, offset_y=0, message=None):
    """
    Waits for an image to appear on screen and clicks it.
    Optional offset allows clicking relative to found location.
    """
    while True:
        location = pyautogui.locateOnScreen(image_path, confidence=confidence)

        if location is not None:
            x, y = pyautogui.center(location)
            pyautogui.click(x + offset_x, y + offset_y)
            if message:
                print(message)
            break
        time.sleep(CHECK_INTERVAL)

def wait_until_gone(image_path, confidence=CONFIDENCE, offset_x=0, offset_y=0, message=None):
    """
    Waits for an image to disappear on screen.
    """
    while True:
        location = pyautogui.locateOnScreen(image_path, confidence=confidence)

        if location is None:
            if message:
                print(message)
            break
        time.sleep(CHECK_INTERVAL)

def list_to_setp(sp, list):
    """
    Converts a list of 6 position/orientation values to setpoint object.
    
    Args:
        sp: Setpoint object to update.
        list: 6-element list [x, y, z, rx, ry, rz].
        
    Returns:
        setpoint: Updated setpoint object.
    """
    for i in range(0, 6):
        sp.__dict__["input_double_register_%i" % i] = list[i]
    return sp

def curpos_to_list(sp):
    """
    Converts current position state object to a list of 6 values.
    
    Args:
        sp: State object with output_double_register attributes.
        
    Returns:
        list: 6-element list [x, y, z, rx, ry, rz] of current position.
    """
    sp_list = []
    for i in range(0, 6):
        sp_list.append(sp.__dict__["output_double_register_%i" % i])
    return sp_list

def run():
    """
    Main control loop that manages robot communication and automation.
    Handles pose queue, force mode, tool outputs, and monitors robot state.
    """
    # logging.basicConfig(level=logging.INFO)
    config_filename = "control_loop_configuration.xml"

    conf = rtde_config.ConfigFile(config_filename)
    state_names, state_types = conf.get_recipe("state")
    setp_names, setp_types = conf.get_recipe("setp")
    watchdog_names, watchdog_types = conf.get_recipe("watchdog")
    force_enable_names, force_enable_types = conf.get_recipe("force_enable")
    tool_names, tool_types = conf.get_recipe("tool")

    con = rtde.RTDE(ROBOT_HOST, ROBOT_PORT)
    con.connect()

    # get controller version
    con.get_controller_version()

    # setup recipes
    con.send_output_setup(state_names, state_types)
    setp = con.send_input_setup(setp_names, setp_types)
    watchdog = con.send_input_setup(watchdog_names, watchdog_types)
    force_enable = con.send_input_setup(force_enable_names, force_enable_types)
    tool = con.send_input_setup(tool_names,tool_types)

    setp.input_double_register_0 = 0
    setp.input_double_register_1 = 0
    setp.input_double_register_2 = 0
    setp.input_double_register_3 = 0
    setp.input_double_register_4 = 0
    setp.input_double_register_5 = 0
    watchdog.input_int_register_0 = 0
    force_enable.input_double_register_6 = 0.0
    tool.input_double_register_7 = 0.0
    tool.input_double_register_8 = 0.0

    if not con.send_start():
        sys.exit()

    new_setp = [0, 0, 0, 0, 0, 0]
    prev_move_completed = True
    # keep robot exactly where it was on communication start
    list_to_setp(setp, [0, 0, 0, 0, 0, 0])
    con.send(setp)
    # prevent robot from entering force mode
    force_enable.input_double_register_6 = 0.0
    con.send(force_enable)
    # keep all tool digital outputs low on startup
    tool.input_double_register_7 = 0.0
    tool.input_double_register_8 = 0.0
    con.send(tool)

    # control loop
    while keep_running:
        state = con.receive()

        if state is None:
            break
        if prev_move_completed and state.output_int_register_0 == 1 and (not pose_queue.empty()):
            prev_move_completed = False
            new_setp = pose_queue.get_nowait()
            list_to_setp(setp, new_setp)
            con.send(setp)
            watchdog.input_int_register_0 = 1
        elif prev_move_completed and state.output_int_register_0 == 1 and enable_force_bool:
            force_enable.__dict__["input_double_register_6"] = 1.0
            con.send(force_enable)
        elif prev_move_completed and state.output_int_register_0 == 1 and not enable_force_bool:
            force_enable.__dict__["input_double_register_6"] = 0
            con.send(force_enable)
        elif not prev_move_completed and state.output_int_register_0 == 0:
            prev_move_completed = True
            watchdog.input_int_register_0 = 0

        curr_pose = curpos_to_list(state)
        try:
            if new_setp == [0, 0, 0, 0, 0, 0]:
                move_completed.put_nowait(0)
            else:
                for i in range(6):
                    if abs(curr_pose[i]-new_setp[i]) > TOL:
                        move_completed.put_nowait(0)
                        break
                    elif i == 5:
                        move_completed.put_nowait(1)
        except queue.Full:
            pass
        
        try:
            contact_made.put_nowait(state.output_int_register_1)
        except queue.Full:
            pass

        try:
            new_tool_outputs = tool_outputs.get_nowait()

            tool.input_double_register_7 = new_tool_outputs[0]
            tool.input_double_register_8 = new_tool_outputs[1]
        except queue.Empty:
            pass

        # update watchdog and tool outputs
        con.send(watchdog)
        con.send(tool)
        time.sleep(0.1)

    con.send_pause()

    con.disconnect()

def wait_move_complete():
    """
    Blocks until robot movement is complete.
    Polls the move_completed queue for completion signal.
    
    Returns:
        bool: True when movement is complete.
    """
    try:
        move_completed.get_nowait()
    except queue.Empty:
        pass
    while True: 
        try:
            if move_completed.get_nowait() == 1:
                break
            else:
                time.sleep(CHECK_INTERVAL)
        except queue.Empty:
            time.sleep(CHECK_INTERVAL)
    return True

def wait_contact_made():
    """
    Blocks until contact is made with the surface.
    Polls the contact_made queue for contact signal.
    
    Returns:
        bool: True when contact is detected.
    """
    try:
        contact_made.get_nowait()
    except queue.Empty:
        pass
    while True: 
        try:
            if contact_made.get_nowait() == 1:
                break
            else:
                time.sleep(CHECK_INTERVAL)
        except queue.Empty:
            time.sleep(CHECK_INTERVAL)
    return True
    
def move_and_wait(setp):
    pose_queue.put(setp)
    wait_move_complete()

# assumes at start of scan already
def scanning_routine():
    '''
    Executes a back-and-forth raster scan pattern within the defined scan bounding box.
    Moves along the y-direction for the initial scan, then shifts in x-direction by SCAN_PATH_WIDTH 
    and reverses y-direction for each subsequent pass until the entire area is covered.
    '''
    scan_width = abs(scan_bounding_box[0][0]-scan_bounding_box[2][0])
    scan_height = -abs(scan_bounding_box[0][1]-scan_bounding_box[2][1])
    num_passes = math.ceil(scan_width/(SCAN_PATH_WIDTH*MM_TO_M))
    scan_waypoint = scan_bounding_box[0]

    # perform initial scan along y-direction
    scan_waypoint[1] += scan_height
    move_and_wait(scan_waypoint)

    # move along x-direction and perform back-and-forth scans until reach edge of scan in x-direction
    for i in range(num_passes):
        # flip direction of scan in y-direction at each end
        scan_height *= -1

        # move along x-direction, capping motion at edge of scan bounding box
        if scan_waypoint[0] + SCAN_PATH_WIDTH * MM_TO_M >= scan_bounding_box[2][0]:
            scan_waypoint[0] = scan_bounding_box[2][0]
        else:
            scan_waypoint[0] += SCAN_PATH_WIDTH * MM_TO_M
        move_and_wait(scan_waypoint)

        # move along y-direction
        scan_waypoint[1] += scan_height
        move_and_wait(scan_waypoint)

def reset_leeb_tester():
    '''
    Reset the Leeb tester by extending the linear actuator for 5 seconds then retracting it for the same amount of time.
    '''
    tool_outputs.put([1.0, 0.0])
    time.sleep(5)
    tool_outputs.put([0.0, 0.0])
    time.sleep(5)

def take_measurement():
    '''
    Takes a measurement by briefly turning on the solenoid and off.
    '''
    tool_outputs.put([0.0, 1.0])
    time.sleep(0.5)
    tool_outputs.put([0.0, 0.0])

# BEGIN ROBOT COMMS
robot_comms = threading.Thread(target=run)
robot_comms.start()

print(r""" 
 ___   __    ______   ___   ___   _________     __   __   ______           ____        
/__/\ /__/\ /_____/\ /__/\ /__/\ /________/\   /_/\ /_/\ /_____/\         /___/\       
\::\_\\  \ \\:::_ \ \\::\ \\  \ \\__.::.__\/   \:\ \\ \ \\:::_ \ \        \_::\ \      
 \:. `-\  \ \\:\ \ \ \\::\/_\ .\ \  \::\ \      \:\ \\ \ \\:\ \ \ \   ___   \::\ \     
  \:. _    \ \\:\ \ \ \\:: ___::\ \  \::\ \      \:\_/.:\ \\:\ \ \ \ /__/\  _\: \ \__  
   \. \`-\  \ \\:\/.:| |\: \ \\::\ \  \::\ \      \ ..::/ / \:\_\ \ \\::\ \/__\: \__/\ 
    \__\/ \__\/ \____/_/ \__\/ \::\/   \__\/       \___/_/   \_____\/ \:_\/\________\/ 
                                                                                       """)
filename = input("Please enter the sample ID: ")
num_testpoints = int(input("Please enter the number of test points: "))
input("Press ENTER to begin scanning routine (ensure Polyscope program is running)...")


# SCANNING ROUTINE

pose_queue.put(scan_bounding_box[0])
wait_move_complete()
print("Moved to start of scan")


time.sleep(3)
mha.activate_window("JMStudio")
wait_and_click(startScan, message="Start button clicked")

scanning_routine()
print("Scan complete!")

#RUN IN ADMIN TO ALLOW CLICKING ON SCREEN
wait_and_click(stopScan, confidence=CONFIDENCE - 0.15, message="Stop button clicked")


# PROCESSING SCAN
wait_and_click(denoise, message="Denoise clicked")
wait_and_click(simplify, message="Simplify clicked")

wait_and_click(append, offset_x=200, message="Append right-side clicked")

pyautogui.write(filename, interval=0.05)

wait_and_click(apply, message="Apply clicked")
wait_and_click(apply, message="Apply clicked again")

time.sleep(1)
wait_until_gone(stopProcess, message="Done processing")
time.sleep(1)

pyautogui.hotkey("ctrl", "e")

wait_and_click(yes, message="Confirmation clicked")

time.sleep(0.3)

pyautogui.hotkey("alt", "d")
pyautogui.write(EXPORT_DIRECTORY, interval=0.03)
pyautogui.press("enter")
time.sleep(0.3)

for _ in range(7):
    pyautogui.press("tab")
    time.sleep(0.05)
pyautogui.write(filename + ".ply", interval=0.05)
pyautogui.press("enter")

print(f"Exported file: {filename}.ply")


time.sleep(5)
print("Beginning processing of scan data...")
result = process_ply(
    num_points=num_testpoints,
    ply_file=f"{filename}.ply",
    target_height=5.0,
    tolerance=2.0,
    csv_file="output_coordinates.csv",
    plot=True
)


# TESTING ROUTINE
if(str.lower(input("Press ENTER after verifying PLY file (type error if oriented wrong): ")) == "error"):
    # keep_running = False
    # robot_comms.join()  
    # raise Exception("Please rerun scan and verify new scan is oriented correctly.")
    test_points_csv = pd.read_csv("output_coordinates_working.csv")
else:
    test_points_csv = pd.read_csv("output_coordinates.csv")

required_cols = {"X_aligned", "Y_aligned", "Z_aligned"}
if not required_cols.issubset(test_points_csv.columns):
    raise ValueError(
        f"CSV must contain columns: {required_cols}"
    )

WORK_PLANE = 100
MM_TO_M = 0.001
TOOL_ORIENTATION = np.array([0,
                             3.14,
                             0],
                             dtype=float)
MAX_TRIES = 2
WINDOW_TITLE = "Beijing TIME High Technology Ltd. DataView TIME5100"

failed_points = []
begin_measurements()

test_points_csv.reset_index()
for index, row in test_points_csv.iterrows():
    test_point = np.array([row["X_aligned"],
                           row["Y_aligned"],
                           row["Z_aligned"]],
                           dtype=float)
    
    # transform test point in scan frame to robot base frame
    test_point = transform_to_baseframe(test_point)

    # convert from mm to m, change z-value to working plane, and append tool orientation before sending to robot
    test_point[2] = WORK_PLANE
    test_point_inm = test_point * MM_TO_M
    test_pose = np.append(test_point_inm, TOOL_ORIENTATION)

    # move robot to directly above test point
    print(f"Moving to {test_pose}")
    pose_queue.put(test_pose.tolist())
    wait_move_complete()

    # input("Press ENTER to reach next point...")
    # enable force mode, wait for contact
    print("Approaching test point")
    enable_force_bool = True
    wait_contact_made()

    # execute test, if measurement bad then retake test n number of times
    for i in range(MAX_TRIES):
        reset_leeb_tester()
        print(f"Measurement attempt {i+1}")
        take_measurement()
        # Wait for measurements to complete, allowing failed measurements
        activate_window(WINDOW_TITLE)
        time.sleep(0.1)
        measure_fail = check_window_issame(timeout=5)
        if measure_fail:
            if i == MAX_TRIES-1:
                print(f"Measurement {i+1} failed! Abandoning test point...")
                failed_points.append(index)
            else:
                print(f"Measurement {i+1} failed! Reattempting...")
        else:
            print(f"Measure {i+1} success!")
            break

    # disable force mode, wait for robot to return to last point
    print("Backing away from test point")
    enable_force_bool = False
    wait_move_complete()

export_hardness_data()


# PLOT DATA
create_combined_csv(
    csv_path="output_coordinates.csv",
    excel_path="data.xls",
    output_path="final_combined.csv",
    failed_indices=failed_points
)



plot_hardness_on_ply("aligned_ply_output.ply", "final_combined.csv", reduction=0.3, z_threshold=12.0)

keep_running = False
robot_comms.join()