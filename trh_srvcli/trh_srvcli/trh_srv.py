import rclpy
import time
from rclpy.action import ActionServer
from rclpy.node import Node

from trh_msgs.action import StringAction

class TRHActionServer(Node):

    def __init__(self):
        super().__init__('trh_action_server')
        self._action_server = ActionServer(
            self,
            StringAction,
            'trh_srv',
            self.execute_callback)
        self.get_logger().info('Init done.')

    def execute_callback(self, goal_handle):
        self.get_logger().info('Executing goal...')
        result = StringAction.Result()
        feedback = StringAction.Feedback()
        feedback.strfeedback = ""
        feedback.strfeedback = goal_handle.request.strrequest + " + one"
        goal_handle.publish_feedback(feedback)
        feedback.strfeedback = goal_handle.request.strrequest + " + two"
        goal_handle.publish_feedback(feedback)
        result.strresult = goal_handle.request.strrequest + "+ three" 
        goal_handle.succeed()
        return result


def main(args=None):
    rclpy.init(args=args)

    action_server = TRHActionServer()

    rclpy.spin(action_server)


if __name__ == '__main__':
    main()