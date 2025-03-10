import time
from threading import Event

from example_interfaces.srv import AddTwoInts
from example_interfaces.action import Fibonacci

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor


class ActionFromService(Node):

    def __init__(self):
        super().__init__('action_from_service')
        self.action_done_event = Event()

        self.callback_group = ReentrantCallbackGroup()
        self.action_client = ActionClient(
            self, Fibonacci, 'fibonacci', callback_group=self.callback_group)
        self.srv = self.create_service(
            AddTwoInts,
            'add_two_ints',
            self.add_two_ints_callback,
            callback_group=self.callback_group)
   
    def feedback_callback(self, feedback):
        self.get_logger().info('Received feedback: {0}'.format(feedback.feedback.sequence))

    def add_two_ints_callback(self, request, response):
        self.get_logger().info('Request received: {} + {}'.format(request.a, request.b))
        if not self.action_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('No action server available')
            return response

        response.sum = request.a + request.b

        goal = Fibonacci.Goal()
        goal.order = response.sum

        self.action_done_event.clear()

        # no feedback rn, but it will be a list of the current coords in queue
        send_goal_future = self.action_client.send_goal_async(goal)
        send_goal_future.add_done_callback(self.goal_response_callback)

        # Wait for action to be done
        self.action_done_event.wait()

        return response

    def goal_response_callback(self, future):
        goal_handle = future.result()
        get_result_future = goal_handle.get_result_async()
        get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        # Signal that action is done
        self.action_done_event.set()


def main(args=None):
    rclpy.init(args=args)

    action_from_service = ActionFromService()

    executor = MultiThreadedExecutor()
    rclpy.spin(action_from_service, executor)

    rclpy.shutdown()


if __name__ == '__main__':
    main()