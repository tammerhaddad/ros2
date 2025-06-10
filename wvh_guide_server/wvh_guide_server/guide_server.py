import rclpy
import time
from rclpy.action import ActionServer
from rclpy.node import Node

from trh_msgs.action import StringAction
from wvh_guide import run

class GuideServer(Node):

    def __init__(self):
        super().__init__('guide_server')
        self._action_server = ActionServer(
            self,
            StringAction,
            'guide_server',
            self.execute_callback)
        self.get_logger().info('Init done.')

    def execute_callback(self, goal_handle):
        self.get_logger().info('Executing goal...')
        result = StringAction.Result()
        path = goal_handle.request.strrequest.split(",")
        summary, path = run(
            start=path[0],
            goal=path[1],
            show_map=False
        )

        print("\n".join(summary))
        print("Path:", path)
        result.strresult = " ".join(summary)
        goal_handle.succeed()
        return result


def main(args=None):
    rclpy.init(args=args)

    action_server = GuideServer()

    rclpy.spin(action_server)


if __name__ == '__main__':
    main()