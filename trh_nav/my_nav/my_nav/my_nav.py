import rclpy
from geometry_msgs.msg import PoseStamped
from stretch_nav2.robot_navigator import BasicNavigator, TaskResult
from rclpy.node import Node
from rclpy.duration import Duration
from std_msgs.msg import String
from trh_msgs.action import SendCoord
from trh_msgs.action import Directions
from rclpy.action import ActionServer
import queue

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

        self._coord_adder = ActionServer(
            self,
            SendCoord,
            'add_coord',
            self.add_coord)
        self._self_navigator = ActionServer(
            self,
            Directions,
            'nav_action',
            self.nav_action)
        
        self.publisher = self.create_publisher(String, 'nav_feedback', 10)
        
        self.get_logger().info('Init done.')
        self.path = []
        self.english_path = []


    def reset_pose(self):
        self.navigator.setInitialPose(self.initial_pose)
        self.navigator.waitUntilNav2Active()
        self.get_logger().info('Initial Pose set to (0,0).')

    def add_coord(self, goal_handle):
        self.get_logger().info('Adding Coord...')
        result = SendCoord.Result()
        feedback = SendCoord.Feedback()
        coordx = goal_handle.request.x
        coordy = goal_handle.request.y
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.pose.position.x = float(coordx)
        pose.pose.position.y = float(coordy)
        pose.pose.orientation.z = 0.0
        pose.pose.orientation.w = 1.0
        self.path.append(pose)
        self.english_path.append(f'({coordx}, {coordy})')
        self.get_logger().info(f'Added coordinate ({coordx}, {coordy})')
        feedback.coord_list = self.english_path
        goal_handle.publish_feedback(feedback)
        result.result = 0
        goal_handle.succeed()
        return result
    
    def nav_action(self, goal_handle):
        self.get_logger().info('Executing navigation...')
        num_poses = goal_handle.request.points
        result = Directions.Result()
        if num_poses > len(self.path):
            self.get_logger().info("Cannot navigate: no destinations in path")
            result.result = "Failed."
            goal_handle.succeed()
            return result

        result = Directions.Result()
        feedback = Directions.Feedback()
        if num_poses < 1:
            self.get_logger().info('Resetting.')
            result.result = "Reset."
            feedback.feedback = "Reset."
            goal_handle.publish_feedback(feedback)
            goal_handle.succeed()
            self.reset_pose()
            return result
        
        poses = []
        for _ in range(num_poses):
            poses.append(self.path.pop(0))
        results = []
        for pose in poses:
            feedback.feedback = f'Navigating to ({pose.pose.position.x}, {pose.pose.position.y})'
            goal_handle.publish_feedback(feedback)
            results.append(self.navigate(pose, feedback))

        feedback.feedback = "Results: " + str(results)
        goal_handle.publish_feedback(feedback)
        
        results = ""
        for i, res in enumerate(results):
            if res == 0:
                results += f"{poses[i].pose.position.x}, {poses[i].pose.position.y} succeeded.\n"
            elif res == 1:
                results += f"{poses[i].pose.position.x}, {poses[i].pose.position.y} canceled.\n"
            elif res == 2:
                results += f"{poses[i].pose.position.x}, {poses[i].pose.position.y} failed.\n"
        
        result.result = results
        self.publisher.publish(String(data=results))
        goal_handle.succeed()
        return result
    
    def navigate(self, pose, goal_handle):
        # goal_feedback = BasicNavigator.Feedback()
        nav_start = self.navigator.get_clock().now()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.navigator.get_clock().now().to_msg()
        route_poses = [pose]
        self.navigator.followWaypoints(route_poses)
        i=0
        while not self.navigator.isTaskComplete():
            i += 1
            feedback = self.navigator.getFeedback()
            if feedback and i % 5 == 0:
                # self.navigator.get_logger().info('Executing current waypoint: (' +
                #     str(pose.pose.position.x) + ", " + str(pose.pose.position.y) + ").")
                # goal_feedback.feedback = f'Executing current waypoint: ({pose.pose.position.x}, {pose.pose.position.y}).'
                # goal_handle.publish_feedback(goal_feedback)
                now = self.navigator.get_clock().now()
  
                # Some navigation timeout to demo cancellation
                if now - nav_start > Duration(seconds=120.0):
                    self.navigator.cancelTask()

        result = self.navigator.getResult()
        if result == TaskResult.SUCCEEDED:
            # goal_feedback.feedback = 'Navigation to (' + str(pose.pose.position.x) + ", " + str(pose.pose.position.y) + ") succeeded."
            # goal_handle.publish_feedback(goal_feedback)
            return 0
        elif result == TaskResult.CANCELED:
            # goal_feedback.feedback = 'Navigation to (' + str(pose.pose.position.x) + ", " + str(pose.pose.position.y) + ") canceled."
            # goal_handle.publish_feedback(goal_feedback)
            return 1
        elif result == TaskResult.FAILED:
            # goal_feedback.feedback = 'Navigation to (' + str(pose.pose.position.x) + ", " + str(pose.pose.position.y) + ") failed."
            # goal_handle.publish_feedback(goal_feedback)
            return 2

def main(args = None):
    rclpy.init(args=args)
    nav = myNavigator()
    rclpy.spin(nav)

if __name__ == '__main__':
    main()