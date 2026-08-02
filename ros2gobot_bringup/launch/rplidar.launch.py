import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler, OpaqueFunction, TimerAction
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessIO
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node

def generate_launch_description():
    channel_type = LaunchConfiguration('channel_type', default='serial')
    serial_port = LaunchConfiguration('serial_port', default='/dev/tty_lidar')
    serial_baudrate = LaunchConfiguration('serial_baudrate', default='460800')
    frame_id = LaunchConfiguration('frame_id', default='laser_link')
    inverted = LaunchConfiguration('inverted', default='false')
    angle_compensate = LaunchConfiguration('angle_compensate', default='true')
    scan_mode = LaunchConfiguration('scan_mode', default='Standard')
    # เพิ่มอาร์กิวเมนต์ launch สำหรับ laser_range_filter (default True)
    laser_range_filter_arg = DeclareLaunchArgument('laser_range_filter', default_value='True', description='Adds a laser range filter in the output.')
    laser_range_filter = LaunchConfiguration('laser_range_filter')

    # 1. ระบุ Path ไปยังไฟล์ lidar_ok.txt
    bringup_dir = get_package_share_directory('ros2gobot_bringup')
    ascii_file_path = os.path.join(bringup_dir, 'config', 'lidar_ok.txt')

    # 2. โหลดข้อความจากไฟล์
    try:
        with open(ascii_file_path, 'r') as f:
            lidar_ok_ascii = '\n' + f.read() + '\n'
    except FileNotFoundError:
        lidar_ok_ascii = "\n\n  >>> LIDAR-OK <<< \n\n"

    # ตัวแปรสำหรับเช็คว่าเราปริ้นท์ไปแล้วหรือยัง (ป้องกันการปริ้นท์ซ้ำ)
    has_printed_ascii = False

    def print_ascii_art(context, *args, **kwargs):
        print(lidar_ok_ascii)
        return []

    def check_lidar_status(event):
        nonlocal has_printed_ascii
        
        # ถ้าเคยปริ้นท์ไปแล้ว ให้ข้ามไปเลย ไม่ต้องทำอะไรซ้ำ
        if has_printed_ascii:
            return []

        log_text = event.text.decode('utf-8', 'replace').lower()
        
        if 'health status : ok' in log_text:
            has_printed_ascii = True # ล็อคไว้ว่าปริ้นท์แล้ว
            
            # เมื่อเจอคำว่า OK ให้หน่วงเวลา 1.0 วินาทีก่อน ค่อยสั่ง print
            # เพื่อให้ Log อื่นๆ ของ Lidar แสดงจนเสร็จก่อน
            return [
                TimerAction(
                    period=1.0, 
                    actions=[OpaqueFunction(function=print_ascii_art)]
                )
            ]
        return []

    ###############################
    ## Not using laser range filter.
    ## Condition: user says FALSE
    ###############################
    sllidar_node_no_filter = Node(
        package='sllidar_ros2',
        executable='sllidar_node',
        name='rplidar_node',
        parameters=[{'channel_type': channel_type,
                     'serial_port': serial_port,
                     'serial_baudrate': serial_baudrate,
                     'frame_id': frame_id,
                     'inverted': inverted,
                     'scan_mode': scan_mode,
                     'angle_compensate': angle_compensate}],
        output='screen',
        # Condition: use only if filter is disabled
        condition=IfCondition(PythonExpression(['not ', laser_range_filter])),
    )

    ###############################
    ## Using laser range filter
    ## Condition: user says TRUE
    ###############################
    sllidar_node_with_filter = Node(
        package='sllidar_ros2',
        executable='sllidar_node',
        name='rplidar_node',
        parameters=[{'channel_type': channel_type,
                     'serial_port': serial_port,
                     'serial_baudrate': serial_baudrate,
                     'frame_id': frame_id,
                     'inverted': inverted,
                     'scan_mode': scan_mode,
                     'angle_compensate': angle_compensate}],
        output='screen',
        # Condition: use only if filter is enabled
        condition=IfCondition(laser_range_filter),
        # Remap to scan_raw topic
        remappings=[('scan', 'scan_raw')]
    )

    laser_filter_node = Node(
        package="laser_filters",
        executable="scan_to_scan_filter_chain",
        parameters=[
            PathJoinSubstitution([
                get_package_share_directory("ros2gobot_bringup"),
                "config", "laser_range_filter.yaml",
            ])],
        output='screen',
        # Receive scan_raw and publish scan_filtered
        remappings=[
          ('scan', 'scan_raw'),
          ('scan_filtered', 'scan'), # Remap output to final scan topic
        ],
        # Condition: use only if filter is enabled
        condition=IfCondition(laser_range_filter)
    )

    ###############################
    ## Event Handlers สำหรับดักจับ Log
    ###############################
    # Unfiltered Event Handler
    # Condition: user says FALSE
    unfiltered_handler = RegisterEventHandler(
        OnProcessIO(
            target_action=sllidar_node_no_filter,
            on_stdout=check_lidar_status,
            on_stderr=check_lidar_status
        ),
        condition=IfCondition(PythonExpression(['not ', laser_range_filter]))
    )

    # Filtered Event Handler
    # Condition: user says TRUE
    filtered_handler = RegisterEventHandler(
        OnProcessIO(
            target_action=sllidar_node_with_filter,
            on_stdout=check_lidar_status,
            on_stderr=check_lidar_status
        ),
        condition=IfCondition(laser_range_filter)
    )

    return LaunchDescription([
        DeclareLaunchArgument('channel_type', default_value=channel_type, description='Specifying channel type of lidar'),
        DeclareLaunchArgument('serial_port', default_value=serial_port, description='Specifying usb port to connected lidar'),
        DeclareLaunchArgument('serial_baudrate', default_value=serial_baudrate, description='Specifying usb port baudrate to connected lidar'),
        DeclareLaunchArgument('frame_id', default_value=frame_id, description='Specifying frame_id of lidar'),
        DeclareLaunchArgument('inverted', default_value=inverted, description='Specifying whether or not to invert scan data'),
        DeclareLaunchArgument('angle_compensate', default_value=angle_compensate, description='Specifying whether or not to enable angle_compensate of scan data'),
        DeclareLaunchArgument('scan_mode', default_value=scan_mode, description='Specifying scan mode of lidar'),
        laser_range_filter_arg,

        sllidar_node_no_filter, # This is only included in final description list if not laser_range_filter
        sllidar_node_with_filter, # This is only included in final description list if laser_range_filter
        laser_filter_node, # This is only included in final description list if laser_range_filter

        unfiltered_handler,
        filtered_handler
    ])