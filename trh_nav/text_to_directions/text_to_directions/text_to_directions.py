import rclpy
import os
from openai import OpenAI
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import String
import time

class dirSender(Node):

    def __init__(self):
        super().__init__('dir_sender')
        self.subscription = self.create_subscription(
            String,
            'input_text',
            self.send_directions,
            10
        )
        self.publisher = self.create_publisher(
            String,
            'text_poses',
            10
        )
        self.prompt_history = [{"role": "system", "content": "You read text and output either 'table' or 'box' based on what location you think the input is directing you to."}]
        self.coord_table = {"box": "6.5,0", "table": "3,-0.5"}
    def send_directions(self, msg):
        text = msg.data
        self.get_logger().info("Text recieved: {0}".format(text))
        response = self.generate_text(text)
        self.get_logger().info("Recieved: {0}".format(response))
        coord = self.coord_table[response]
        self.publisher.publish(String(data=coord))
        self.get_logger().info("Sending: ({0})".format(coord))
    
    def generate_text(self, text):
        self.prompt_history.append({"role": "user", "content": text})
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        chat_completion = client.chat.completions.create(
            messages=self.prompt_history,
            model='gpt-4',
        )
        response = chat_completion.choices[0].message.content
        self.prompt_history.append({"role": "assistant", "content": chat_completion.choices[0].message.content})
        return response
    
    
def main(args = None):
    rclpy.init(args=args)
    sender = dirSender()
    rclpy.spin(sender)

if __name__ == '__main__':
    main()