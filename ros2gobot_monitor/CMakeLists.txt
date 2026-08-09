cmake_minimum_required(VERSION 3.8)
project(ros2gobot_monitor)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(ros2gobot_msgs REQUIRED)
find_package(rcl_interfaces REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(tf2_msgs REQUIRED)

add_executable(monitor_node src/monitor_node.cpp)

# 👇 เพิ่มคำสั่งนี้ให้ Compiler รู้จักโฟลเดอร์ include
target_include_directories(monitor_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(monitor_node
  rclcpp
  ros2gobot_msgs
  rcl_interfaces
  sensor_msgs
  nav_msgs
  tf2_msgs
)

# 👇 เพิ่มการติดตั้งโฟลเดอร์ include ด้วย
install(DIRECTORY include/
  DESTINATION include
)

install(TARGETS
  monitor_node
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
