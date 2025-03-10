import rclpy
import time
from rclpy.action import ActionServer
from rclpy.node import Node
from trh_msgs.action import StringAction

import hello_helpers.hello_misc as hm
import stretch_body.robot

class RobotControlServer(Node):

    def __init__(self):
        super().__init__('stretch_control')
        self._action_server = ActionServer(
            self,
            StringAction,
            'stretch_control',
            self.execute_callback)
        
        self.robot = stretch_body.robot.Robot()
        self.hello_node = hm.HelloNode()
        if not self.robot.startup():
            self.get_logger().info('Robot failed to start up')
            exit()
        if not self.robot.is_calibrated():
            self.home_robot()

        self.get_logger().info('Init done.')

    def execute_callback(self, goal_handle):
        self.get_logger().info('Executing goal...')
        result = StringAction.Result()
        feedback = StringAction.Feedback()
        nums = goal_handle.request.strrequest.split("-")
        tilt = float(nums[0])
        pan = float(nums[1])
        arm = 0
        if len(nums) > 2:
            arm = float(nums[2])
        
        feedback.strfeedback = "Recieved: tilt {tilt}, pan {pan}. Moving head..."
        goal_handle.publish_feedback(feedback)
        self.move_head(tilt, pan, arm)
        feedback.strfeedback = "Head moved to tilt {tilt}, pan {pan}."
        goal_handle.publish_feedback(feedback)
        result.strresult = "Done: tilt {tilt}, pan {pan}"
        goal_handle.succeed()
        self.get_logger().info("Goal Complete: {goal_handle.request.strrequest}")
        return result
    
    def home_robot(self):
        self.get_logger().info('Homing Robot.')
        self.robot.home()
    
    def move_head(self, tilt, pan=0, arm=0):
      self.robot.head.move_to('head_pan',pan)
      self.robot.head.move_to('head_tilt',tilt)

def main(args=None):
    rclpy.init(args=args)

    action_server = RobotControlServer()

    rclpy.spin(action_server)


if __name__ == '__main__':
    main()