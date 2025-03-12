import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from trh_msgs.action import StringAction
from trh_msgs.action import Directions
from trh_msgs.action import SendCoord
from trh_msgs.action import ListReq
from trh_msgs.msg import Coord
from trh_msgs.msg import Num
from std_msgs.msg import String
import threading
from visualization_msgs.msg import MarkerArray
from datetime import datetime

class NavHub(Node):

    def __init__(self):
        super().__init__('nav_hub')
        self.tts_client = ActionClient(self, StringAction, 'TTS_action')
        self.toggle_listen_client = ActionClient(self, Num, 'listen_toggle') # not used
        self.dir_client = ActionClient(self, SendCoord, 'dir_server')
        self.nav_client = ActionClient(self, Directions, 'nav_action')
        self.coord_client = ActionClient(self, SendCoord, "add_coord")
        self.stt_client = ActionClient(self, StringAction, 'get_audio')
        self.rob_client = ActionClient(self, StringAction, 'stretch_control') #'cam,0.3,0'
        self.face_sub = self.create_subscription(MarkerArray, '/faces/marker_array', self.face_callback, 10)

        # possible locations, and their coordinates
        self.coord_table = {"box": "4,1", "table": "1.2,0.5", "home": "0,0"}
        self.latest_face = []

    # Move Camera
    def cam_control(self, tilt, pan):
        goal_msg = StringAction.Goal()
        self.get_logger().info('sending cam goal...')
        goal_msg.strrequest = 'cam,{0},{1}'.format(tilt, pan)
        future = self.rob_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)
        goal_future = future.result().get_result_async()
        rclpy.spin_until_future_complete(self, goal_future)
        self.get_logger().info('Cam goal completed')
        if goal_future.result().strresult is not None and goal_future.result().strresult != "":
            return True
        else:
            self.get_logger().info('Cam goal failed')
            return None
    
    # Speak the imported text
    def tts_call(self, text):
        goal_msg = StringAction.Goal()
        self.get_logger().info('Sending TTS goal...')
        goal_msg.strrequest = text
        future = self.tts_client.send_goal_async(goal_msg)
        # wait for the send_goal future to be done
        rclpy.spin_until_future_complete(self, future)
        # now we setup the loop for the results
        goal_future = future.result().get_result_async()
        # loop goal future
        rclpy.spin_until_future_complete(self, goal_future)
        self.get_logger().info('TTS goal completed')
        if goal_future.result().strresult is not None and goal_future.result().strresult != "":
            return True
        else:
            self.get_logger().info('TTS goal failed')
            return None

    # Request audio, this will pause the code until the audio is recieved
    def stt_call(self):
        goal_msg = StringAction.Goal()
        self.get_logger().info('sending STT goal...')
        goal_msg.strrequest = "get audio" # not used, i need to make a new action for this
        future = self.stt_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)
        goal_future = future.result().get_result_async()
        user_input = goal_future.result().strresult
        rclpy.spin_until_future_complete(self, goal_future)
        self.get_logger().info('STT goal completed, user said: {0}'.format(user_input))
        if user_input is not None and user_input != "":
            return user_input
        else:
            self.get_logger().info('STT goal failed')
            return None

    # Request GPT to generate a response, also returns the goal location if there is one
    def gpt_call(self, user_input):
        goal_msg = StringAction.Goal()
        self.get_logger().info('sending GPT goal...')
        goal_msg.strrequest = user_input
        future = self.dir_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)
        goal_future = future.result().get_result_async()
        gpt_response = goal_future.result().strresult
        rclpy.spin_until_future_complete(self, goal_future)
        self.get_logger().info('GPT goal completed, GPT said: {0}'.format(gpt_response))
        if gpt_response is not None and gpt_response != "":
            return [gpt_response.response, gpt_response.goal]
        else:
            self.get_logger().info('GPT goal failed')
            return None

    # add a coordinate to the list
    def add_coord_call(self, goal_text):
        coord = self.coord_table[goal_text]
        coord = coord.split(",")
        coord_to_send = SendCoord.Goal()
        coord_to_send.x = float(coord[0])
        coord_to_send.y = float(coord[1])
        self.coord_client.wait_for_server()
        self._send_goal_future = self.coord_client.send_goal_async(
            coord_to_send, feedback_callback=self.feedback_callback)
        self._send_goal_future.add_done_callback(self.add_coord_response_callback)

    # feedback callback for add_coord_call
    def add_coord_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Coord not added :(')
            return
        self.get_logger().info('Coord added :)')
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    # get result callback for add_coord_call
    def nav_call(self, points):
        goal_msg = Directions.Goal()
        goal_msg.points = points
        self.get_logger().info('Sending nav goal...')
        future = self.nav_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)
        goal_future = future.result().get_result_async()
        return goal_future
    
    # feedback callback for nav_call
    def nav_future(self, goal_future):
        rclpy.spin_until_future_complete(self, goal_future, timeout_sec=1)
        self.get_logger().info('Nav goal completed')
        # this is gonna come into conflict at some point i gotta handle it in main
        self.tts_call("I have arrived at the location, is there anything else I can help you with?.")
        if goal_future.result().strresult is not None and goal_future.result().strresult != "":
            return True
        else:
            self.get_logger().info('Nav goal failed')
            return None

    # adds faces to the latest_face variable
    def face_callback(self, msg):
        self.latest_face = msg.markers
    
    def wait_for_interactor(self, total_time = 1, timeout = -1):

        def face_close_enough(faces):
            # self.get_logger().info('face close eno0ugh')
            return len(faces) > 0

        # move head up
        started = False
        start_time = datetime.now()
        while True and (timeout == -1 or (datetime.now() - start_time).total_seconds() < timeout):
            rclpy.spin_once(self)
            # self.get_logger().info(f'{face_close_enough(copy.deepcopy(self.latest_face))}')
            # self.get_logger().info(f'{(self.latest_face)}')
            if face_close_enough(copy.deepcopy(self.latest_face)):
                # self.get_logger().info('we;re gere')
                if not started:
                    # self.get_logger().info('started face ckkse e3ogyug')
                    started = True
                    interact_start_time = datetime.now()
                else:
                    # self.get_logger().info(' not started face close ebnough')
                    if (datetime.now() - interact_start_time).total_seconds() > total_time:
                        return True
        return False
    def run(self):
        # start
        # idle:
        # check for person:
        # while (person):
        # - greet
        # - get response
        # - respond with tts
        # - if nav
        #   - request nav server

        # idle
        self.get_logger().info('Startup done.')
        person = False
        # going to be an outside loop
        self.cam_control(0.3, 0)

        while person:
            # greet
            self.tts_call("Hello, how can I help you?")
            self.cam_control(0.3, 0)
            # get user input
            person_response = self.stt_call()
            # need to broaden this to check other ways to say goodbye, maybe with the gpt call?
            # i could add a "goodbye" location that the model could check for
            if person_response is "Goodbye.":
                self.tts_call("Goodbye! Let me know if you need anything else.")
                break
            # look down while thiking
            self.cam_control(-0.3, 0)
            gpt_response = self.gpt_call(person_response)
            # look back up to talk to them, we are assuming theyll stay quiet for this
            self.cam_control(0.3, 0)
            self.tts_call(gpt_response[0])
            # after responding, check if they want to go somewhere and then go there
            if gpt_response[1] is not None:
                # i want to add this to the gpt responses to make it more natural
                # need to add another server
                if gpt_response[1] == "other":
                    self.tts_call("I'm sorry, I don't have that location on my map. Please try again.")
                else:
                    # add coord with coord_client
                    self.add_coord_call(gpt_response[1])
                    # say "go" with nav_client
                    # do i have to thread this??? ---------
                    nav_future = self.nav_call(1)
                    while not rclpy.spin_until_finished(nav_future, timeout_sec=1):
                        # add timeout
                        person_response = self.stt_call()
                        # need to broaden this to check other ways to say goodbye, maybe with the gpt call?
                        # i could add a "goodbye" location that the model could check for
                        if person_response is "Goodbye.":
                            self.tts_call("Goodbye! Let me know if you need anything else.")
                            break
                        self.cam_control(-0.3, 0)
                        gpt_response = self.gpt_call(person_response)
                        self.cam_control(0.3, 0)
                        self.tts_call(gpt_response[0])
                    
                    self.get_logger().info('Nav goal completed')
                    # this is gonna come into conflict at some point i gotta handle it in main
                    self.tts_call("I have arrived at the location, is there anything else I can help you with?.")
                

        # CALL TO FACE DETECTION TBD (gotta pull from robot)
        # also want to make a seperate server that is constantly monitoring
        # maybe publish sorta like the speaking one? and i could just like the subscription
        # with a true false statement

def main(args=None):
    rclpy.init(args=args)

    node = NavHub()

    executor = rclpy.executors.MultiThreadedExecutor(num_threads=10)
    executor.add_node(node)
    # executor.add_node(hello_node)
    executor_thread = threading.Thread(target=executor.spin, daemon=True)
    executor_thread.start()

    node.run()


if __name__ == '__main__':
    main()