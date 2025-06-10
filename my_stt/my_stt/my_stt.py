import time
import numpy as np
import whisper
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from audio_common_msgs.msg import AudioStamped
from std_msgs.msg import String
from rclpy.action import ActionServer
from trh_msgs.action import Numba
from trh_msgs.action import StringAction
from trh_msgs.action import BlankToString
from threading import Event
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

class SpeechToText(Node):

    def __init__(self):
        super().__init__('speech_to_text')

        # parameters
        self.declare_parameter('silence_duration', 2)  # seconds
        self.declare_parameter('calibration_duration', 3)  # seconds
        self.declare_parameter('interpreter', 'small')  # https://github.com/openai/whisper for info about model sizes, default is small

        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,  # Ensure reliability matches with the publisher
            depth=10
        )
        # subscribe to audio
        self.subscription = self.create_subscription(
            AudioStamped,
            'input_audio',
            self.listener_callback,
            qos_profile)
        # toggle listening
        self.toggle_server = ActionServer(self, Numba, 'listen_toggle', self.server_toggle_callback)
        # obsolete, but still can be used, publishes all input text to a topic (not used by default, uncomment line 203)
        self.input_text = self.create_publisher(String, 'input_text', 10)
        # also obsolete, for debugging
        self.vol_pub = self.create_publisher(String, 'volume', 10)

        # init this for threading the action call with when audio gets processed
        self.action_done_event = Event()
        self.callback_group = ReentrantCallbackGroup()
        # audio request server
        self.audio_server = ActionServer(
            self,
            BlankToString, 'get_audio',
            self.get_audio_callback,
            callback_group=self.callback_group)
        
        # accumulate audio data
        self.accumulated_data = bytearray()
        self.is_accumulating = False
        # starts at -1 for calibration, then is the limit for when audio starts recording
        self.volume_threshold = -1
        self.sample_rate = 16000
        self.silence_start_time = None
        self.node_start_time = time.time()
        # used for taking average volume
        self.calibration_volumes = []
        # Audio will begin processing after 1 second of no speech.
        self.silence_duration = self.get_parameter('silence_duration').get_parameter_value().integer_value
        # Audio will calibrate for 3 seconds to calibrate background noise level
        self.calibration_duration = self.get_parameter('calibration_duration').get_parameter_value().integer_value
        # Load the model, currently small, but can be changed to base if need faster processing
        self.model = whisper.load_model(self.get_parameter('interpreter').get_parameter_value().string_value)
        # starts out true, so that it calibrates on startup, but is by default False, so it doesn't pick up tts or random noise
        self.listening = True
        # not needed except for the most recent, but it seems nice to have
        self.text_history = []

        self.get_logger().info('\nInit done.\n')

    # action server to get audio and return text
    def get_audio_callback(self, goal_handle):
        self.listening = True
        self.get_logger().info('Getting audio...')
        # clear any events, so i dont request the same audio twice
        self.action_done_event.clear()
        # set up the result
        result = BlankToString.Result()
        result.result = "Audio received"
        # wait in a thread for the audio to be recorded and processed
        self.action_done_event.wait()
        # the text is added when done processing, so just fetch the most recent.
        result.result = self.text_history[-1]
        goal_handle.succeed()
        # Stop listening because the request is over.
        self.listening = False
        return result
    
    # simple action server to toggle listening on and off
    def server_toggle_callback(self, goal_handle):
        self.get_logger().info('Toggling listening...')
        if goal_handle.request.numrequest == 0:
            self.get_logger().info('Listening on.')
            self.listening = True
        elif goal_handle.request.numrequest == 1:
            self.get_logger().info('Listening off.')
            self.listening = False
        else:
            self.get_logger().info('Invalid request.')
        goal_handle.succeed()

    #this is always running, because it is subscribed to the speakers of the device
    def listener_callback(self, audio: AudioStamped):

        # read audio data
        audio_data = np.frombuffer(audio.audio.audio_data.int16_data, dtype=np.int16)
        # calculate volume, but only if there is audio data, then publish to a topic for viewing/debugging
        volume = np.linalg.norm(audio_data) / len(audio_data) if len(audio_data) > 0 else 0
        self.vol_pub.publish(String(data=f'Vol: {volume}'))
        
        # this only happens once, at startup
        if self.volume_threshold == -1:
            # set the background noise
            self.set_background_noise_level(volume)
            # then stop listening until a request is made
            self.listening = False
            return
        
        # if we aren't listening, we just return, nothing happens
        if not self.listening:
            return
        
        # if the volume goes above the threshold, start accumulating audio data, this happens once, until we are accumulating
        if volume > self.volume_threshold and not self.is_accumulating:
            # and start accumulating
            self.is_accumulating = True
            self.silence_start_time = None
        
        # if recording
        if self.is_accumulating:
            # store the data
            self.accumulated_data.extend(audio_data)
            # save the start time
            if self.silence_start_time is None:
                self.silence_start_time = time.time()
            elif time.time() - self.silence_start_time >= self.silence_duration:
                # if we have been silent for the duration, stop accumulating, and process the audio
                self.is_accumulating = False
                # theres no real point in the listening = false here, as the program literally 
                # CANNOT, as it is processing, but its here just in case
                self.listening = False
                self.process_audio_chunk(self.accumulated_data)
                # reset the data
                self.accumulated_data = bytearray()
                self.silence_start_time = None
    
    def set_background_noise_level(self, volume):
        if self.silence_start_time is None:
            # start calibration
            self.get_logger().info('Calibrating... (shut up)')
            self.silence_start_time = time.time()
            self.is_accumulating = True
        elif time.time() - self.silence_start_time >= self.calibration_duration:
            # get the highest volume, which should be 'silence' and then double it
            # we add 3 because in the case where there is a noise cancellation in the mic (like my laptop),
            # the max volume will be below 1, and so we need to add a little bit to make sure it doesn't pick up random noise
            max_vol = np.max(self.calibration_volumes)
            self.volume_threshold = max_vol*2 + 3
            self.accumulated_data = bytearray()
            self.silence_start_time = None
            self.is_accumulating = False
            self.get_logger().info(f"Calibrated. Volume threshold: {self.volume_threshold}")

        
        if self.is_accumulating:
            # we just accumulate the volumes, not the acutal sound.
            self.calibration_volumes.append(volume)
        
    def process_audio_chunk(self, audio_chunk):
        # we process the audio
        audio_data = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
        # then feed it into the model (by default whisper)
        result = self.model.transcribe(audio_data, fp16=False, language="en")
        # then we get the text from the result
        text = result['text']
        self.get_logger().info(f'Recognized text: {text}')
        if len(text) > 0:
            # this can be uncommented to publish the text to a topic
            # if you want it to happen automatically without requests, 
            # simply change the self.listening to True after processing and at init
            # self.publisher.publish(String(data=text))
            self.text_history.append(text)
            # we tell the action server that we are done processing, so it can return the text
            self.action_done_event.set()
        else: 
            # sometimes the model doesn't recognize anything, and outputs ""
            self.get_logger().info('No text recognized, not publishing')
            # keep listening
            self.listening = True

def main(args=None):
    rclpy.init(args=args)
    stt = SpeechToText()
    executor = MultiThreadedExecutor()
    rclpy.spin(stt, executor)

if __name__ == '__main__':
    main()
