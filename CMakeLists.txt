cmake_minimum_required(VERSION 3.30)
project(S4 VERSION 1.1 LANGUAGES C CXX)

set(S4_IS_TOP_LEVEL OFF)
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    set(S4_IS_TOP_LEVEL ON)
endif()

if(S4_IS_TOP_LEVEL AND NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# Top-level (s4_lua): bootstrap sibling infrastructure → mekil (ILP64 embed). No MKL::MKL.
if(S4_IS_TOP_LEVEL)
    set(_s4_infra_root "${CMAKE_CURRENT_SOURCE_DIR}/../infrastructure")
    if(NOT EXISTS "${_s4_infra_root}/CMakeLists.txt")
        message(FATAL_ERROR
            "S4 top-level requires sibling infrastructure at ${_s4_infra_root} (mekil embed; no MKL::MKL)")
    endif()
    if(NOT DEFINED CMAKE_ENABLE_MKL)
        set(CMAKE_ENABLE_MKL ON CACHE BOOL "Link Intel MKL in mekil/uca")
    endif()
    if(NOT CMAKE_ENABLE_MKL)
        message(FATAL_ERROR "S4 top-level / s4_lua requires CMAKE_ENABLE_MKL=ON (mekil embed)")
    endif()
    set(CMAKE_SCALAR_DOUBLE ON CACHE BOOL "S4 uses double; mekil double precision" FORCE)
    set(INFRA_AS_SUBPROJECT TRUE)
    set(INFRA_OUTPUT_DIR "${CMAKE_BINARY_DIR}")
    # ootb stage copies the build-tree binary; keep RUNPATH $ORIGIN-only (no abs build dir).
    if(UNIX)
        set(CMAKE_BUILD_RPATH "$ORIGIN")
        set(CMAKE_BUILD_RPATH_USE_ORIGIN TRUE)
    endif()
    add_subdirectory("${_s4_infra_root}" "${CMAKE_BINARY_DIR}/_infra")
    unset(_s4_infra_root)
endif()

# Product + s4_lua: MEKIL only. RNP+MKL::MKL is not a supported channel.
set(S4_EIGEN_BACKEND "MEKIL" CACHE STRING "Eigensystem backend: MEKIL only")
set_property(CACHE S4_EIGEN_BACKEND PROPERTY STRINGS MEKIL)
if(NOT S4_EIGEN_BACKEND STREQUAL "MEKIL")
    message(FATAL_ERROR
        "S4_EIGEN_BACKEND=${S4_EIGEN_BACKEND} unsupported; use MEKIL (mekil embed). "
        "RNP + MKL::MKL is removed.")
endif()

option(S4_ENABLE_LUA "Build S4lua interpreter (requires full S4 library)" OFF)

if(S4_IS_TOP_LEVEL)
    set(_s4_default_full ON)
else()
    set(_s4_default_full OFF)
endif()
if(S4_ENABLE_LUA)
    set(_s4_default_full ON)
endif()
option(S4_BUILD_FULL "Build full libS4 (FMM + static archive)" ${_s4_default_full})
unset(_s4_default_full)
if(S4_ENABLE_LUA AND NOT S4_BUILD_FULL)
    set(S4_BUILD_FULL ON CACHE BOOL "Build full libS4 (FMM + static archive)" FORCE)
endif()

function(s4_apply_eigen_backend target_name)
    if(NOT TARGET infrastructure::mekil AND NOT TARGET mekil)
        message(FATAL_ERROR "S4 MEKIL backend requires infrastructure::mekil (or mekil) from infrastructure")
    endif()
    target_compile_definitions(${target_name} PUBLIC S4_EIGEN_BACKEND_MEKIL=1)
    # mekil headers use nested namespaces (MSVC C2429 without /std:c++17+).
    target_compile_features(${target_name} PUBLIC cxx_std_17)
    if(TARGET infrastructure::mekil)
        target_link_libraries(${target_name} PUBLIC infrastructure::mekil)
    else()
        target_link_libraries(${target_name} PUBLIC mekil)
    endif()
endfunction()

set(S4_BRIDGE_INCLUDE_DIRS
    ${CMAKE_CURRENT_SOURCE_DIR}/S4
    ${CMAKE_CURRENT_SOURCE_DIR}/S4/pattern
    ${CMAKE_CURRENT_SOURCE_DIR}/S4/RNP
    ${CMAKE_CURRENT_SOURCE_DIR}/S4/kiss_fft
)

function(s4_apply_compile_opts target_name)
    if(MSVC)
        # /O2 conflicts with Debug's /RTC1 (cl D8016); keep opt only for non-Debug.
        # strcasecmp → _stricmp (historical vc/Makefile /Dstrcasecmp=_stricmp).
        # /W0: third-party S4 sources; suppress legacy warning noise.
        target_compile_options(${target_name} PRIVATE
            $<$<AND:$<COMPILE_LANGUAGE:C,CXX>,$<NOT:$<CONFIG:Debug>>>:/O2>
            $<$<COMPILE_LANGUAGE:C,CXX>:/W0>
        )
        target_compile_definitions(${target_name} PRIVATE strcasecmp=_stricmp)
    else()
        # No -march=*: product/CI binaries use the compiler default ISA (never host-native).
        # -w: third-party S4 sources; suppress legacy warning noise (same as nfmds).
        target_compile_options(${target_name} PRIVATE
            -O3 -w -fcx-limited-range -fno-exceptions -fPIC
        )
    endif()
endfunction()

function(s4_configure_object_target target_name)
    target_include_directories(${target_name} PUBLIC ${S4_BRIDGE_INCLUDE_DIRS})
    s4_apply_compile_opts(${target_name})
    # HAVE_BLAS kept for legacy ifdefs; MEKIL paths must not include TBLAS_ext / Fortran UND.
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

if(S4_BUILD_FULL)
    add_library(S4_fmm_objects OBJECT ${S4_CORE_FMM_SOURCES})
    s4_configure_object_target(S4_fmm_objects)
    s4_apply_eigen_backend(S4_fmm_objects)
endif()

add_library(S4_bridge STATIC ${S4_BRIDGE_SOURCES})

target_include_directories(S4_bridge PUBLIC ${S4_BRIDGE_INCLUDE_DIRS})
s4_apply_compile_opts(S4_bridge)
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

if(S4_BUILD_FULL)
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

    s4_apply_compile_opts(S4)
    target_compile_definitions(S4 PUBLIC HAVE_BLAS)

    s4_apply_eigen_backend(S4)

    set_target_properties(S4 PROPERTIES
        ARCHIVE_OUTPUT_DIRECTORY "${_s4_archive_out}"
        OUTPUT_NAME "S4"
    )
endif()

if(S4_BUILD_FULL)
    add_subdirectory(tests)
endif()

if(S4_ENABLE_LUA)
    if(NOT S4_BUILD_FULL)
        message(FATAL_ERROR "S4_ENABLE_LUA requires S4_BUILD_FULL (full S4 static library)")
    endif()
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
    target_compile_definitions(s4_lua52 PUBLIC $<IF:$<BOOL:${WIN32}>,LUA_USE_WINDOWS,LUA_USE_LINUX>)
    message(STATUS "S4lua: FetchContent lua-5.2.4")
    add_executable(S4lua S4/main_lua.c)
    target_include_directories(S4lua PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/S4
        ${CMAKE_CURRENT_SOURCE_DIR}/S4/RNP
        ${CMAKE_CURRENT_SOURCE_DIR}/S4/kiss_fft
        "${lua52_SOURCE_DIR}/src"
    )
    s4_apply_compile_opts(S4lua)
    if(MSVC)
        target_sources(S4lua PRIVATE S4/win/getopt.c)
        target_include_directories(S4lua PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/S4/win)
        target_compile_definitions(S4lua PRIVATE strdup=_strdup WIN32)
    endif()
    target_compile_definitions(S4lua PRIVATE HAVE_BLAS _USE_MATH_DEFINES)
    target_link_libraries(S4lua PRIVATE S4 s4_lua52)
    if(UNIX)
        target_link_libraries(S4lua PRIVATE dl m stdc++)
        # mekil embeds MKL; S4lua NEEDED libmekil (+ fftw via mekil PUBLIC; iomp5 via mekil).
        # BUILD_WITH_INSTALL_RPATH: stage the build-tree binary with $ORIGIN only.
        set_target_properties(S4lua PROPERTIES
            BUILD_RPATH "$ORIGIN"
            BUILD_RPATH_USE_ORIGIN TRUE
            INSTALL_RPATH "$ORIGIN"
            BUILD_WITH_INSTALL_RPATH TRUE
        )
    endif()
    set_target_properties(S4lua PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${_s4_archive_out}"
    )
endif()
