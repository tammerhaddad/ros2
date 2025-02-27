import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from trh_msgs.action import StringAction
from trh_msgs.action import Directions
from trh_msgs.action import SendCoord
from trh_msgs.action import ListReq
from trh_msgs.msg import Coord
from trh_msgs.msg import Num

class NavHub(Node):

	def __init__(self):
		super().__init__('nav_hub')
		self.stt_client = ActionClient(self, ListReq, 'stt')
		self.tts_client = ActionClient(self, self, StringAction, 'TTS_action')
		self.toggle_listen_client = ActionClient(self, Num, 'listen_toggle')
		self.dir_client = ActionClient(self, Directions, 'dir_server')
		# text_to_directions,
		# # pose_sender,
		# trh_nav,
		# text_to_audio,
		# audio_to_sound,
		# auto_tts 

	def stt_goal(self, request):
		goal_msg = ListReq.Goal()
		goal_msg.num = request
		self.stt_client.wait_for_server()
		self._send_goal_future = self.stt_client.send_goal_async(
			goal_msg, feedback_callback=self.stt_feedback)
		self._send_goal_future.add_done_callback(self.sttcallback)
		
	def stt_callback(self, future):
		goal_handle = future.result()
		if not goal_handle.accepted:
			self.get_logger().info('Goal rejected :(')
			return
		self.get_logger().info('Goal accepted :)')
		result = goal_handle.get_result_async()
		self._get_result_future = result
		self._get_result_future.add_done_callback(self.stt_result)

	def stt_result(self, future):
		result = future.result().result
		self.get_logger().info('Result: {0}'.format(result.strresult))
		# rclpy.shutdown()

	def stt_feedback(self, feedback_msg):
		feedback = feedback_msg.feedback
		# self.get_logger().info('Feedback: {0}'.format(feedback.strfeedback))

def main(args=None):
	rclpy.init(args=args)
	node = NavHub()
	rclpy.spin(node)


if __name__ == '__main__':
	main()