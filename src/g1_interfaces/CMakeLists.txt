cmake_minimum_required(VERSION 3.8)
project(g1_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# 依赖
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# 生成消息
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/FaceResult.msg"
  "msg/MotionCmd.msg"
)

# 导出运行时依赖
ament_export_dependencies(rosidl_default_runtime)

# 最后必须是这个
ament_package()
