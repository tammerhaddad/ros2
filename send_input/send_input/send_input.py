import rclpy
import os
from openai import OpenAI
from rclpy.action import ActionClient
from rclpy.node import Node
from audio_common_msgs.action import TTS
from parcs_stt_tts_msgs.action import TTS as parcs_TTS
from std_msgs.msg import String
import time

class InputSender(Node):

    def __init__(self):
        super().__init__('input_sender')
        # self._action_client = ActionClient(self, TTS, 'say')
        self.subscription = self.create_subscription(
            String,
            'input_text',
            self.send_goal,
            10)
        self.publisher = self.create_publisher(
            String,
            'prompt_text',
            10)
        # self.subscription

        self.declare_parameter('tts_package', 'parcs')
        tts_package = self.get_parameter('tts_package').get_parameter_value().string_value
        if tts_package == 'parcs':
            self._action_client = ActionClient(self, parcs_TTS, 'tts')
        elif tts_package == 'ros':
            self._action_client = ActionClient(self, TTS, 'say')
        else:
            self.get_logger().error('Invalid TTS package specified. Please specify either "parcs" or "ros"')
            rclpy.shutdown()

        self.publisher2 = self.create_publisher(String, 'times', 10)
        self.prompt_history = [{"role": "system", "content": "You are a helpful assistant."}]

    def send_goal(self, msg):
        if self.get_parameter('tts_package').get_parameter_value().string_value == 'parcs':
            goal_msg = parcs_TTS.Goal()
        else:
            goal_msg = TTS.Goal()
        
        current_time = time.strftime('%H:%M:%S', time.localtime())
        milliseconds = int((time.time() % 1) * 1000)
        self.publisher2.publish(String(data='[{time}:{milliseconds}]: Input Recieved: {text}'.format(time=current_time, milliseconds=milliseconds, text = msg.data)))
                
        self.get_logger().info('Inputting prompt: {0}'.format(msg.data))

        response = self.generate_text(msg.data)
        
        self.prompt_history.append({"role": "assistant", "content": response})

        current_time = time.strftime('%H:%M:%S', time.localtime())
        milliseconds = int((time.time() % 1) * 1000)
        self.publisher2.publish(String(data='[{time}:{milliseconds}]: Response generated: {response}'.format(time=current_time, milliseconds=milliseconds, response = response)))
        
        self.get_logger().info('API response: \n{0}\n'.format(response))

        if self.get_parameter('tts_package').get_parameter_value().string_value == 'parcs':
            goal_msg.tts = response
        elif self.get_parameter('tts_package').get_parameter_value().string_value == 'ros':
            goal_msg.text = str(response)

        self._action_client.wait_for_server()
        self._send_goal_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )

        self.publisher.publish(String(data=response))
        current_time = time.strftime('%H:%M:%S', time.localtime())
        milliseconds = int((time.time() % 1) * 1000)
        self.publisher2.publish(String(data='[{time}:{milliseconds}]: Response Sent.'.format(time=current_time, milliseconds=milliseconds)))

        self._send_goal_future.add_done_callback(self.goal_response_callback)
    
    def goal_response_callback(self, future):
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().info('Goal rejected.')
            return
        
        self.get_logger().info('Goal accepted.')
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        result = future.result().result
        # self.get_logger().info('Result: {0}'.format(result.sequence))
        # rclpy.shutdown()

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        # self.get_logger().info('Received feedback: {0}'.format(feedback.partial_sequence)

    def generate_text(self, prompt):
        chat_completion = "I heard.  {0}".format(prompt)
        
        # with open(os.path.expanduser("~/.trhapi.txt"), "r") as file:
        #     key = file.read()
        self.prompt_history.append({"role": "user", "content": prompt})
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        chat_completion = client.chat.completions.create(
            messages=self.prompt_history,
            model="gpt-4",
        )

        return chat_completion.choices[0].message.content
    
def main(args = None):


    rclpy.init(args=args)
    action_client = InputSender()
    # user_input = input("Enter the text to be sent: ")
    # api_response = action_client.generate_text(user_input)
    # action_client.send_goal(api_response)
    # action_client.get_logger().info('Goal sent: {0}'.format(api_response))

    rclpy.spin(action_client)

if __name__ == '__main__':
    main()