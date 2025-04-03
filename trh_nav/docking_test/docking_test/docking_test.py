import rclpy
import time
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from geometry_msgs.msg import Twist
from hello_helpers import hello_misc as hm
from sensor_msgs.msg import JointState
import threading

class JointState():
    def __init__(self):
        self.name = []
        self.position = []
        self.velocity = []
        self.effort = []

    def __repr__(self):
        return f"JointState(name={self.name}, position={self.position}, velocity={self.velocity}, effort={self.effort})"
    
    def set(self, nameList, positionList, velocityList, effortList):
        self.name = nameList
        self.position = positionList
        self.velocity = velocityList
        self.effort = effortList

    def get(self):
        return self.name, self.position, self.velocity, self.effort

class DockingControl(Node):
    def __init__(self):
        super().__init__('docking_control')
        self.hello_node = hm.HelloNode.quick_create('hello')
        self.precision_mode = False
        self.fast_base_mode = False

        # Initialize command objects
        self.base_command = CommandBase()
        self.lift_command = CommandLift()
        self.arm_command = CommandArm()
        self.head_pan_command = CommandHeadPan()
        self.head_tilt_command = CommandHeadTilt()

        # Threading for control loop
        self.wait_between_executions = 1.0 / 15.0
        self.stop_loop = False
        self.lock = threading.Lock()
        self._init_command()
        self.controller_thread = threading.Thread(target=self.controller_loop, daemon=True)
        self.controller_thread.start()

        self.vel_pub = self.create_publisher(Twist, 'stretch/cmd_vel', 10)
        self.vel_msg = Twist()
        self.joint_sub = self.create_subscription(JointState, 'stretch/joint_states', self.joint_state_callback, 10)
        # string[] name
        # float64[] position
        # float64[] velocity
        # float64[] effort
        self.current_joints = JointState()

    def joint_state_callback(self, msg):
        self.current_joints.set(msg.name, msg.position, msg.velocity, msg.effort)


    def _init_command(self):
        with self.lock:
            self.new_command_received = False
            self.command = {'num': 0, 'time': time.time(), 'cmd': None}

    def stop(self):
        with self.lock:
            self.stop_loop = True
            self.new_command_received = False
            self.command['num'] += 1
            self.command['time'] = time.time()
            self.command['cmd'] = zero_vel.copy()
            self._execute(self.command)

    def set_command(self, cmd):
        with self.lock:
            self.command['num'] += 1
            self.command['time'] = time.time()
            self.command['cmd'] = cmd.copy()
            self.new_command_received = True

    def controller_loop(self):
        while True:
            with self.lock:
                if self.stop_loop:
                    exit()
                if self.new_command_received:
                    self._execute(self.command)
                    self.new_command_received = False
            time.sleep(self.wait_between_executions)

    def _execute(self, norm_vel_cmd):
        cmd = norm_vel_cmd['cmd']
        if cmd is not None:
            # Base Control
            if 'base_forward' in cmd or 'base_counterclockwise' in cmd:
                vf = cmd.get('base_forward', 0.0)
                vcc = cmd.get('base_counterclockwise', 0.0)
                self.base_command.command_stick_to_motion(vcc, vf, self.hello_node)

            # Lift Control
            if 'lift_up' in cmd:
                v = cmd['lift_up']
                self.lift_command.command_stick_to_motion(v, self.hello_node)

            # Arm Control
            if 'arm_out' in cmd:
                v = cmd['arm_out']
                self.arm_command.command_stick_to_motion(v, self.hello_node)

            # Head Control
            if 'head_pan_counterclockwise' in cmd:
                v = cmd['head_pan_counterclockwise']
                self.head_pan_command.command_stick_to_motion(v, self.hello_node)
            if 'head_tilt_up' in cmd:
                v = cmd['head_tilt_up']
                self.head_tilt_command.command_stick_to_motion(v, self.hello_node)

class CommandBase:
    # ...existing code from normalized_velocity_control.py...

class CommandLift:
    # ...existing code from normalized_velocity_control.py...

class CommandArm:
    # ...existing code from normalized_velocity_control.py...

class CommandHeadPan:
    # ...existing code from normalized_velocity_control.py...

class CommandHeadTilt:
    # ...existing code from normalized_velocity_control.py...

zero_vel = {
    'base_forward': 0.0,
    'base_counterclockwise': 0.0,
    'lift_up': 0.0,
    'arm_out': 0.0,
    'head_pan_counterclockwise': 0.0,
    'head_tilt_up': 0.0,
}

def main(args=None):

    rclpy.init(args=args)
    docking_control = DockingControl()

    # Spin hello_node in a separate thread
    hello_node_thread = threading.Thread(target=spin_hello_node, args=(docking_control.hello_node,), daemon=True)
    hello_node_thread.start()

    rclpy.spin(docking_control)
    docking_control.destroy_node()
    rclpy.shutdown()

def spin_hello_node(hello_node):
    executor = MultiThreadedExecutor()
    executor.add_node(hello_node)
    executor.spin()
    executor.shutdown()

if __name__ == '__main__':
    main()