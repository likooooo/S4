/* Minimal POSIX getopt for MSVC (public-domain style). Used only by S4lua on Windows. */
#ifndef S4_WIN_GETOPT_H
#define S4_WIN_GETOPT_H

#ifdef __cplusplus
extern "C" {
#endif

extern char *optarg;
extern int optind, opterr, optopt;

int getopt(int argc, char * const argv[], const char *optstring);

#ifdef __cplusplus
}
#endif

#endif
