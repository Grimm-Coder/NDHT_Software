import sys
import math

sys.path.append("..")
import logging

import rtde.rtde as rtde
import rtde.rtde_config as rtde_config


# logging.basicConfig(level=logging.INFO)

ROBOT_HOST = "10.36.196.112"
ROBOT_PORT = 30004
config_filename = "control_loop_configuration.xml"

keep_running = True

logging.getLogger().setLevel(logging.INFO)

conf = rtde_config.ConfigFile(config_filename)
state_names, state_types = conf.get_recipe("state")
setp_names, setp_types = conf.get_recipe("setp")
watchdog_names, watchdog_types = conf.get_recipe("watchdog")

con = rtde.RTDE(ROBOT_HOST, ROBOT_PORT)
con.connect()

# get controller version
con.get_controller_version()

# setup recipes
con.send_output_setup(state_names, state_types)
setp = con.send_input_setup(setp_names, setp_types)
watchdog = con.send_input_setup(watchdog_names, watchdog_types)

# Setpoints to move the robot to
# index 0-2: position, in m, relative to base
# index 3-5: orientation, in rad, relative to base

# current setpoints will move robot arm in box shape with side lengths 150mm
setp1 = [-0.15, -0.24, 0.15, 0, 3.14, 0]
setp2 = [-0.10, -0.24, 0.15, 0, 3.14, 0]
setp3 = [-0.10, -0.2, 0.15, 0, 3.14, 0]
setp4 = [-0.15, -0.2, 0.15, 0, 3.14, 0]

assert math.sqrt(setp1[0]**2 + setp1[1]**2 + setp1[2]**2) <= 0.45
assert math.sqrt(setp2[0]**2 + setp2[1]**2 + setp2[2]**2) <= 0.45
assert math.sqrt(setp3[0]**2 + setp3[1]**2 + setp3[2]**2) <= 0.45
assert math.sqrt(setp4[0]**2 + setp4[1]**2 + setp4[2]**2) <= 0.45

setp.input_double_register_0 = 0
setp.input_double_register_1 = 0
setp.input_double_register_2 = 0
setp.input_double_register_3 = 0
setp.input_double_register_4 = 0
setp.input_double_register_5 = 0

# The function "rtde_set_watchdog" in the "rtde_control_loop.urp" creates a 1 Hz watchdog
watchdog.input_int_register_0 = 0

def setp_to_list(sp):
    sp_list = []
    for i in range(0, 6):
        sp_list.append(sp.__dict__["input_double_register_%i" % i])
    return sp_list

def list_to_setp(sp, list):
    for i in range(0, 6):
        sp.__dict__["input_double_register_%i" % i] = list[i]
    return sp


# start data synchronization
if not con.send_start():
    sys.exit()

# control loop
i = -1
move_completed = True
while keep_running:
    # receive the current state
    state = con.receive()

    if state is None:
        break

    # do something...
    if move_completed and state.output_int_register_0 == 1:
        move_completed = False
        if (setp_to_list(setp) == setp1):
            new_setp = setp2
        elif (setp_to_list(setp) == setp2):
            new_setp = setp3
        elif (setp_to_list(setp) == setp3):
            new_setp = setp4
        else:
            new_setp = setp1
            
        list_to_setp(setp, new_setp)
        print("New pose = " + str(new_setp))
        # send new setpoint
        con.send(setp)
        watchdog.input_int_register_0 = 1
    elif not move_completed and state.output_int_register_0 == 0:
        print("Move to confirmed pose = " + str(state.target_q))
        move_completed = True
        watchdog.input_int_register_0 = 0

    # kick watchdog
    con.send(watchdog)

con.send_pause()

con.disconnect()
