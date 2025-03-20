import rclpy
import os
from openai import OpenAI
from rclpy.action import ActionServer
from rclpy.node import Node
from std_msgs.msg import String
from trh_msgs.action import StringAction
from trh_msgs.action import Directions
from trh_msgs.action import SendCoord
from trh_msgs.msg import Coord
from rclpy.action import ActionClient
from trh_msgs.action import GPTAction
from trh_msgs.action import GPTHistory

import json

class dirSender(Node):

    def __init__(self):
        super().__init__('dir_sender')
        self._action_server = ActionServer(
            self,
            GPTAction,
            'dir_server',
            self.execute_callback)
        self.gpt_server = ActionServer(
            self,
            StringAction,
            'gpt_server',
            self.gpt_callback)
        self.add_dir_client = ActionClient(
            self,
            SendCoord,
            "add_coord"
            )
        self.nav_client = ActionClient(
            self,
            Directions,
            "nav_action"
        )
        self.history_server = ActionServer(
            self,
            GPTHistory,
            "gpt_history",
            self.history_callback
        )
        
        self.prompt_history = [{"role": "system", "content": "You are a navigational assistant named Stretch. You will be guiding users to locations in a room, as well as conversing with them."}]
        self.coord_table = {"box": "4,1", "table": "1.2,0.5", "home": "0,0"}
        self.get_logger().info('Init done.')
    
    def history_callback(self, goal_handle):
        # pretty simply add 
        result = GPTHistory.Result()
        role = goal_handle.request.role
        text = goal_handle.request.text
        self.prompt_history.append({"role": role, "content": text})
        result.success = True
        goal_handle.succeed()
        return result

    def execute_callback(self, goal_handle):
        self.get_logger().info('Executing goal...')
        result = GPTAction.Result()
        feedback = GPTAction.Feedback()
        text = goal_handle.request.user_input
        response = self.generate_text(text)

        self.feedback_helper(feedback, goal_handle, "Response: {0}".format(response))
        if response.get("destination") not in self.coord_table.keys():
            result.goal = "other"
            self.feedback_helper(feedback, goal_handle, "Responding to user: {0}".format(response.get("response")))
        else:
            result.goal = response.get("destination")

        result.response = response.get("response")
        goal_handle.succeed()
        return result
    
    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Coord not added :(')
            return

        self.get_logger().info('Coord added :)')

        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        
        result = future.result().result
        # rclpy.shutdown()

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback.coord_list
        # self.get_logger().info('Feedback: {0}'.format(feedback.feedback))
        
    def feedback_helper(self, feedback, goal_handle, text):
        feedback.feedback = "Text recieved: {0}".format(text)
        goal_handle.publish_feedback(feedback)
         
    def send_directions(self, msg):
        text = msg.data
        response = self.generate_text(text)
        
        if response.get("destination") in self.coord_table.keys():
            if response.get("destination") == "other":
                self.auto_tts.publish(String(data="Im sorry, but you instructed me to go to somewhere not in my map, please try again"))
                return
            coord = self.coord_table[response.get("destination")]
            # self.sendPose.publish(String(data=coord))
            coord = coord.split(",")
            coord_to_send = SendCoord.Goal()
            coord_to_send.x = float(coord[0])
            coord_to_send.y = float(coord[1])
            self.get_logger().info(f"Sending: ({coord_to_send.x}, {coord_to_send.y})")
            self.add_dir_client.wait_for_server()
            self._send_goal_future = self.add_dir_client.send_goal_async(
                coord_to_send, feedback_callback=self.feedback_callback)
            self._send_goal_future.add_done_callback(self.goal_response_callback)
            point = Directions.Goal()
            point.points = 1
            self.get_logger().info(f'Going to {point.points} points.')
            self._send_goal_future = self.nav_client.send_goal_async(point)
            self._send_goal_future.add_done_callback(self.nav_goal_response)

        res = response.get("response")
        self.get_logger().info("Text recieved: {0}".format(text))
        response = self.generate_text(text)
        
        # if response.get("response") == String:
        self.get_logger().info("Speaking: {0}".format(response.get("response")))
        self.auto_tts.publish(String(data=response.get("response")))
        # if response.get("destination") == String:
        # if response.get("destination") in ["table", "box", "home"]:
        #     self.sendLoc.publish(String(data=response.get("destination")))
        #     coord = self.coord_table[response.get("destination")]
        #     self.sendPose.publish(String(data=coord))
        #     self.get_logger().info("Sending: ({0})".format(coord))

    def nav_goal_response(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Navigation goal rejected :(')
            return

        self.get_logger().info('Navigation goal accepted :)')

        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)
    
    def generate_text(self, text):
        self.prompt_history.append({"role": "user", "content": text})

        functions = [
            {
                "type": "function",
                "function": {
                    "name": "process_response",
                    "description": "Generate a JSON object for an assistants response",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "response": {"type": "string", "description": "What the assistant should say to the user"},
                            "destination": {"type": "string", "description": "Where the user said the assistant should go. Options: 'table', 'box', 'home'. If the user is not explicitly asking for directions or telling you to go somewhere, just respond with 'other'. If there is a word that sounds like one of the locations, like 'boss' (which sounds like box), use the approximation in case the user misspoke. Only do this if the words have similar letters, if someone says 'aquarium' then just say other"},
                        },
                        "required": ["response", "destination"]
                    }
                }
            }
        ]

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        chat_completion = client.chat.completions.create(
            messages=self.prompt_history,
            model='gpt-4o-mini',
            tools=functions,
            tool_choice="required"
        )
        response_message = chat_completion.choices[0].message
        response = {}
        if response_message.tool_calls:
            function_args = response_message.tool_calls[0].function.arguments
            response = json.loads(function_args)
        self.prompt_history.append({"role": "assistant", "content": response.get("response")})
        return response
    
    def gpt_callback(self, goal_handle):
        result = StringAction.Result()
        text = goal_handle.request.strrequest
        response = self.generate_simple_text(text)
        result.strresult = response
        goal_handle.succeed()
        return result
   
    def generate_simple_text(self, text):
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": text}],
            model='gpt-4o-mini',
        )
        res = chat_completion.choices[0].message.content
        self.get_logger().info(f"Simple GPT Response: {str(res)}")
        return res


def main(args = None):
    rclpy.init(args=args)
    sender = dirSender()
    rclpy.spin(sender)

if __name__ == '__main__':
    main()