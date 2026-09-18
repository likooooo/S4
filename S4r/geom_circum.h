#ifndef GEOM_CIRCUM_H_INCLUDED
#define GEOM_CIRCUM_H_INCLUDED

void geom_circum_tri2d(
	const double a[2],
	const double b[2],
	const double c[2],
	double circumcenter[2],
	double *xi,
	double *eta
);

double geom_circum_fit2d(
	int n,
	const double *p, /* length 2*n of (x,y) pairs */
	double c[2], double *r
);

#endif // GEOM_CIRCUM_H_INCLUDED
