import rclpy
from rclpy.action import ActionClient
from rclpy.action import ActionServer
from rclpy.node import Node
from audio_common_msgs.action import TTS
from std_msgs.msg import String
from trh_msgs.action import StringAction
from trh_msgs.action import BlankToBool

class auto_tts(Node):
    def __init__(self):
        super().__init__('input_sender')
        # this is one way to request speech
        self.subscription = self.create_subscription(
            String,
            'TTS_text',
            self.send_goal,
            10)
        # asking for the status of the speech
        # self.speaking_req = self.ActionServer(
        #     self,
        #     BlankToBool,
        #     'is_speaking',
        #     self.is_speaking_callback
        # )
        # main way to request speech, the equivalent of "/say" for tts_ros
        self.server = ActionServer(
            self,
            StringAction,
            'TTS_action',
            self.execute_callback
        )
        self.speaking = False
        self._action_client = ActionClient(self, TTS, 'say')
        self.get_logger().info("Init done.")

    # this is the callback for the "is_speaking" request, just returns true or false
    def is_speaking_callback(self, goal_handle):
        self.get_logger().info('Executing goal...')
        result = BlankToBool.Result()
        result.result = self.speaking
        goal_handle.succeed()
        return result

    # this is the callback for the main way to request speech
    def execute_callback(self, goal_handle):
        self.get_logger().info('Executing goal...')
        self.speaking = True
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

    # sends a goal to tts_ros
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
    
    # checks if tts_ros has accepted the goal
    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('tts_ros has rejected request.')
            return
    
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    # when tts_ros is done speaking, we can set speaking to false, and 
    def get_result_callback(self, future):
        result = future.result().result
        # self.get_logger().info('Result: {0}'.format(result.text))
        self.speaking = False

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback


def main(args = None):
    rclpy.init(args=args)
    action_client = auto_tts()
    rclpy.spin(action_client)

if __name__ == '__main__':
    main()