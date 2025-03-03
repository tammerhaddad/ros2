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
        self.get_logger().info('Init done.')

    def execute_callback(self, goal_handle):
        self.get_logger().info('Executing goal...')
        nums = goal_handle.request.strrequest.split("-")
        result = StringAction.Result()
        feedback = StringAction.Feedback()
        feedback.strfeedback = ""
        goal_handle.publish_feedback(feedback)
        result.strresult = "Done: tilt {tilt}, pan {pan}"
        goal_handle.succeed()
        return result
    
    def move_head(self, tilt, pan=0):
      self.robot.head.move_to('head_pan',pan)
      self.robot.head.move_to('head_tilt',tilt)

      # self.hello_node.switch_to_position_mode()
      # self.hello_node.move_to_pose({'joint_head_tilt': float(tilt), 'joint_head_pan': float(pan)}, blocking=True)
      # self.hello_node.switch_to_navigation_mode()



def main(args=None):
    rclpy.init(args=args)

    action_server = RobotControlServer()

    rclpy.spin(action_server)


if __name__ == '__main__':
    main()