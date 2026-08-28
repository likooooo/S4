cmake_minimum_required(VERSION 3.30)
project(S4 VERSION 1.1 LANGUAGES C CXX)

# Bridge-only (full S4 / Lua archived at simulation_core/.tmp/S4_full_CMakeLists.txt).

set(S4_EIGEN_BACKEND "MEKIL" CACHE STRING "Eigensystem backend: MEKIL or RNP")
set_property(CACHE S4_EIGEN_BACKEND PROPERTY STRINGS MEKIL RNP)

function(s4_apply_eigen_backend target_name)
    if(S4_EIGEN_BACKEND STREQUAL "MEKIL")
        if(NOT TARGET infrastructure::uca)
            message(FATAL_ERROR "S4 MEKIL backend requires infrastructure::uca from parent project")
        endif()
        target_compile_definitions(${target_name} PUBLIC S4_EIGEN_BACKEND_MEKIL=1)
        target_link_libraries(${target_name} PUBLIC infrastructure::uca)
    elseif(S4_EIGEN_BACKEND STREQUAL "RNP")
        target_compile_definitions(${target_name} PUBLIC S4_EIGEN_BACKEND_RNP=1 HAVE_LAPACK)
        if(TARGET infrastructure::uca)
            target_link_libraries(${target_name} PUBLIC infrastructure::uca)
        else()
            find_package(MKL CONFIG QUIET)
            if(MKL_FOUND)
                target_link_libraries(${target_name} PUBLIC MKL::MKL)
            else()
                target_link_libraries(${target_name} PUBLIC lapack blas)
            endif()
        endif()
    else()
        message(FATAL_ERROR "Unknown S4_EIGEN_BACKEND=${S4_EIGEN_BACKEND}")
    endif()
endfunction()

set(S4_BRIDGE_INCLUDE_DIRS
    ${CMAKE_CURRENT_SOURCE_DIR}/S4
    ${CMAKE_CURRENT_SOURCE_DIR}/S4/pattern
    ${CMAKE_CURRENT_SOURCE_DIR}/S4/RNP
    ${CMAKE_CURRENT_SOURCE_DIR}/S4/kiss_fft
)

function(s4_configure_object_target target_name)
    target_include_directories(${target_name} PUBLIC ${S4_BRIDGE_INCLUDE_DIRS})
    # -w: third-party C (K&R predicates, macro redefs, unused locals); not ours to fix
    target_compile_options(${target_name} PRIVATE
        -O3 -w -march=native -fcx-limited-range -fno-exceptions -fPIC
    )
    target_compile_definitions(${target_name} PUBLIC HAVE_BLAS _USE_MATH_DEFINES)
endfunction()

set(S4_PATTERN_SOURCES
    S4/gsel.c
    S4/sort.c
    S4/pattern/pattern.c
    S4/pattern/intersection.c
    S4/pattern/predicates.c
    S4/numalloc.c
)

add_library(S4_pattern_objects OBJECT ${S4_PATTERN_SOURCES})
s4_configure_object_target(S4_pattern_objects)

set(S4_BRIDGE_SOURCES
    S4/s4_bridge.cpp
    S4/s4_bridge_glist.cpp
    $<TARGET_OBJECTS:S4_pattern_objects>
)

add_library(S4_bridge STATIC ${S4_BRIDGE_SOURCES})

target_include_directories(S4_bridge PUBLIC ${S4_BRIDGE_INCLUDE_DIRS})

target_compile_options(S4_bridge PRIVATE
    -O3 -w -march=native -fcx-limited-range -fno-exceptions -fPIC
)

target_compile_definitions(S4_bridge PUBLIC HAVE_BLAS _USE_MATH_DEFINES)

if(DEFINED S4_OUTPUT_DIR)
    set(_s4_archive_out "${S4_OUTPUT_DIR}")
else()
    set(_s4_archive_out "${CMAKE_BINARY_DIR}")
endif()

set_target_properties(S4_bridge PROPERTIES
    ARCHIVE_OUTPUT_DIRECTORY "${_s4_archive_out}"
    OUTPUT_NAME "S4_bridge"
)
