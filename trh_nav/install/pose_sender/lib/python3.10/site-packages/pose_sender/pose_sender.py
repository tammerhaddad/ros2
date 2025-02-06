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

    def coord_parser(self, coord):
        xy = coord.split(",")
        self.send_coords(self, xy[0], xy[1])

    def send_coords(self, x, y):
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.pose.position.x = float(x)
        pose.pose.position.y = float(y)
        pose.pose.orientation.z = 0.0
        pose.pose.orientation.w = 1.0

        self.publisher.publish(pose)

    

def main(args = None):
    rclpy.init(args=args)
    sender = poseSender()
    sender.get_logger().info("Pose Sender started.")
    coord_x = -1.0
    coord_y = -1.0
    while(coord_x != 0.0 and coord_y != 0.0):
        sender.get_logger().info("Input coords: ")
        coord_x = input("x: ")
        coord_y = input("y: ")
        sender.send_coords(coord_x, coord_y)
    sender.send_coords(0.0, 0.0)
    sender.get_logger().info("Exiting")
    rclpy.shutdown()

if __name__ == '__main__':
    main()