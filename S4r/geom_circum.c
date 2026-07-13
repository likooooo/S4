#include <math.h>
#include "geom_circum.h"

void geom_circum_tri2d(
	const double a[2],
	const double b[2],
	const double c[2],
	double circumcenter[2],
	double *xi,
	double *eta
){
  double xba, yba, xca, yca;
  double balength, calength;
  double denominator;
  double xcirca, ycirca;

  xba = b[0] - a[0];
  yba = b[1] - a[1];
  xca = c[0] - a[0];
  yca = c[1] - a[1];
  balength = xba * xba + yba * yba;
  calength = xca * xca + yca * yca;

  denominator = 0.5 / (xba * yca - yba * xca);

  xcirca = (yca * balength - yba * calength) * denominator;
  ycirca = (xba * calength - xca * balength) * denominator;
  circumcenter[0] = a[0]+xcirca;
  circumcenter[1] = a[1]+ycirca;

  if (xi != (double *) NULL) {
    *xi = (xcirca * yca - ycirca * xca) * (2.0 * denominator);
    *eta = (ycirca * xba - xcirca * yba) * (2.0 * denominator);
  }
}

double geom_circum_fit2d(
	int n,
	const double *a,
	double c[2], double *r
){
	int i;
	double m[2] = { 0,0 };
	double BB[3] = { 0,0,0 };
	double b[2] = { 0,0 };
	const double in = 1./(double)n;
	*r = 0;
	for(i = 0; i < n; ++i){
		m[0] += a[2*i+0];
		m[1] += a[2*i+1];
	}
	m[0] *= in; m[1] *= in;
	for(i = 0; i < n; ++i){
		const double t[2] = { a[2*i+0]-m[0], a[2*i+1]-m[1] };
		const double bi = t[0]*t[0] + t[1]*t[1];
		const double Bi0 = 2*t[0];
		const double Bi1 = 2*t[1];
		b[0] += Bi0 * bi;
		b[1] += Bi1 * bi;
		*r += bi;
		BB[0] += Bi0*Bi0;
		BB[1] += Bi0*Bi1;
		BB[2] += Bi1*Bi1;
	}
	*r *= in;

	{
		double idet = 1. / (BB[0]*BB[2] - BB[1]*BB[1]);
		double v[2] = {
			idet * (BB[2] * b[0] - BB[1] * b[1]),
			idet * (BB[0] * b[1] - BB[1] * b[0])
		};
		*r = sqrt(*r + v[0]*v[0] + v[1]*v[1]);
		c[0] = m[0]+v[0]; c[1] = m[1]+v[1];
		return sqrt(hypot(
			BB[0]*v[0] + BB[1]*v[1] - b[0],
			BB[1]*v[0] + BB[2]*v[1] - b[1]
		)) * in;
	}
}
