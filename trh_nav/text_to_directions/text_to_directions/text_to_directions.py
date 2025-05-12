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
# used for the function call, not entirely necessary
import json

class dirSender(Node):
    def __init__(self):
        super().__init__('dir_sender')

        # action that returns text and a goal
        self._action_server = ActionServer(
            self,
            GPTAction,
            'dir_server',
            self.execute_callback)
        # simple gpt server that is just text to text with no memory
        self.gpt_server = ActionServer(
            self,
            StringAction,
            'gpt_server',
            self.gpt_callback)
        # adds a coordinate to the queue
        self.add_dir_client = ActionClient(
            self,
            SendCoord,
            "add_coord"
            )
        # instructs robot to go to coord
        self.nav_client = ActionClient(
            self,
            Directions,
            "nav_action"
        )
        # adds a message to the history
        self.history_server = ActionServer(
            self,
            GPTHistory,
            "gpt_history",
            self.history_callback
        )
        # sets up the gpt to be a robot
        self.prompt_history = []
        # self.coord_table = {"box": "4,1", "table": "1.2,0.5", "home": "0,0"}
        # self.coord_table = {"chair": "-1,1"}
        self.coord_table = {"elevator": "2,-10", "exit": "-7,2", "lab": "2, -20", "home": "0,0"}
        self.get_logger().info('Init done.')
    
    # pretty simply add a prompt to the history, this can be from the user, gpt, even the system.
    def history_callback(self, goal_handle):
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
        # gets the text and generates a response
        text = goal_handle.request.user_input
        response = self.generate_text(text)
        self.feedback_helper(feedback, goal_handle, "Response: {0}".format(response))
        # split the destination and actual worded response up for easier reading on the other end
        result.goal = response.get("destination")
        result.response = response.get("response")
        goal_handle.succeed()
        return result
    
    # just checks if the coord is added or not
    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Coord not added :(')
            return

        self.get_logger().info('Coord added :)')

        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    # not used
    def get_result_callback(self, future):
        
        result = future.result().result
        # rclpy.shutdown()

    # not used
    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback.coord_list
        # self.get_logger().info('Feedback: {0}'.format(feedback.feedback))
        
    # logs the text that the gpt gave back
    def feedback_helper(self, feedback, goal_handle, text):
        feedback.feedback = "Text recieved: {0}".format(text)
        goal_handle.publish_feedback(feedback)
    
    # DEPRECATED CODE FROM WHEN THIS WAS A SUBSCRIBER
    def send_directions(self, msg):
        text = msg.data
        response = self.generate_text(text)

        # get the coordinates of the destination based on the text given in the message
        if response.get("destination") in self.coord_table.keys():
            if response.get("destination") == "other":
                self.auto_tts.publish(String(data="Im sorry, but you instructed me to go to somewhere not in my map, please try again"))
                return
            coord = self.coord_table[response.get("destination")]
            coord = coord.split(",")
            coord_to_send = SendCoord.Goal()
            coord_to_send.x = float(coord[0])
            coord_to_send.y = float(coord[1])
            self.get_logger().info(f"Sending: ({coord_to_send.x}, {coord_to_send.y})")
            # partially integrated with current methodologies, 
            # this used to just create a pose and send it to rviz
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
        # also making use of deprecated code that no longer exists
        self.get_logger().info("Speaking: {0}".format(response.get("response")))
        self.auto_tts.publish(String(data=response.get("response")))
        # if response.get("destination") == String:
        # if response.get("destination") in ["table", "box", "home"]:
        #     self.sendLoc.publish(String(data=response.get("destination")))
        #     coord = self.coord_table[response.get("destination")]
        #     self.sendPose.publish(String(data=coord))
        #     self.get_logger().info("Sending: ({0})".format(coord))

    # checks if the navigation goal was sent
    def nav_goal_response(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Navigation goal rejected :(')
            return

        self.get_logger().info('Navigation goal accepted :)')
 
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)
    
    # pretty simple text generation, along with the goal
    def generate_text(self, text):
        self.prompt_history.append({"role": "user", "content": text})

        # preset to be a robot that assists in navigation, will probably move this outside of this node soon
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
                            "destination": {"type": "string", "description": f"Where the user said the assistant should go. Options: {self.coord_table.keys()}. If the user is not explicitly asking for directions or telling you to go somewhere, just respond with 'other'. If there is a word that sounds like one of the locations, like 'boss' (which sounds like box), use the approximation in case the user misspoke. Only do this if the words have similar letters, if someone says 'aquarium' then just say other. if the user specifices a location that is not in the list, reply 'invalid'"},
                        },
                        "required": ["response", "destination"]
                    }
                }
            }
        ]
        
        # connects to openai and gets a response based on the prompt history
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        chat_completion = client.chat.completions.create(
            messages=self.prompt_history,
            model='gpt-4o-mini',
            tools=functions,
            tool_choice="required"
        )
        response_message = chat_completion.choices[0].message
        response = {}
        # we split the response based on the function, will move this out of the node along with the hardcoded function
        if response_message.tool_calls:
            function_args = response_message.tool_calls[0].function.arguments
            response = json.loads(function_args)
        self.prompt_history.append({"role": "assistant", "content": response.get("response")})
        return response
    
    # simple_gpt_callback function
    # just text to text
    def gpt_callback(self, goal_handle):
        result = StringAction.Result()
        text = goal_handle.request.strrequest
        response = self.generate_simple_text(text)
        result.strresult = response
        goal_handle.succeed()
        return result
    
    # could have put this in the above function but seemed better to keep seperate
    # just a simpler version of the generate_text function, purely text to text
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