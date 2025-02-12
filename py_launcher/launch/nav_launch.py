import launch
import os
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():

    nav_driver_launch = IncludeLaunchDescription(
      PythonLaunchDescriptionSource([os.path.join(
         get_package_share_directory('stretch_nav2'), 'launch',
         'navigation.launch.py')]),
         launch_arguments={'map': os.path.join(os.getenv('HELLO_FLEET_PATH'), 'maps', 'local_correct_map.yaml')}.items(),
      )

    speech_to_audio = Node(
        package = 'audio_common',
        executable = 'audio_capturer_node',
        name = 'speech_to_audio',
        remappings=[
                ('audio', 'input_audio'),
        ]
    )

    audio_to_text = Node(
        package = 'my_stt',
        executable = 'stt',
        name = 'audio_to_text',
    )

    text_to_directions = Node(
        package= 'text_to_directions',
        executable = 'send_dir',
        name = 'text_to_directions'
    )

    pose_sender = Node(
        package = 'pose_sender',
        executable = 'send_pose',
        name = 'pose_sender'
    )

    trh_nav = Node(
        package = 'my_nav',
        executable = 'trh_nav',
        name = 'trh_navigation'
    )

    text_to_audio = Node(
        package = 'tts_ros',
        executable = 'tts_node',
        name = 'prompt_to_audio',
        remappings=[
                ('audio', 'output_audio'),
            ]
    )

    audio_to_sound = Node(
        package = 'audio_common',
        executable = 'audio_player_node',
        name = 'audio_to_sound',
        remappings=[
                ('audio', 'output_audio'),
            ]
    )

    auto_tts = Node(
        package = 'autoTTS',
        executable = 'autoTTS',
        name = 'auto_tts',
    )

    return launch.LaunchDescription([
        nav_driver_launch,
        speech_to_audio,
        audio_to_text,
        text_to_directions,
        pose_sender,
        trh_nav,
        text_to_audio,
        audio_to_sound,
        auto_tts
    ])