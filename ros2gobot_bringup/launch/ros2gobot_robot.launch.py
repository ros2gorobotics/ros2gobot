# BSD 3-Clause License
# ... (ลิขสิทธิ์คงเดิมตามต้นฉบับ)

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction, RegisterEventHandler, EmitEvent
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown

# Obtains share directory paths.
pkg_ros2gobot_bringup = get_package_share_directory('ros2gobot_bringup')
pkg_ros2gobot_control = get_package_share_directory('ros2gobot_control')
pkg_ros2gobot_description = get_package_share_directory('ros2gobot_description')

def generate_launch_description():

    odom_topic_arg = DeclareLaunchArgument(
                name='odom_topic', 
                default_value='/odom',
                description='EKF out odometry topic'
            )
    odom_topic = LaunchConfiguration('odom_topic')  

    rplidar_arg = DeclareLaunchArgument(
            'include_rplidar',
            default_value='True',
            description='Indicates whether to include rplidar launch.')
    rplidar =  LaunchConfiguration('include_rplidar')
    
    # [NEW] อาร์กิวเมนต์ launch สำหรับสลับการกรองสแกนเลเซอร์
    laser_range_filter_arg = DeclareLaunchArgument(
            'laser_range_filter',
            default_value='True',
            description='Enable laser scan filtering')
    laser_range_filter = LaunchConfiguration('laser_range_filter')
       
    # Includes ros2gobot_description launch file
    include_ros2gobot_description = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros2gobot_description, 'launch', 'ros2gobot_description.launch.py'),
        ),
    )

    # Include ros2gobot_control launch file
    include_ros2gobot_control =  IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros2gobot_control, 'launch', 'ros2gobot_control.launch.py'),
        ),
        launch_arguments={
        }.items()
    )

    # Include rplidar launch file
    include_rplidar = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros2gobot_bringup, 'launch', 'rplidar.launch.py'),
        ),
        launch_arguments={
            "serial_port": '/dev/tty_lidar',
            "laser_range_filter": laser_range_filter, # [NEW] ส่งค่าไปยัง Lidar launch
        }.items(),
            condition=IfCondition(rplidar)
    )
    
    # ----------------------------------------------------
    # การเพิ่ม IMU Node (BNO08x)
    # ----------------------------------------------------
    pkg_bno086_driver = get_package_share_directory('bno086_uartrvc_driver')

    imu_config_file = os.path.join(
        pkg_bno086_driver, 
        'config',
        'bno086_uart_rvc.yaml'
    )

    imu_node = Node(
        package='bno086_uartrvc_driver',  
        executable='bno086_uartrvc_driver',  
        name='bno086_uartrvc_driver',
        output='screen',
        parameters=[imu_config_file]
    )

    # IMU สามารถเริ่มได้พร้อมกับเซ็นเซอร์อื่นๆ (3.0 วินาที)
    imu_timer = TimerAction(period=3.0, actions=[imu_node])


    # ----------------------------------------------------
    # การเพิ่ม EKF Node (robot_localization)
    # ----------------------------------------------------
    ekf_config_file = os.path.join(
        pkg_ros2gobot_bringup, 'config', 'ekf.yaml'
    )
    
    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[ekf_config_file],
        remappings=[("odometry/filtered",odom_topic)]
    )

    # EKF ควรเริ่มหลังจาก ros2gobot_control และ IMU เริ่มทำงานและเผยแพร่ข้อมูลแล้ว (ตั้งค่าเป็น 6.0 วินาที)
    ekf_timer = TimerAction(period=6.0, actions=[ekf_node])
    
    # ----------------------------------------------------
    # Global Error Handler
    # ----------------------------------------------------
    def handle_process_exit(event, context):
        if event.returncode != 0 and event.returncode is not None:
            return EmitEvent(
                event=Shutdown(reason=f'\n\n[FATAL ERROR] Process exited with code {event.returncode}! Shutting down entire launch system.\n')
            )
        return None

    global_shutdown_handler = RegisterEventHandler(
        event_handler=OnProcessExit(
            on_exit=handle_process_exit
        )
    )
    
    # ----------------------------------------------------
    # ROS2GO Monitor, API Server และ Rosbridge
    # ----------------------------------------------------
    ros2gobot_monitor_node = Node(
        package='ros2gobot_monitor',
        executable='monitor_node',
        name='ros2gobot_monitor',
        output='screen'
    )
    
    api_server_node = Node(
        package='ros2gobot_monitor',
        executable='api_server',
        name='api_server_node',
        output='screen'
    )

    rosbridge_websocket_node = Node(
        package='rosbridge_server',
        executable='rosbridge_websocket',
        name='rosbridge_websocket',
        output='screen',
        parameters=[{'port': 9090}]
    )
    # ----------------------------------------------------

    # Waits for ros2gobot_description to set up robot_state_publisher.
    ros2gobot_control_timer = TimerAction(period=5.0, actions=[include_ros2gobot_control])
    # Defer sensors launch to avoid overhead while robot_state_publisher is setting up.
    rplidar_timer = TimerAction(period=3.0, actions=[include_rplidar])

    return LaunchDescription([
        global_shutdown_handler, 
        include_ros2gobot_description,
        ros2gobot_control_timer,
        odom_topic_arg,
        imu_timer,
        ekf_timer,
        rplidar_arg,
        laser_range_filter_arg,      # [NEW] Argument สำหรับ Filter
        rplidar_timer,
        ros2gobot_monitor_node,      # Node ติดตามสถานะ
        api_server_node,             # Node สำหรับ Web API (สั่งงานผ่านเว็บ)
        rosbridge_websocket_node,    # Node สำหรับ WebSocket
    ])
