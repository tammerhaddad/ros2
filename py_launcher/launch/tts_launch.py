import launch
from launch_ros.actions import Node

def generate_launch_description():

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

    text_to_prompt = Node(
        package = 'send_input',
        executable = 'send',
        name = 'text_to_prompt',
        parameters=[
            {'tts_package': 'ros'},
        ]
    )
    
    prompt_to_audio = Node(
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

    parcs_tts = Node(
        package = 'parcs_tts',
        executable = 'parcs_tts',
        name = 'parcs_tts',
        parameters=[
            {'interpreter': 'openai'},
        ]
    )

    parcs_stt = Node(
        package = 'parcs_stt',
        executable = 'stt_node',
        name = 'parcs_stt',
    )

    return launch.LaunchDescription([
        # py_tts,
        audio_to_text,
        text_to_prompt,
        prompt_to_audio,
        audio_to_sound,
        speech_to_audio,
        # parcs_tts,
    ])