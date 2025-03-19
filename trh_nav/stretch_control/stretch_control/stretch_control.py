import rclpy
import time
from rclpy.action import ActionServer
from rclpy.node import Node
from trh_msgs.action import StringAction
from std_msgs.msg import String
import hello_helpers.hello_misc as hm
import stretch_body.robot
import threading

class RobotControlServer(Node):

    def __init__(self, hello_node):
        super().__init__('stretch_control')
        self._action_server = ActionServer(
            self,
            StringAction,
            'stretch_control_real',
            self.execute_callback)
        self.error_publish = self.create_publisher(String, 'errors', 10)
        
        self.robot = stretch_body.robot.Robot()
        self.hello_node = hello_node
        # if not self.robot.startup():
        #     self.get_logger().info('Robot failed to start up')
        #     self.error_publish.publish(String(data="Control:Robot has not started up"))
        #     exit()
        # if not self.robot.is_homed():
        #     self.error_publish.publish(String(data="Homing Robot"))
        #     self.home_robot()

        self.get_logger().info('Init done.')

    def execute_callback(self, goal_handle):
        self.get_logger().info('Executing goal...')
        result = StringAction.Result()
        feedback = StringAction.Feedback()
        nums = goal_handle.request.strrequest.split(",")
        match nums[0]:
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
            case _:
                self.get_logger().info("Invalid robot movement order.")
                goal_handle.succeed()
        return result
    
    def home_robot(self):
        self.get_logger().info('Homing Robot.')
        self.robot.home()
    
    def move_head(self, tilt, pan=0):
      self.hello_node.switch_to_position_mode()
      self.hello_node.move_to_pose({'joint_head_tilt': float(tilt), 'joint_head_pan': float(pan)}, blocking=True)
      self.hello_node.switch_to_navigation_mode()

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