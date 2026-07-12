#!/bin/bash

OBJDIR="$1"
LIBFILE="$2"
BLAS_LIB="${BLAS_LIB:-/usr/lib/x86_64-linux-gnu/libblas.so.3}"
LAPACK_LIB="${LAPACK_LIB:-/usr/lib/x86_64-linux-gnu/liblapack.so.3}"

cat <<SETUPPY > setup.py
from distutils.core import setup, Extension

S4module = Extension('S4',
	sources = [
		'S4/main_python.c'
	],
	libraries = [
		'S4',
		'stdc++',
		'gfortran'
	],
	library_dirs = ['$OBJDIR'],
	extra_link_args = [
		'$LIBFILE',
		'$BLAS_LIB',
		'$LAPACK_LIB'
	]
)

setup(name = 'S4',
	version = '1.1',
	description = 'Stanford Stratified Structure Solver (S4): Fourier Modal Method',
	ext_modules = [S4module]
)
SETUPPY
