import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/tammerhaddad/ament_ws/src/trh_ros/trh_nav/install/my_nav'
