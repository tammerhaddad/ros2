import rclpy
import time
from rclpy.action import ActionServer
from rclpy.node import Node
from trh_msgs.action import StringAction
from std_msgs.msg import String
import hello_helpers.hello_misc as hm
import threading

from geometry_msgs.msg import Twist
from geometry_msgs.msg import Vector3
from sensor_msgs.msg import JointState
from sensor_msgs.msg import BatteryState

# not currently used, but can store the joint states in a class for easier access
# the different sections are based on the information given by "stretch/joint_states"
class MyJointState():
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

# main control node
class RobotControlServer(Node):

    def __init__(self, hello_node):
        super().__init__('stretch_control')
        self._action_server = ActionServer(
            self,
            StringAction,
            'stretch_control',
            self.execute_callback)
        self.error_publish = self.create_publisher(String, 'errors', 10)
        # hello node is used to control the robot via rviz driver
        self.hello_node = hello_node
        # this publishes Twist commands to the robot wheels
        self.vel_pub = self.create_publisher(Twist, 'stretch/cmd_vel', 10)
        # this recieves the joint states of the robot, including name, position, velocity, and effort
        self.joint_sub = self.create_subscription(JointState, 'stretch/joint_states', self.joint_state_callback, 10)
        # this recieves the battery state of the robot, including voltage and current
        self.bat_sub = self.create_subscription(BatteryState, 'battery', self.battery_callback, 10)
        self.charging = False
        self.current_joints = MyJointState()
        # initializes this, currently dont actually need it because of vel_publish, which lets me plug in the info
        self.vel_msg = Twist()
        self.vel_publish = lambda self, v_m, w_r: self.vel_pub.publish(Twist(linear=Vector3(x=v_m, y=0, z=0), angular=Vector3(z=w_r, y=0, x=0)))
        # self.vel_publish = lambda self, v_m, w_r: self.vel_pub.publish(Twist(linear={'x': v_m, 'y': 0, 'z': 0}, angular={'z': w_r, 'y': 0, 'x': 0}))
        self.get_logger().info('Init done.')
        # for calibration at the beginning
        self.temp_battery_calculator = []
        # after calibration, this is the battery voltage when not plugged in
        self.battery_base = None

    # this just keeps the current joints updated
    def joint_state_callback(self, msg):
        self.current_joints.set(msg.name, msg.position, msg.velocity, msg.effort)

    def battery_callback(self, msg):
        # this is used to calibrate the battery voltage when not plugged in
        if self.battery_base is None:
            self.temp_battery_calculator.append(msg.voltage)
            if len(self.temp_battery_calculator) > 20:
                self.battery_base = sum(self.temp_battery_calculator) / len(self.temp_battery_calculator) + 0.2
                self.get_logger().info(f'Battery base set to {self.battery_base}')
                self.temp_battery_calculator = None
                
            return
        
        # this is post calibration, we just check if the robot is charging or not.
        # if it changes, we log the change
        if msg.voltage > self.battery_base:
            if not self.charging:
                self.get_logger().info('Battery is charging.')
            self.charging = True
        else:
            if self.charging:
                self.get_logger().info('Battery is not charging.')
            self.charging = False

    # server callback
    def execute_callback(self, goal_handle):
        self.get_logger().info('Executing goal...')
        result = StringAction.Result()
        feedback = StringAction.Feedback()
        # right now the goal is just a string, so we split it by commas to get the different parts
        nums = goal_handle.request.strrequest.split(",")
        # the first part is the command, the rest are the arguments
        match nums[0]:
            # these are all self explanatory, broken up into different sections based on what they do,
            # and adding more is simple, just add a new case to the match statement
            case "control":
                secondary = nums[1]
                match secondary:
                    case "cam":
                        tilt = float(nums[1])
                        pan = float(nums[2])
                        feedback.strfeedback = "Recieved: tilt {tilt}, pan {pan}. Moving head..."
                        goal_handle.publish_feedback(feedback)
                        self.move_head(tilt, pan)
                        feedback.strfeedback = "Head moved to tilt {tilt}, pan {pan}."
                        goal_handle.publish_feedback(feedback)
                        result.strresult = "Done: tilt {tilt}, pan {pana}"
                        goal_handle.succeed()
                        self.get_logger().info("Goal Complete: {goal_handle.request.strrequest}")
                    case "home":
                        feedback.strfeedback = "Homing robot..."
                        goal_handle.publish_feedback(feedback)
                        self.home_robot()
                        feedback.strfeedback = "Robot homed."
                        goal_handle.publish_feedback(feedback)
                        result.strresult = "Done: Robot homed."
                        goal_handle.succeed()
                    case "stop":
                        feedback.strfeedback = "Stopping robot..."
                        goal_handle.publish_feedback(feedback)
                        self.stop_robot()
                        feedback.strfeedback = "Robot stopped."
                        goal_handle.publish_feedback(feedback)
                        result.strresult = "Done: Robot stopped."
                        goal_handle.succeed()
                    case "position":
                        feedback.strfeedback = "Getting robot position..."
                        goal_handle.publish_feedback(feedback)
                        xya = self.get_robot_position()
                        feedback.strfeedback = f"Robot position: {xya}"
                        goal_handle.publish_feedback(feedback)
                        result.strresult = f"Done: Robot position: {xya}"
                        goal_handle.succeed()
                    case "rotate":
                        feedback.strfeedback = "Rotating robot..."
                        goal_handle.publish_feedback(feedback)
                        theta = float(nums[2])
                        self.rotate_to(theta)
                        feedback.strfeedback = f"Robot rotated to {theta}."
                        goal_handle.publish_feedback(feedback)
                        result.strresult = f"Done: Robot rotated to {theta}."
                        goal_handle.succeed()
                    case _:
                        self.get_logger().info("Invalid robot control order.")
            case "info":
                secondary = nums[1]
                match secondary:
                    case "charging":
                        feedback.strfeedback = "Getting robot charging status..."
                        goal_handle.publish_feedback(feedback)
                        charging = self.is_charging()
                        feedback.strfeedback = f"Robot charging: {charging}"
                        goal_handle.publish_feedback(feedback)
                        result.strresult = f"Done: Robot charging: {charging}"
                        goal_handle.succeed()
                    case "joints":
                        feedback.strfeedback = "Getting robot joints..."
                        goal_handle.publish_feedback(feedback)
                        joints = self.joint_states()
                        feedback.strfeedback = f"Robot joints: {joints}"
                        goal_handle.publish_feedback(feedback)
                        result.strresult = f"Done: Robot joints: {joints}"
                        goal_handle.succeed()
                    case _:
                        self.get_logger().info("Invalid robot control order.")
            case _:
                self.get_logger().info("Invalid robot movement order.")
            
        goal_handle.succeed()
        return result
    

    # just a bunch of functions for the above commands
    def home_robot(self):
        self.get_logger().info('Homing Robot.')
        self.hello_node.home_the_robot()
        self.hello_node.stow_the_robot()
    
    def stop_robot(self):
        self.get_logger().info('Stopping Robot.')
        self.hello_node.stop_the_robot()

    def get_robot_position(self):
        self.get_logger().info('Getting Robot position.')
        xya, time = self.hello_node.get_robot_floor_pose_xya(floor_frame='map')
        # xya = [x, y, angle]
        self.get_logger().info(f'Robot position: (x: {xya[0]}, y: {xya[1]}, angle: {xya[2]})')
        return xya
    
    def is_charging(self):
        return self.charging
    
    def joint_states(self):
        return self.current_joints.get()
    
    def move_head(self, tilt, pan=0):
      self.hello_node.switch_to_position_mode()
      self.hello_node.move_to_pose({'joint_head_tilt': float(tilt), 'joint_head_pan': float(pan)}, blocking=True)
      self.hello_node.switch_to_navigation_mode()

    def rotate_to(self, theta):
        cur_ang = self.get_robot_position()[2]
        goal_ang = theta
        while cur_ang - goal_ang > 0.02:
            self.vel_publish(self, 0, 0.1)
            time.sleep(0.1)
            cur_ang = self.get_robot_positifon()[2]

# initializes the node and starts the action server
def main(args=None):

    hello_node = hm.HelloNode.quick_create('hello')
    action_server = RobotControlServer(hello_node)
    executor = rclpy.executors.MultiThreadedExecutor(num_threads=10)
    executor.add_node(action_server)
    executor_thread = threading.Thread(target=executor.spin, daemon=True)
    executor_thread.start()
    rclpy.spin(action_server)


if __name__ == '__main__':
    main()