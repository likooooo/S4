/* Minimal POSIX getopt for MSVC. Used only by S4lua on Windows. */
#include "getopt.h"

#include <stdio.h>
#include <string.h>

char *optarg = NULL;
int optind = 1;
int opterr = 1;
int optopt = 0;

int getopt(int argc, char * const argv[], const char *optstring) {
	static char *next = NULL;
	char c;
	const char *cp;

	if (optind >= argc || argv[optind] == NULL || argv[optind][0] != '-' || argv[optind][1] == '\0')
		return -1;
	if (strcmp(argv[optind], "--") == 0) {
		++optind;
		return -1;
	}

	if (next == NULL || *next == '\0')
		next = argv[optind] + 1;
	c = *next++;
	optopt = (unsigned char)c;
	cp = strchr(optstring, c);
	if (cp == NULL || c == ':') {
		if (opterr)
			fprintf(stderr, "Unknown option -%c.\n", c);
		if (*next == '\0')
			++optind;
		return '?';
	}
	if (cp[1] == ':') {
		if (*next != '\0') {
			optarg = next;
			next = NULL;
			++optind;
		} else if (++optind >= argc) {
			if (opterr)
				fprintf(stderr, "Option -%c requires an argument.\n", c);
			optarg = NULL;
			return (optstring[0] == ':') ? ':' : '?';
		} else {
			optarg = argv[optind++];
			next = NULL;
		}
	} else {
		optarg = NULL;
		if (*next == '\0') {
			next = NULL;
			++optind;
		}
	}
	return (unsigned char)c;
}
