#ifndef _RNP_LINEAR_SOLVE_MEKIL_H_
#define _RNP_LINEAR_SOLVE_MEKIL_H_

// MEKIL: LinearSolve<'N'> for complex double via mekil::lapack (getrf+getrs).
// Replaces HAVE_LAPACK → zgesv_ without Fortran UND or lp64 int pivots.

#include "LinearSolve.h"
#include <cstdlib>
#include <mekil/lapack_eigensystem.hpp>

namespace RNP {

template <>
template <>
inline LinearSolve<'N'>::LinearSolve(size_t n, size_t nRHS, std::complex<double> *a, size_t lda,
                                     std::complex<double> *b, size_t ldb, int *info, size_t *pivots) {
	if (NULL != info) *info = 0;
	if (0 == n || nRHS == 0) return;

	size_t *ipiv = pivots;
	if (NULL == pivots) ipiv = (size_t *)malloc(sizeof(size_t) * n);

	int ret = mekil::lapack::lu_factor<double>(n, n, a, lda, ipiv);
	if (ret == 0) ret = mekil::lapack::lu_solve<double>('N', n, nRHS, a, lda, ipiv, b, ldb);

	if (NULL == pivots) free(ipiv);
	if (NULL != info) *info = ret;
}

}  // namespace RNP

#endif  // _RNP_LINEAR_SOLVE_MEKIL_H_
