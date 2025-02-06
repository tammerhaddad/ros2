import rclpy
from geometry_msgs.msg import PoseStamped
from stretch_nav2.robot_navigator import BasicNavigator, TaskResult
from rclpy.node import Node
from rclpy.duration import Duration
# from trh_msgs.msg import Coord
from std_msgs.msg import String

class poseSender(Node):

    def __init__(self):
        super().__init__('pose_sender')
        self.publisher = self.create_publisher(
            PoseStamped,
            'poses',
            10
        )
        self.subscriber = self.create_subscription(
            String, #Coord
            'text_poses',
            self.coord_parser,
            10
        )
        self.running = True

    def coord_parser(self, coord):
        xy = coord.data.split(",")
        self.send_coords(xy[0], xy[1])

    def send_coords(self, x, y):
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.pose.position.x = float(x)
        pose.pose.position.y = float(y)
        pose.pose.orientation.z = 0.0
        pose.pose.orientation.w = 1.0

        self.publisher.publish(pose)
        if (pose.pose.position.x == pose.pose.position.y == 0.0):
            self.running = False

    

def main(args = None):
    rclpy.init(args=args)
    sender = poseSender()
    sender.get_logger().info("Pose Sender started.")
    if not sender.running:
        sender.get_logger().info("Returning to home and shutting down.")
        rclpy.shutdown
    rclpy.spin(sender)

if __name__ == '__main__':
    main()