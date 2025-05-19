import rclpy
from geometry_msgs.msg import PoseStamped
from stretch_nav2.robot_navigator import BasicNavigator, TaskResult
from rclpy.node import Node
from rclpy.duration import Duration
from std_msgs.msg import String
from trh_msgs.action import SendCoord
from trh_msgs.action import Directions
from rclpy.action import ActionServer

class myNavigator(Node):
    def __init__(self):
        super().__init__("my_nav")

        # initalizes navigator, which is a wrapper around nav2
        self.navigator = BasicNavigator()

        # simple initial pose, probably can be simplified
        self.initial_pose = PoseStamped()
        self.initial_pose.header.frame_id = 'map'
        self.initial_pose.header.stamp = self.navigator.get_clock().now().to_msg()
        self.initial_pose.pose.position.x = 0.0
        self.initial_pose.pose.position.y = 0.0
        self.initial_pose.pose.orientation.z = 0.0
        self.initial_pose.pose.orientation.w = 1.0
        self.navigator.setInitialPose(self.initial_pose)
        self.navigator.waitUntilNav2Active()

        # action server to add coordinates to queue
        self._coord_adder = ActionServer(
            self,
            SendCoord,
            'add_coord',
            self.add_coord)
        # action server to navigate to previously added coordinates
        self._self_navigator = ActionServer(
            self,
            Directions,
            'nav_action',
            self.nav_action)
                
        self.get_logger().info('Init done.')
        # list of poses to navigate to
        # this is a list of poses, not coordinates
        self.path = []
        # holds the coordinates in a readable format
        self.english_path = []

    # only used when nav_action is used with no coords in queue
    def reset_pose(self):
        # resets the robot to the initial pose (goes home)
        self.navigate(self.initial_pose)
        self.get_logger().info('Resetting to initial pose.')

    # add coord callback, adds a coord to a list
    def add_coord(self, goal_handle):
        self.get_logger().info('Adding Coord...')
        result = SendCoord.Result()
        feedback = SendCoord.Feedback()

        # converts goal into a pose
        coordx = goal_handle.request.x
        coordy = goal_handle.request.y
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.pose.position.x = float(coordx)
        pose.pose.position.y = float(coordy)
        pose.pose.orientation.z = 0.0
        pose.pose.orientation.w = 1.0
        # adds pose and english pose
        self.path.append(pose)
        self.english_path.append(f'({coordx}, {coordy})')
        self.get_logger().info(f'Added coordinate ({coordx}, {coordy})')
        # the poses are just the feedback, and nothing actually ha pens.
        feedback.coord_list = self.english_path
        goal_handle.publish_feedback(feedback)
        result.result = 0
        goal_handle.succeed()
        return result
    
    # callback for nav_action server. Tells the robot to go to the poses in queue.
    def nav_action(self, goal_handle):
        self.get_logger().info('Executing navigation...')
        num_poses = goal_handle.request.points
        result = Directions.Result()
        # if they give a number greater than the number of poses in the queue, it will not work.
        if num_poses > len(self.path):
            self.get_logger().info("Cannot navigate: no destinations in path")
            result.result = "Failed."
            goal_handle.succeed()
            return result

        result = Directions.Result()
        feedback = Directions.Feedback()

        # if there are no poses in the queue, it will reset the robot to (0,0)
        if num_poses < 1:
            self.get_logger().info('Resetting.')
            result.result = "Reset."
            feedback.feedback = "Reset."
            goal_handle.publish_feedback(feedback)
            goal_handle.succeed()
            self.reset_pose()
            return result
        
        # make a list of poses to navigate to
        poses = []
        for _ in range(num_poses):
            poses.append(self.path.pop(0))
        # results is to track the result of each pose, for example (success, success, fail, abort, success)

        # NOT FULLY IMPLEMENTED
        results = []
        # navigates to each pose in order
        for pose in poses:
            feedback.feedback = f'Navigating to ({pose.pose.position.x}, {pose.pose.position.y})'
            goal_handle.publish_feedback(feedback)
            results.append(self.navigate(pose))

        feedback.feedback = "Results: " + str(results)
        goal_handle.publish_feedback(feedback)
        
        # organizes the results
        results = ""
        for i, res in enumerate(results):
            if res == 0:
                results += f"{poses[i].pose.position.x}, {poses[i].pose.position.y} succeeded.\n"
            elif res == 1:
                results += f"{poses[i].pose.position.x}, {poses[i].pose.position.y} canceled.\n"
            elif res == 2:
                results += f"{poses[i].pose.position.x}, {poses[i].pose.position.y} failed.\n"
        
        # and publish the results
        # again, not fully implemented.
        result.result = results
        # self.publisher.publish(String(data=results))
        goal_handle.succeed()
        return result
    
    # navigate function, tells the stretch_nav2 driver to navigate to a coordinate
    def navigate(self, pose):
        # goal_feedback = BasicNavigator.Feedback()
        nav_start = self.navigator.get_clock().now()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.navigator.get_clock().now().to_msg()
        # only works on lists, but we are taking in one pose at a time
        # could be changed as we are navigating to multiple poses, but for now we do one at a time
        route_poses = [pose]
        self.navigator.followWaypoints(route_poses)
        i=0
        # feedback loop while still navigating
        while not self.navigator.isTaskComplete():
            i += 1
            feedback = self.navigator.getFeedback()
            if feedback and i % 5 == 0:
                now = self.navigator.get_clock().now()
  
                # Some navigation timeout to demo cancellation
                if now - nav_start > Duration(seconds=120.0):
                    self.navigator.cancelTask()


        # not used, but meant to give feedback on navigation
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