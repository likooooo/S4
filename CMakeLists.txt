cmake_minimum_required(VERSION 3.30)
project(S4 VERSION 1.1 LANGUAGES C CXX)

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
    target_compile_options(${target_name} PRIVATE
        -O3 -Wall -march=native -fcx-limited-range -fno-exceptions -fPIC
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

set(S4_CORE_FMM_SOURCES
    S4/S4.cpp
    S4/rcwa.cpp
    S4/fmm/fmm_common.cpp
    S4/fmm/fmm_closed.cpp
    S4/fmm/fmm_PolBasisNV.cpp
    S4/fmm/fmm_PolBasisVL.cpp
    S4/fmm/fmm_PolBasisJones.cpp
    S4/fmm/fmm_kottke.cpp
    S4/fmm/fmm_experimental.cpp
    S4/fmm/fmm_FFT.cpp
    S4/fmm/fft_iface.cpp
    S4/kiss_fft/kiss_fft.c
    S4/kiss_fft/tools/kiss_fftnd.c
)

add_library(S4_pattern_objects OBJECT ${S4_PATTERN_SOURCES})
s4_configure_object_target(S4_pattern_objects)

set(S4_BRIDGE_SOURCES
    S4/s4_bridge.cpp
    S4/s4_bridge_glist.cpp
    $<TARGET_OBJECTS:S4_pattern_objects>
)

if(SIMULATION_MKL_REQUESTED)
    add_library(S4_fmm_objects OBJECT ${S4_CORE_FMM_SOURCES})
    s4_configure_object_target(S4_fmm_objects)
    s4_apply_eigen_backend(S4_fmm_objects)
endif()

add_library(S4_bridge STATIC ${S4_BRIDGE_SOURCES})

target_include_directories(S4_bridge PUBLIC ${S4_BRIDGE_INCLUDE_DIRS})

target_compile_options(S4_bridge PRIVATE
    -O3 -Wall -march=native -fcx-limited-range -fno-exceptions -fPIC
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

if(SIMULATION_MKL_REQUESTED)
    set(S4_EXTRA_SOURCES
        S4/SpectrumSampler.c
        S4/cubature.c
        S4/Interpolator.c
        S4/convert.c
    )

    add_library(S4 STATIC
        $<TARGET_OBJECTS:S4_pattern_objects>
        $<TARGET_OBJECTS:S4_fmm_objects>
        ${S4_EXTRA_SOURCES}
    )

    target_include_directories(S4 PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/S4
        ${CMAKE_CURRENT_SOURCE_DIR}/S4/RNP
        ${CMAKE_CURRENT_SOURCE_DIR}/S4/kiss_fft
    )

    target_compile_options(S4 PRIVATE
        -O3 -Wall -march=native -fcx-limited-range -fno-exceptions -fPIC
    )

    target_compile_definitions(S4 PUBLIC HAVE_BLAS)

    s4_apply_eigen_backend(S4)

    set_target_properties(S4 PROPERTIES
        ARCHIVE_OUTPUT_DIRECTORY "${_s4_archive_out}"
        OUTPUT_NAME "S4"
    )
endif()

if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/tests/CMakeLists.txt" AND SIMULATION_MKL_REQUESTED)
    add_subdirectory(tests)
endif()

option(S4_ENABLE_LUA "Build S4lua interpreter (requires full S4 library)" OFF)

if(S4_ENABLE_LUA)
    if(NOT SIMULATION_MKL_REQUESTED)
        message(FATAL_ERROR "S4_ENABLE_LUA requires SIMULATION_MKL_REQUESTED (full S4 static library)")
    endif()
    find_package(Lua 5.2 QUIET)
    if(Lua_FOUND)
        set(S4_LUA_INCLUDE_DIRS ${LUA_INCLUDE_DIR})
        set(S4_LUA_LINK_LIBS ${LUA_LIBRARIES})
    else()
        include(FetchContent)
        FetchContent_Declare(
            lua52
            URL https://www.lua.org/ftp/lua-5.2.4.tar.gz
            URL_HASH SHA256=b9e2e4aad6789b3b63a056d442f7b39f0ecfca3ae0f1fc0ae4e9614401b69f4b
        )
        FetchContent_MakeAvailable(lua52)
        file(GLOB _s4_lua_core_src "${lua52_SOURCE_DIR}/src/*.c")
        list(REMOVE_ITEM _s4_lua_core_src "${lua52_SOURCE_DIR}/src/lua.c" "${lua52_SOURCE_DIR}/src/luac.c")
        add_library(s4_lua52 STATIC ${_s4_lua_core_src})
        target_include_directories(s4_lua52 PUBLIC "${lua52_SOURCE_DIR}/src")
        target_compile_definitions(s4_lua52 PUBLIC LUA_USE_LINUX)
        set(S4_LUA_INCLUDE_DIRS "${lua52_SOURCE_DIR}/src")
        set(S4_LUA_LINK_LIBS s4_lua52)
        message(STATUS "S4lua: using FetchContent lua-5.2.4 (system Lua 5.2 not found)")
    endif()
    add_executable(S4lua S4/main_lua.c)
    target_include_directories(S4lua PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/S4
        ${CMAKE_CURRENT_SOURCE_DIR}/S4/RNP
        ${CMAKE_CURRENT_SOURCE_DIR}/S4/kiss_fft
        ${S4_LUA_INCLUDE_DIRS}
    )
    target_compile_options(S4lua PRIVATE -O3 -Wall -march=native -fcx-limited-range -fPIC)
    target_compile_definitions(S4lua PRIVATE HAVE_BLAS _USE_MATH_DEFINES)
    target_link_libraries(S4lua PRIVATE S4 ${S4_LUA_LINK_LIBS} dl m stdc++)
    set_target_properties(S4lua PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${_s4_archive_out}"
    )
endif()
