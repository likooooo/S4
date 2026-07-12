cmake_minimum_required(VERSION 3.30)
project(S4 VERSION 1.1 LANGUAGES C CXX)

set(S4_EIGEN_BACKEND "MEKIL" CACHE STRING "Eigensystem backend: MEKIL or RNP")
set_property(CACHE S4_EIGEN_BACKEND PROPERTY STRINGS MEKIL RNP)

set(S4_SOURCES
    S4/S4.cpp
    S4/rcwa.cpp
    S4/fmm/fmm_common.cpp
    S4/fmm/fmm_FFT.cpp
    S4/fmm/fmm_kottke.cpp
    S4/fmm/fmm_closed.cpp
    S4/fmm/fmm_PolBasisNV.cpp
    S4/fmm/fmm_PolBasisVL.cpp
    S4/fmm/fmm_PolBasisJones.cpp
    S4/fmm/fmm_experimental.cpp
    S4/fmm/fft_iface.cpp
    S4/pattern/pattern.c
    S4/pattern/intersection.c
    S4/pattern/predicates.c
    S4/numalloc.c
    S4/gsel.c
    S4/sort.c
    S4/kiss_fft/kiss_fft.c
    S4/kiss_fft/tools/kiss_fftnd.c
    S4/SpectrumSampler.c
    S4/cubature.c
    S4/Interpolator.c
    S4/convert.c
)

add_library(S4 STATIC ${S4_SOURCES})

target_include_directories(S4 PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/S4
    ${CMAKE_CURRENT_SOURCE_DIR}/S4/RNP
    ${CMAKE_CURRENT_SOURCE_DIR}/S4/kiss_fft
)

target_compile_options(S4 PRIVATE
    -O3 -Wall -march=native -fcx-limited-range -fno-exceptions -fPIC
)

target_compile_definitions(S4 PUBLIC HAVE_BLAS)

if(S4_EIGEN_BACKEND STREQUAL "MEKIL")
    if(NOT TARGET infrastructure::uca)
        message(FATAL_ERROR "S4 MEKIL backend requires infrastructure::uca from parent project")
    endif()
    target_compile_definitions(S4 PUBLIC S4_EIGEN_BACKEND_MEKIL=1)
    target_link_libraries(S4 PUBLIC infrastructure::uca)
elseif(S4_EIGEN_BACKEND STREQUAL "RNP")
    target_compile_definitions(S4 PUBLIC S4_EIGEN_BACKEND_RNP=1 HAVE_LAPACK)
    if(TARGET infrastructure::uca)
        target_link_libraries(S4 PUBLIC infrastructure::uca)
    else()
        find_package(MKL CONFIG QUIET)
        if(MKL_FOUND)
            target_link_libraries(S4 PUBLIC MKL::MKL)
        else()
            target_link_libraries(S4 PUBLIC lapack blas)
        endif()
    endif()
else()
    message(FATAL_ERROR "Unknown S4_EIGEN_BACKEND=${S4_EIGEN_BACKEND}")
endif()

if(DEFINED S4_OUTPUT_DIR)
    set(_s4_archive_out "${S4_OUTPUT_DIR}")
else()
    set(_s4_archive_out "${CMAKE_BINARY_DIR}")
endif()

set_target_properties(S4 PROPERTIES
    ARCHIVE_OUTPUT_DIRECTORY "${_s4_archive_out}"
    OUTPUT_NAME "S4"
)

if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/tests/CMakeLists.txt")
    add_subdirectory(tests)
endif()
