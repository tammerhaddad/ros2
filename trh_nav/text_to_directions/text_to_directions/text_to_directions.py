import rclpy
import os
from openai import OpenAI
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import String
import json

class dirSender(Node):

    def __init__(self):
        super().__init__('dir_sender')
        self.subscription = self.create_subscription(
            String,
            'input_text',
            self.send_directions,
            10
        )
        self.sendPose = self.create_publisher(
            String,
            'text_poses',
            10
        )
        self.sendLoc = self.create_publisher(
            String,
            'locations',
            10
        )
        self.states = self.create_subscription(
            String,
            'states',
            self.state_redirection,
            10
        )
        self.autoTTS = self.create_publisher(
            String,
            'TTS_text',
            10
        )
        self.prompt_history = [{"role": "system", "content": "You are a navigational robot named Stretch. You will be guiding users to locations in a room, as well as conversing with them."}]
        self.coord_table = {"box": "6.5,0", "table": "1.2,0.5", "home": "0,0"}

    def state_redirection(self, msg):
        self.get_logger().info("State recieved: {0}".format(msg.data))
        state = msg.data.split(".")
        match state[0]:
            case "nav":
                match state[1]:
                    case "start":
                        self.autoTTS.publish(String(data="Navigating to {0}.".format(state[2])))
                        self.prompt_history = [{"role": "system", "content": "You have started navigating to {0}.".format(state[2])}]
                    case "success":
                        self.autoTTS.publish(String(data="You have arrived at {0}.".format(state[2])))
                        self.prompt_history = [{"role": "system", "content": "You have arrived at {0}.".format(state[2])}]
                    case "fail":
                        self.autoTTS.publish(String(data="Navigation to {0} has failed.".format(state[2])))
                        self.prompt_history = [{"role": "system", "content": "Navigation to {0} has failed.".format(state[2])}]
                    case _:
                        self.get_logger().info("Invalid state: {0}".format(msg.data))
            case "talk":
                pass
            case _:
                self.get_logger().info("Invalid state: {0}".format(msg.data))   
         
    def send_directions(self, msg):
        text = msg.data
        self.get_logger().info("Text recieved: {0}".format(text))
        response = self.generate_text(text)
        self.get_logger().info("Recieved: {0}".format(response))
        self.sendLoc.publish(String(data=response))
        if response not in self.coord_table.keys():
            self.autoTTS.publish(String(data=response))
            self.get_logger().info("Responding to user: {0}".format(response))
        else:
            coord = self.coord_table[response]
            self.sendPose.publish(String(data=coord))
            self.get_logger().info("Sending: ({0})".format(coord))
    
    def generate_text(self, text):
        self.prompt_history.append({"role": "user", "content": text})

        functions = [
            {
                "type": "function",
                "function": {
                    "name": "process_response",
                    "description": "Generate a JSON object for a robot response",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "response": {"type": "string", "description": "What the robot should say to the user"},
                            "destination": {"type": "string", "description": "Where the user said the robot should go. Options: 'table', 'box', 'home'"},
                        },
                        "required": ["response", "destination"]
                    }
                }
            }
        ]

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        chat_completion = client.chat.completions.create(
            messages=self.prompt_history,
            model='gpt-4',
            tools=functions,
            tool_choice="auto"
        )
        response_message = chat_completion.choices[0].message
        response = {}
        if response_message.tool_calls:
            function_args = response_message.tool_calls[0].function.arguments
            response = json.loads(function_args)
        self.prompt_history.append({"role": "assistant", "content": response["response"]})
        if response["destination"] in ["table", "box", "home"]:
            return response["destination"]
        return response

def main(args = None):
    rclpy.init(args=args)
    sender = dirSender()
    rclpy.spin(sender)

if __name__ == '__main__':
    main()