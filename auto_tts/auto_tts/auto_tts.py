import rclpy
from rclpy.action import ActionClient
from rclpy.action import ActionServer
from rclpy.node import Node
from audio_common_msgs.action import TTS
from std_msgs.msg import String
from trh_msgs.msg import Num
from trh_msgs.action import StringAction

class auto_tts(Node):
    def __init__(self):
        super().__init__('input_sender')
        self.subscription = self.create_subscription(
            String,
            'TTS_text',
            self.send_goal,
            10)
        self.publisher = self.create_publisher(
            Num,
            'yappin',
            10)
        self.server = ActionServer(
            self,
            StringAction,
            'TTS_action',
            self.execute_callback
        )
        self._action_client = ActionClient(self, TTS, 'say')
        self.get_logger().info("Init done.")

    def execute_callback(self, goal_handle):
        self.get_logger().info('Executing goal...')
        num = Num()
        num.num = 0
        self.publisher.publish(num)
        result = StringAction.Result()
        feedback = StringAction.Feedback()
        msg = TTS
        msg.data = goal_handle.request.strrequest
        self.send_goal(msg)
        feedback.strfeedback = msg.data
        goal_handle.publish_feedback(feedback)
        result.strresult = msg.data
        goal_handle.succeed()
        return result

    def send_goal(self, msg):
        goal_msg = TTS.Goal()
        goal_msg.text = str(msg.data)
        
        self._action_client.wait_for_server()
        self._send_goal_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )
        # self.get_logger().info('Sending TTS goal: ' + goal_msg.text)
        self._send_goal_future.add_done_callback(self.goal_response_callback)
    
    def goal_response_callback(self, future):
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().info('Goal rejected.')
            return
        
        self.get_logger().info('Goal accepted.')
        self._get_result_future = goal_handle.get_result_async()
        res = self._get_result_future.result()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        result = future.result().result
        self.get_logger().info('Result: {0}'.format(result.text))
        msg = Num()
        msg.num = 1
        self.publisher.publish(msg)

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        # self.get_logger().info('Received feedback: {0}'.format(feedback.partial_sequence)


def main(args = None):
    rclpy.init(args=args)
    action_client = auto_tts()
    rclpy.spin(action_client)

if __name__ == '__main__':
    main()