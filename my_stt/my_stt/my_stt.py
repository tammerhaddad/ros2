# Copyright 2016 Open Source Robotics Foundation, Inc.

#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import numpy as np
import whisper
import openai
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from audio_common_msgs.msg import AudioStamped
from std_msgs.msg import String


class SpeechToText(Node):

    def __init__(self):
        super().__init__('speech_to_text')
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,  # Ensure reliability
            depth=10
        )

        self.listening = False
        self.subscription = self.create_subscription(
            AudioStamped,
            'input_audio',
            self.listener_callback,
            qos_profile)
        self.publisher = self.create_publisher(
            String,
            'input_text',
            10)
        
        self.publisher2 = self.create_publisher(String, 'times', 10)
        self.publisher3 = self.create_publisher(String, 'volume', 10)
        
        self.accumulated_data = bytearray()
        self.is_accumulating = False
        self.volume_threshold = -1
        self.sample_rate = 16000  # assuming 16kHz sample rate
        self.silence_start_time = None
        self.node_start_time = time.time()
        self.calibration_volumes = []

        self.declare_parameter('silence_duration', 1)  # seconds
        self.declare_parameter('calibration_duration', 3)  # seconds
        self.declare_parameter('interpreter', 'base'), # base, small

        self.silence_duration = self.get_parameter('silence_duration').get_parameter_value().integer_value
        self.calibration_duration = self.get_parameter('calibration_duration').get_parameter_value().integer_value

        self.model = whisper.load_model(self.get_parameter('interpreter').get_parameter_value().string_value)
        self.get_logger().info('\nInit done.\n')

    def listener_callback(self, audio: AudioStamped):
        if not self.listening:
            return
        
        audio_data = np.frombuffer(audio.audio.audio_data.int16_data, dtype=np.int16)
        if len(audio_data) > 0:
            volume = np.linalg.norm(audio_data) / len(audio_data)
        else:
            volume = 0

        self.publisher3.publish(String(data='Vol: {volume}'.format(volume=volume)))
        # self.get_logger().info(f'Volume: {volume}, Threshold: {self.volume_threshold}')

        if self.volume_threshold == -1:
            self.set_background_noise_level(audio)
            return
        
        if volume > self.volume_threshold:
            if not self.is_accumulating:
                current_time = time.strftime('%H:%M:%S', time.localtime())
                milliseconds = int((time.time() % 1) * 1000)
                self.publisher2.publish(String(data='[{time}:{milliseconds}]: Audio started.'.format(time=current_time, milliseconds=milliseconds)))
            self.accumulated_data.extend(audio_data)
            self.is_accumulating = True
            self.silence_start_time = None
        elif self.is_accumulating:
            if self.silence_start_time is None:
                self.silence_start_time = time.time()
            elif time.time() - self.silence_start_time >= self.silence_duration:
                self.is_accumulating = False
                current_time = time.strftime('%H:%M:%S', time.localtime())
                milliseconds = int((time.time() % 1) * 1000)
                self.publisher2.publish(String(data='[{time}:{milliseconds}]: Audio off, processing.'.format(time=current_time, milliseconds=milliseconds)))
                # self.process_audio_chunk(self.accumulated_data)
                self.listening = False
                self.process_audio_chunk(self.accumulated_data)
                self.accumulated_data = bytearray()
                self.silence_start_time = None
    
    def set_background_noise_level(self, audio: AudioStamped):
        audio_data = np.frombuffer(audio.audio.audio_data.int16_data, dtype=np.int16)

        if self.silence_start_time is None:
            self.get_logger().info('Calibrating... (shut up)')
            self.silence_start_time = time.time()
            self.is_accumulating = True
        elif time.time() - self.silence_start_time >= self.calibration_duration:
            max_vol = np.max(self.calibration_volumes)
            self.volume_threshold = max_vol*2 + 3
            self.accumulated_data = bytearray()
            self.silence_start_time = None
            self.is_accumulating = False
            self.get_logger().info(f"Calibrated. Volume threshold: {self.volume_threshold}")

        
        if self.is_accumulating:
            volume = np.linalg.norm(audio_data) / len(audio_data)
            self.calibration_volumes.append(volume)
        


    def process_audio_chunk(self, audio_chunk):
        audio_data = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
        result = self.model.transcribe(audio_data, fp16=False)
        text = result['text']
        current_time = time.strftime('%H:%M:%S', time.localtime())
        milliseconds = int((time.time() % 1) * 1000)
        self.publisher2.publish(String(data='[{time}:{milliseconds}]: Audio processed.'.format(time=current_time, milliseconds=milliseconds)))

        # self.action_client.wait_for_server()
        # goal_msg = TTS2.Goal()
        # goal_msg.tts = text
        # self.action_client.send_goal_async(goal_msg)

        self.get_logger().info(f'Recognized text: {text}')

        if len(text) > 0:
            self.publisher.publish(String(data=text))
        else: 
            self.get_logger().info('No text recognized, not publishing')

def main(args=None):
    rclpy.init(args=args)
    stt = SpeechToText()
    rclpy.spin(stt)
    stt.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

