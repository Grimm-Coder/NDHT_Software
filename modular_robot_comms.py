import rtde.rtde as rtde
import rtde.rtde_config as rtde_config

import queue
import threading
import time

class UR3e_Comms:
    def __init__(self, CONFIG, IP, PORT = 30004, LOG = False):
        '''
        Initialize an instance of communications with the UR3e robot. 
        ***WARNING*** Only have one instance of this class running at a time!

        Args:
        CONFIG - String of absolute path to the XML file containing configuration information for inputs/outputs of UR3e. (Note: current class implementation assumes only 6 outputs (for pose information), 1 input (for move complete information), and 1 watchdog bit.)
        IP - String of the fixed UR3e robot IP address
        PORT (Default 30004) - Integer port of the UR3e robot where communications. (Note: Do not change unless specifically changed communication port in Polyscope software.)
        '''
        self._IP = IP
        self._PORT = PORT
        self._CONFIG = CONFIG
        self._LOG = LOG

        self._conf = rtde_config.ConfigFile(self._CONFIG)
        self._state_names, self._state_types = self._conf.get_recipe("state")
        self._setp_names, self._setp_types = self._conf.get_recipe("setp")
        self._watchdog_names, self._watchdog_types = self._conf.get_recipe("watchdog")
        # self._tool_names, self._tool_types = self._conf.get_recipe("tool")
        self._con = rtde.RTDE(self._IP, self._PORT)

        self._pose_queue = queue.Queue()
        self._tool_outputs = queue.Queue()

        self._thread = threading.Thread(self._connect())


    def _list_to_setp(sp, list):
        for i in range(0, 6):
            sp.__dict__["input_double_register_%i" % i] = list[i]
        return sp

    def connect(self):
        self._connect()

    def _connect(self):
        self._con.connect()

        # setup recipes
        self._con.send_output_setup(self._state_names, self._state_types)
        self._setp = self._con.send_input_setup(self._setp_names, self._setp_types)
        self._watchdog = self._con.send_input_setup(self._watchdog_names, self._watchdog_types)
        # self._tool = self._con.send_input_setup(self._tool_names, self._tool_types)

        if not self._con.send_start():
            if self._LOG: print("Start command failed!") # replace with error throw
        else:
            if self._LOG: print("Start command sent successfully!")
        
        # watchdog = 1 means in process of sending pose
        # watchdog = 0 means pose has been confirmed by robot
        self._watchdog.input_int_register_0 = 0
        prev_move_transmitted = True
        while True:
            state = self._con.receive()

            # print("state.output_int_register_0 = ", state.output_int_register_0)
            # print("prev_move_transmitted = ", prev_move_transmitted)
            # print("self._pose_queue.empty() = ", self._pose_queue.empty())
            if prev_move_transmitted and state.output_int_register_0 == 1 and not self._pose_queue.empty():
                prev_move_transmitted = False
                
                new_setp = self._pose_queue.get_nowait()
                self._list_to_setp(self._setp, new_setp)
                if self._LOG: print("Sending pose - " + str(new_setp)) 
                # send new setpoint
                self._con.send(self._setp)
                self._watchdog.input_double_register_6 = 1.0
            elif not prev_move_transmitted and state.output_int_register_0 == 0:
                if self._LOG: print("Pose confirmed - " + str(state.target_q))
                prev_move_transmitted = True
                self._watchdog.input_double_register_6 = 0.0

            # GIVE THOUGHT ON HOW TOOL OUTPUTS ARE UPDATED
            # if state.output_int_register_0 == 1 and not self._tool_outputs.empty():
            #     pass # send the tool outputs that have now been set

            # kick watchdog
            # if self._LOG: print("Watchdog kicked")
            self._con.send(self._watchdog)
            time.sleep(0.1)
            
    def send_pose(self, pose):
        '''
        Enqueue a pose to be sent to the UR3e robot. Will be executed using FIFO if other moves queued, and will be executed immediately if no other moves are queued.

        Args:
        pose - A six-element list of the form [px, py, pz, rx, ry, rz]
        '''
        self._pose_queue.put(pose)
        
        
    def send_tool_doutputs(self, tool_doutputs):
        '''
        Enqueues both digital tool outputs to be sent to the UR3e. Will be executed using FIFO if other tool outputs queued, and will be executed immediately if no other outputs are queued.

        Args:
        tool_doutputs - A two-element list of the form [digital_output1, digital_output2]
        '''
        self._tool_doutputs.put(tool_doutputs)

    def check_queue_empty(self):
        '''
        Checks if no poses are in the queue (i.e. all prev poses have been sent)

        Args:
        None
        '''
        return self._pose_queue.empty()

import threading

if __name__ == '__main__':
    
    test_connection = UR3e_Comms("control_loop_configuration.xml", "10.36.196.112", 30004, True)

    test_connection.connect()

    print("do we reach here?")

    # move between three points
    setp1 = [-0.15, -0.24, 0.15, 0, 3.14, 0]
    setp2 = [-0.10, -0.24, 0.15, 0, 3.14, 0]
    setp3 = [-0.10, -0.2, 0.15, 0, 3.14, 0]
    test_connection.send_pose(setp1)
    test_connection.send_pose(setp2)
    test_connection.send_pose(setp3)

    # wait till all moves have been sent
    while test_connection.check_queue_empty():
        print("Waiting...")
        pass