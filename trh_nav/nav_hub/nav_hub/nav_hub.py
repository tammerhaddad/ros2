import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from trh_msgs.action import StringAction
from trh_msgs.action import Directions
from trh_msgs.action import SendCoord
from trh_msgs.action import GPTAction
from trh_msgs.action import BlankToString
from trh_msgs.action import GPTHistory
from trh_msgs.action import StringToBool
import threading
from visualization_msgs.msg import MarkerArray
from datetime import datetime
import copy
import time

class NavHub(Node):

    def __init__(self):
        super().__init__('nav_hub')
        # THIS LINE SEG FAULTS????
        # self.toggle_listen_client = ActionClient(self, Num, 'listen_toggle') # not used

        # outdated, now useing self made tts
        # self.tts_client = ActionClient(self, TTS, 'say')

        # initialize the clients
        self.tts_client = ActionClient(self, StringToBool, 'trh_tts')
        self.dir_client = ActionClient(self, GPTAction, 'dir_server')
        self.nav_client = ActionClient(self, Directions, 'nav_action')
        self.coord_client = ActionClient(self, SendCoord, "add_coord")
        self.stt_client = ActionClient(self, BlankToString, 'get_audio')
        self.rob_client = ActionClient(self, StringAction, 'stretch_control') #'cam,0.3,0'
        self.gpt_history_client = ActionClient(self, GPTHistory, 'gpt_history')
        self.face_sub = self.create_subscription(MarkerArray, '/faces/marker_array', self.face_callback, 10)
        self.gpt_client = ActionClient(self, StringAction, 'gpt_server')

        # wait for the action servers to be available
        # i log which one we are waiting for so we can see which one isnt running yet
        self.get_logger().info("Waiting for: tts_client")
        self.tts_client.wait_for_server()
        self.get_logger().info("Waiting for: dir_client")
        self.dir_client.wait_for_server()
        self.get_logger().info("Waiting for: nav_client")
        self.nav_client.wait_for_server()
        self.get_logger().info("Waiting for: coord_client")
        self.coord_client.wait_for_server()
        self.get_logger().info("Waiting for: stt_client")
        self.stt_client.wait_for_server()
        self.get_logger().info("Waiting for: rob_client")
        self.rob_client.wait_for_server()
        self.get_logger().info("Waiting for: gpt_client")
        self.gpt_client.wait_for_server()
        self.get_logger().info("Waiting for: history_client")
        self.gpt_history_client.wait_for_server()

        # possible locations, and their coordinates
        # self.coord_table = {"box": "4,1", "table": "1.2,0.5", "home": "0,0"} # 
        # self.coord_table = {"chair": "1,-1"}
        self.coord_table = {"elevator": "2,-10", "exit": "-7,2", "lab": "2, -20", "home": "0,0"}
        self.latest_face = []
        self.start_time = datetime.now()

    def history_call(self, role, text):
        # goal_msg = GPTHistory.Goal()
        # self.get_logger().info('Adding input to GPT History...')
        # goal_msg.role = role
        # goal_msg.text = text
        # future = self.gpt_history_client.send_goal_async(goal_msg)
        # rclpy.spin_until_future_complete(self, future)
        # goal_future = future.result().get_result_async()
        # rclpy.spin_until_future_complete(self, goal_future)
        # res = goal_future.result().result.success
        # if not res:
        #     self.get_logger().info("GPT history not added")
        res = True
        return res

    def gpt_call(self, text):
        goal_msg = StringAction.Goal()  
        self.get_logger().info('sending simple GPT goal...')
        goal_msg.strrequest = text
        future = self.gpt_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)
        goal_future = future.result().get_result_async()
        rclpy.spin_until_future_complete(self, goal_future)
        gpt_response = goal_future.result().result.strresult
        self.get_logger().info('GPT goal completed, GPT said: {0}'.format(gpt_response))
        return gpt_response

    # Move Camera
    def cam_control(self, tilt, pan):
        goal_msg = StringAction.Goal()
        self.get_logger().info('sending cam goal..')
        goal_msg.strrequest = 'control,cam,{0},{1}'.format(tilt, pan)
        self.get_logger().info(goal_msg.strrequest)
        future = self.rob_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)
        self.get_logger().info("cam goal recieved")
        goal_future = future.result().get_result_async()
        rclpy.spin_until_future_complete(self, goal_future)
    
    # Speak the imported text
    def tts_call(self, text):
        goal_msg = StringToBool.Goal()
        self.get_logger().info('Sending TTS goal...')
        goal_msg.request = text
        future = self.tts_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)
        goal_future = future.result().get_result_async()
        while not goal_future.done():
            rclpy.spin_until_future_complete(self, goal_future, timeout_sec=0.5)
        self.get_logger().info('TTS goal completed')

    # Request audio, this will pause the code until the audio is recieved
    def stt_call(self):
        goal_msg = BlankToString.Goal()
        self.get_logger().info('sending STT goal...')
        future = self.stt_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)
        goal_future = future.result().get_result_async()
        rclpy.spin_until_future_complete(self, goal_future, timeout_sec=30.0)
        if not goal_future.done():
            self.get_logger().info('STT goal timed out')
            return "UserTimedOut404"
        user_input = goal_future.result().result.result
        self.get_logger().info('STT goal completed, user said: {0}'.format(user_input))
        self.get_logger().info(f"User said: {user_input}")
        return user_input
    
    # this is the first half of the stt_call, simply sending the request and returning a future if the goal was accepted
    def stt_listen(self):
        goal_msg = BlankToString.Goal()
        self.get_logger().info('sending STT goal...')
        future = self.stt_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)
        goal_future = future.result().get_result_async()
        self.get_logger().info('Nav Goal Sent successfully')
        return goal_future

    # Request GPT to generate a response, also returns the goal location if there is one
    def nav_gpt_call(self, user_input):
        goal_msg = GPTAction.Goal()
        self.get_logger().info('Processing user goal...')
        goal_msg.user_input = user_input
        future = self.dir_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)
        goal_future = future.result().get_result_async()
        rclpy.spin_until_future_complete(self, goal_future)
        gpt_response = goal_future.result().result
        self.get_logger().info('Goal processed, Response is: {0}'.format(gpt_response))
        return [gpt_response.response, gpt_response.goal]

    # add a coordinate to the list
    def add_coord_call(self, goal_text):
        coord = self.coord_table[goal_text]
        coord = coord.split(",")
        coord_to_send = SendCoord.Goal()
        coord_to_send.x = float(coord[0])
        coord_to_send.y = float(coord[1])
        self.get_logger().info(f'Adding ({coord_to_send.x},{coord_to_send.y}) to queue')
        future = self.coord_client.send_goal_async(coord_to_send)
        rclpy.spin_until_future_complete(self, future)
        goal_future = future.result().get_result_async()
        rclpy.spin_until_future_complete(self, goal_future)
        # gpt_response = goal_future.result().result
        self.get_logger().info('Coord has been added.')
        return True

    # get result callback for add_coord_call
    def nav_send_goal(self, points):
        goal_msg = Directions.Goal()
        goal_msg.points = points
        self.get_logger().info('Sending nav goal...')
        future = self.nav_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)
        goal_future = future.result().get_result_async()
        self.get_logger().info('Nav Goal Sent successfully')
        return goal_future
    
    # adds faces to the latest_face variable
    def face_callback(self, msg):
        self.latest_face = msg.markers
    
    def wait_for_interactor(self, total_time = 1, timeout = -1):

        # if there are faces detected, return true
        def face_close_enough(faces):
            return len(faces) > 0

        started = False
        start_time = datetime.now()
        # we wait for the determined amount of time, then check if there are faces detected
        while True and (timeout == -1 or (datetime.now() - start_time).total_seconds() < timeout):
            rclpy.spin_once(self)
            if face_close_enough(copy.deepcopy(self.latest_face)):
                if not started:
                    started = True
                    interact_start_time = datetime.now()
                else:
                    if (datetime.now() - interact_start_time).total_seconds() > total_time:
                        return True
        return False


    def run(self):
        self.get_logger().info('Startup done.')
        running = True
        # setting up the gpt to be a robot
        self.history_call("system", "You are a navigational assistant named Stretch. You will be guiding users to locations in a room, as well as conversing with them.")
        while running:

            # initial cam position a bit above level
            self.cam_control(0.3, 0.0)
            while self.wait_for_interactor():
                # looks higher up when person detected
                self.cam_control(0.5, 0.0)
                self.tts_call("Hello, how can I help you?")
                self.history_call("assistant", "Hello, how can I help you?")
                interacting = True

                # this is so we can toggle interaction off even if the user is here
                while interacting:
                    self.get_logger().info("Continuing interaction")
                    # gets text
                    person_response = self.stt_call()
                    self.cam_control(0.3, 0.0)
                    # times out if the user doesn't respond
                    if person_response == "UserTimedOut404":
                        person_there = False
                        # just a sweep of the area
                        positions = [-1, -0.5, 0, 0.5, 1]
                        for i in positions:
                            self.cam_control(i, 0.0)
                            if self.wait_for_interactor(1, 1):
                                person_there = True
                                self.cam_control(0.5, 0.0)
                                break
                        # if they left, go home
                        if not person_there:
                            self.add_coord_call("home")
                            nav_future = self.nav_send_goal(1)
                            interacting = False
                            self.cam_control(0, 0.0)
                            self.tts_call("Goodbye! Let me know if you need anything else.")
                            self.history_call("assistant", "Goodbye! Let me know if you need anything else.")
                            break

                    # if the user says goodbye, go home
                    check_for_goodbye = self.gpt_call(
                        f"You are a navigational robot with the ability to go to the following locations: "
                        f"{self.coord_table.values()}. Does the following response indicate that the user is leaving? be very strict, only say yes if they say 'goodbye' 'cya' 'im leaving' or something similar"
                        f"Answer only y or n: {person_response}"
                    )
                    if check_for_goodbye == "y":
                        self.cam_control(0, 0.0)
                        self.tts_call("Goodbye! Let me know if you need anything else.")
                        self.history_call("assistant", "Goodbye! Let me know if you need anything else.")
                        time.sleep(5)
                        self.add_coord_call("home")
                        nav_future = self.nav_send_goal(1)
                        interacting = False
                        break

                    # otherwise, we process the response
                    gpt_response = self.nav_gpt_call(person_response)
                    self.cam_control(0.5, 0)
                    self.get_logger().info('GPT goal completed, GPT said: {0}'.format(gpt_response[0]))     
                    # speak out the gpts response
                    self.tts_call(gpt_response[0])
                    # if the user had a location in mind, we proceed with navigation
                    if gpt_response[1] is not None:
                        # obviously if the response is invalid, we ask them to repeat
                        if gpt_response[1] == "invalid":
                            # need to decide how to loop this
                            self.tts_call("I'm sorry, I don't have that location on my map. Please try again.")
                            self.history_call("assistant", "I'm sorry, I don't have that location on my map. Please try again.")
                        elif gpt_response[1] in self.coord_table.keys() or gpt_response[1] == "other":
                            if gpt_response[1] == "other":
                                break
                            self.add_coord_call(gpt_response[1])
                            self.cam_control(0, 0.0)
                            nav_future = self.nav_send_goal(1)
                            # not used yet, this is for speaking while driving                            
                            stt_future = self.stt_listen()
                            while not nav_future.done():
                                rclpy.spin_until_future_complete(self, nav_future, timeout_sec=1)
                                self.get_logger().info("Driving...")
                                # rclpy.spin_until_future_complete(self, stt_future, timeout_set=1)
                                # if stt_future.done():
                                #     user_input = stt_future.result().result.result
                                #     self.get_logger().info('STT goal completed, user said: {0}'.format(user_input))
                                #     gpt_response = self.nav_gpt_call(person_response)
                                #     break
                            # stt_future.cancel_goal_async()
                            # rclpy.spin_until_future_complete(self, stt_future)
                            
                            self.get_logger().info('Nav goal completed')
                            # self.tts_call("I have arrived at the location, is there anything else I can help you with?.")
                            # self.history_call("assistant", "I have arrived at the location, is there anything else I can help you with?.")
                        else: 
                            # not invalid but not a location, just a conversation
                            self.get_logger().info("Conversation detected")

        self.get_logger().info("code runs")

def main(args=None):
    rclpy.init(args=args)

    node = NavHub()
    executor = rclpy.executors.MultiThreadedExecutor(num_threads=10)
    executor.add_node(node)
    executor_thread = threading.Thread(target=executor.spin, daemon=True)
    executor_thread.start()
    node.run()

if __name__ == '__main__':
    main()