import rclpy
import os
from openai import OpenAI
from rclpy.action import ActionServer
from rclpy.node import Node
from std_msgs.msg import String
from trh_msgs.action import StringAction
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
        self.auto_tts = self.create_publisher(
            String,
            'TTS_text',
            10
        )
        self._action_server = ActionServer(
            self,
            StringAction,
            'dir_server',
            self.execute_callback)
        
        self.prompt_history = [{"role": "system", "content": "You are a navigational assistant named Stretch. You will be guiding users to locations in a room, as well as conversing with them."}]
        self.coord_table = {"box": "6.5,0", "table": "1.2,0.5", "home": "0,0"}
        self.get_logger().info('Init done.')

    def execute_callback(self, goal_handle):
        self.get_logger().info('Executing goal...')
        result = StringAction.Result()
        feedback = StringAction.Feedback()
        text = goal_handle.request.strrequest
        self.feedback_helper(feedback, goal_handle, "Text recieved: {0}".format(text))
        response = self.generate_text(text)
        self.get_logger().info('Response checker: {0}'.format(response))
        self.feedback_helper(feedback, goal_handle, "Response: {0}".format(response))
        
        self.sendLoc.publish(String(data=response))
        if response not in self.coord_table.keys():
            self.auto_tts.publish(String(data=response))
            self.feedback_helper(feedback, goal_handle, "Responding to user: {0}".format(response))
        else:
            coord = self.coord_table[response]
            self.sendPose.publish(String(data=coord))
            self.feedback_helper(feedback, goal_handle, "Sending: ({0})".format(coord))

        result.strresult = response
        goal_handle.succeed()
        return result
    
    def feedback_helper(self, feedback, goal_handle, text):
        feedback.strfeedback = "Text recieved: {0}".format(text)
        goal_handle.publish_feedback(feedback)

    def state_redirection(self, msg):
        self.get_logger().info("State recieved: {0}".format(msg.data))
        state = msg.data.split(".")
        match state[0]:
            case "nav":
                match state[1]:
                    case "start":
                        self.auto_tts.publish(String(data="Navigating to {0}.".format(state[2])))
                        self.prompt_history.append({"role": "system", "content": "You have started navigating to {0}.".format(state[2])})
                    case "success":
                        self.auto_tts.publish(String(data="You have arrived at {0}.".format(state[2])))
                        self.prompt_history.append({"role": "system", "content": "You have arrived at {0}.".format(state[2])})
                    case "fail":
                        self.auto_tts.publish(String(data="Navigation to {0} has failed.".format(state[2])))
                        self.prompt_history.append({"role": "system", "content": "Navigation to {0} has failed.".format(state[2])})
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
            self.auto_tts.publish(String(data=response))
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
                    "description": "Generate a JSON object for a response",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "response": {"type": "string", "description": "What you should say to the user"},
                            "destination": {"type": "string", "description": "Where the user said you should go. Options: 'table', 'box', 'home'. if No destination is specified, respond 'other'"},
                        },
                        "required": ["response", "destination"]
                    }
                }
            }
        ]

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.get_logger().info("Prompt history: {0}".format(self.prompt_history))
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
        if response is not None and "response" in response.keys():
            # self.get_logger().info(response)
            self.prompt_history.append({"role": "assistant", "content": str(response["response"])})
            if response["destination"] in ["table", "box", "home"]:
                return response["destination"]
            return response
        else: 
            self.get_logger().info("Invalid response: {0}".format(response))
            res = "I'm sorry, I don't understand. Could you please rephrase that?"
            self.prompt_history.append({"role": "assistant", "content": str(res)})
            return res

def main(args = None):
    rclpy.init(args=args)
    sender = dirSender()
    rclpy.spin(sender)

if __name__ == '__main__':
    main()