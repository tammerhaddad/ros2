import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from trh_msgs.action import StringAction

class strActionClient(Node):

    def __init__(self):
        super().__init__('trh_action_client')
        self.client = ActionClient(self, StringAction, 'trh_srv')

    def send_goal(self, request):
        goal_msg = StringAction.Goal()
        goal_msg.strrequest = request

        self.client.wait_for_server()
        self._send_goal_future = self.client.send_goal_async(
            goal_msg, feedback_callback=self.feedback_callback)
        self._send_goal_future.add_done_callback(self.goal_response_callback)
    
    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Goal rejected :(')
            return

        self.get_logger().info('Goal accepted :)')

        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        result = future.result().result
        self.get_logger().info('Result: {0}'.format(result.strresult))
        rclpy.shutdown()

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        self.get_logger().info('Feedback: {0}'.format(feedback.strfeedback))

def main(args=None):
    rclpy.init(args=args)

    action_client = strActionClient()

    action_client.send_goal("zero ")

    rclpy.spin(action_client)


if __name__ == '__main__':
    main()