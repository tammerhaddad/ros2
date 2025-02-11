import rclpy
from geometry_msgs.msg import PoseStamped
from stretch_nav2.robot_navigator import BasicNavigator, TaskResult
from rclpy.node import Node
from rclpy.duration import Duration

class myNavigator(Node):
    def __init__(self):
        super().__init__("my_nav")
        self.navigator = BasicNavigator()
        self.initial_pose = PoseStamped()
        self.initial_pose.header.frame_id = 'map'
        self.initial_pose.header.stamp = self.navigator.get_clock().now().to_msg()
        self.initial_pose.pose.position.x = 0.0
        self.initial_pose.pose.position.y = 0.0
        self.initial_pose.pose.orientation.z = 0.0
        self.initial_pose.pose.orientation.w = 1.0
        self.navigator.setInitialPose(self.initial_pose)
        self.navigator.waitUntilNav2Active()
        self.subscription = self.create_subscription(
            PoseStamped,
            'poses',
            self.navigate,
            10)
        
    def navigate(self, msg):
        pose = msg
        self.get_logger().info('Navigating to ({x}, {y})'.format(x=pose.pose.position.x, y=pose.pose.position.y))
        nav_start = self.navigator.get_clock().now()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.navigator.get_clock().now().to_msg()
        pose.pose.orientation.w = 1.0
        route_poses = [pose]
        self.navigator.followWaypoints(route_poses)
        i=0
        while not self.navigator.isTaskComplete():
            i += 1
            feedback = self.navigator.getFeedback()
            if feedback and i % 5 == 0:
                self.navigator.get_logger().info('Executing current waypoint: (' +
                    str(pose.pose.position.x) + ", " + str(pose.pose.position.y) + ").")
                now = self.navigator.get_clock().now()
  
                # Some navigation timeout to demo cancellation
                if now - nav_start > Duration(seconds=120.0):
                    self.navigator.cancelTask()

        result = self.navigator.getResult()
        if result == TaskResult.SUCCEEDED:
            self.navigator.get_logger().info('Route complete! Restarting...')
            # self.get_logger().info('Navigation complete!, returning home.')
            # self.navigate(self.initial_pose)
        elif result == TaskResult.CANCELED:
            self.navigator.get_logger().info('Security route was canceled, exiting.')
            rclpy.shutdown()
        elif result == TaskResult.FAILED:
            self.navigator.get_logger().info('Security route failed! Restarting from other side...')

def main(args = None):
    rclpy.init(args=args)
    nav = myNavigator()
    rclpy.spin(nav)

if __name__ == '__main__':
    main()