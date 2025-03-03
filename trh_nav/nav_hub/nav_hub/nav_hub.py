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

class NavHub(Node):

	def __init__(self):
		super().__init__('nav_hub')
		self.tts_client = ActionClient(self, self, StringAction, 'TTS_action')
		self.toggle_listen_client = ActionClient(self, Num, 'listen_toggle') # not used
		self.dir_client = ActionClient(self, SendCoord, 'dir_server')
		self.nav_client = ActionClient(self, Directions, 'nav_action')
		self.voice_sub = self.create_subscription(
            String,
            'input_text',
            self.send_directions,
            10
        )
		# text_to_directions,
		# # pose_sender,
		# trh_nav,
		# text_to_audio,
		# audio_to_sound,
		# auto_tts 

def main(args=None):
	rclpy.init(args=args)
	node = NavHub()
	rclpy.spin(node)


if __name__ == '__main__':
	main()