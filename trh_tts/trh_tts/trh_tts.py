import time
from threading import Event

import rclpy
from rclpy.action import ActionServer
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
import subprocess
import pyaudio
from trh_msgs.action import StringToBool


class TrhTTS(Node):

    def __init__(self):
        super().__init__('trh_tts')
        self.tts_server = ActionServer(self, StringToBool, 'trh_tts', self.tts_callback)
        self.cancel_sound = ActionServer(self, StringToBool, 'trh_tts/cancel_sound', self.cancel_sound_callback)
        self.action_done_event = Event()
        self.festival_process = None
        self.p = None
        self.stream = None
        self.is_playing = False
        self.get_logger().info('Init Done.')

    def tts_callback(self, goal_handle):
        self.get_logger().info('Received text: %s' % goal_handle.request.request)
        result = StringToBool.Result()
        self.action_done_event = Event()
        self.tts_call(goal_handle.request.request)
        self.get_logger().info('Action completed successfully')
        self.action_done_event.wait()
        goal_handle.succeed()
        result.response = True
        return result

    def cancel_sound_callback(self, goal_handle):
        self.get_logger().info('Received cancel request')
        self.cancel_playback()
        goal_handle.succeed()
        result = StringToBool.Result()
        result.response = True
        return result

    def tts_call(self, text):
        festival_cmd = ['festival', '--tts']
        self.festival_process = subprocess.Popen(
            festival_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE
        )
        self.festival_process.stdin.write(text.encode('utf-8'))
        self.festival_process.stdin.close()
        self.p = pyaudio.PyAudio()
        self.stream = self.initialize_pyaudio_stream(self.p)
        self.play_audio_stream(self.festival_process, self.stream)
        self.cleanup_pyaudio(self.p, self.stream)

    def initialize_pyaudio_stream(self, p):
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            output=True
        )
        return stream

    def play_audio_stream(self, festival_process, stream):
        chunk_size = 1024
        self.is_playing = True
        while self.is_playing:
            self.get_logger().info("Playing audio")
            data = festival_process.stdout.read(chunk_size)
            if not data:
                break
            stream.write(data)
        self.action_done_event.set()

    def cleanup_pyaudio(self, p, stream):
        stream.stop_stream()
        stream.close()
        p.terminate()

    def cancel_playback(self):
        self.is_playing = False
        if self.festival_process:
            self.festival_process.terminate()
        if self.stream:
            self.cleanup_pyaudio(self.p, self.stream)


def main(args=None):
    rclpy.init(args=args)

    action_from_service = TrhTTS()

    executor = MultiThreadedExecutor()
    rclpy.spin(action_from_service, executor)

    rclpy.shutdown()


if __name__ == '__main__':
    main()