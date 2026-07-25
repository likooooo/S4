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
	library_dirs = ['build'],
	extra_link_args = [
		'build/libS4.a',
		'/usr/lib/x86_64-linux-gnu/libblas.so.3',
		'/usr/lib/x86_64-linux-gnu/liblapack.so.3'
	]
)

setup(name = 'S4',
	version = '1.1',
	description = 'Stanford Stratified Structure Solver (S4): Fourier Modal Method',
	ext_modules = [S4module]
)
