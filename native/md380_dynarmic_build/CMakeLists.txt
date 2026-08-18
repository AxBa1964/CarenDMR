cmake_minimum_required(VERSION 3.12)

project(carendmr_md380_bridge LANGUAGES C CXX)

if(NOT DEFINED MD380_SOURCE_DIR OR MD380_SOURCE_DIR STREQUAL "")
    message(FATAL_ERROR "MD380_SOURCE_DIR muss auf den geklonten md380_vocoder_dynarmic-Quellordner zeigen.")
endif()

if(NOT EXISTS "${MD380_SOURCE_DIR}/CMakeLists.txt")
    message(FATAL_ERROR "MD380_SOURCE_DIR ist ungültig: ${MD380_SOURCE_DIR}")
endif()

# Der Upstream baut eine statische Bibliothek, die anschließend in unsere
# plattformabhängige Shared Library eingebunden wird. PIC verhindert dabei
# insbesondere unter Linux/macOS Linkprobleme.
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

add_subdirectory("${MD380_SOURCE_DIR}" md380_upstream)

add_library(carendmr_md380_bridge SHARED
    "${CMAKE_CURRENT_LIST_DIR}/../md380_dynarmic_bridge.cpp"
)

target_include_directories(carendmr_md380_bridge PRIVATE
    "${MD380_SOURCE_DIR}"
)

target_link_libraries(carendmr_md380_bridge PRIVATE
    md380_vocoder
)

set_target_properties(carendmr_md380_bridge PROPERTIES
    OUTPUT_NAME "carendmr_md380_bridge"
)
