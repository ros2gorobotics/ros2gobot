cmake_minimum_required(VERSION 3.5)
project(ros2gobot_navigation)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY launch rviz config maps
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/robot_map
  scripts/robot_nav
  DESTINATION bin
)

ament_package()
