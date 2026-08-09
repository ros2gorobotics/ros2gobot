// BSD 3-Clause License
//
// Copyright (c) 2026, MT Robotics Limited Partnership
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//
// 1. Redistributions of source code must retain the above copyright notice, this
//    list of conditions and the following disclaimer.
//
// 2. Redistributions in binary form must reproduce the above copyright notice,
//    this list of conditions and the following disclaimer in the documentation
//    and/or other materials provided with the distribution.
//
// 3. Neither the name of the copyright holder nor the names of its
//    contributors may be used to endorse or promote products derived from
//    this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
// DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
// FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
// DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
// SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
// CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
// OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
// OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#ifndef ROS2GOBOT_MONITOR__MONITOR_NODE_HPP_
#define ROS2GOBOT_MONITOR__MONITOR_NODE_HPP_

#include <chrono>
#include <memory>
#include <string>
#include <fstream>
#include <algorithm>

#include "rclcpp/rclcpp.hpp"
#include "ros2gobot_msgs/msg/robot_status.hpp"
#include "ros2gobot_msgs/msg/robot_log.hpp"
#include "rcl_interfaces/msg/log.hpp"

class MonitorNode : public rclcpp::Node
{
public:
  MonitorNode();

private:
  void log_callback(const rcl_interfaces::msg::Log::SharedPtr msg);
  float get_cpu_temp();
  float get_cpu_usage();
  void status_timer_callback();

  rclcpp::Subscription<rcl_interfaces::msg::Log>::SharedPtr sub_rosout_;
  rclcpp::Publisher<ros2gobot_msgs::msg::RobotLog>::SharedPtr pub_log_;
  rclcpp::Publisher<ros2gobot_msgs::msg::RobotStatus>::SharedPtr pub_status_;
  rclcpp::TimerBase::SharedPtr timer_status_;

  int node_check_counter_;
  bool navigation_active_;
  bool mapping_active_;
};

#endif  // ROS2GOBOT_MONITOR__MONITOR_NODE_HPP_
