#ifndef _RNP_TBLAS_MEKIL_H_
#define _RNP_TBLAS_MEKIL_H_

// MEKIL: MultMM/MultMV specializations via mekil::lapack (no TBLAS_ext Fortran UND).
// Matches the call shapes previously accelerated by TBLAS_ext under RNP+MKL.

#include <complex>
#include <mekil/lapack_eigensystem.hpp>

namespace RNP {
namespace TBLAS {

template <>
template <>
inline MultMV<'N'>::MultMV(size_t m, size_t n, const std::complex<double> &alpha,
                           const std::complex<double> *a, size_t lda, const std::complex<double> *x,
                           size_t incx, const std::complex<double> &beta, std::complex<double> *y,
                           size_t incy) {
	mekil::lapack::gemv<double>('N', m, n, alpha, a, lda, x, incx, beta, y, incy);
}

template <>
template <>
inline MultMV<'N'>::MultMV(size_t m, size_t n, const double &alpha, const std::complex<double> *a,
                           size_t lda, const std::complex<double> *x, size_t incx, const double &beta,
                           std::complex<double> *y, size_t incy) {
	mekil::lapack::gemv<double>('N', m, n, std::complex<double>(alpha), a, lda, x, incx,
	                            std::complex<double>(beta), y, incy);
}

template <>
template <>
inline MultMM<'N', 'N'>::MultMM(size_t m, size_t n, size_t k, const double &alpha,
                                const std::complex<double> *a, size_t lda,
                                const std::complex<double> *b, size_t ldb, const double &beta,
                                std::complex<double> *c, size_t ldc) {
	mekil::lapack::gemm<double>('N', 'N', m, n, k, std::complex<double>(alpha), a, lda, b, ldb,
	                            std::complex<double>(beta), c, ldc);
}

template <>
template <>
inline MultMM<'N', 'N'>::MultMM(size_t m, size_t n, size_t k, const std::complex<double> &alpha,
                                const std::complex<double> *a, size_t lda,
                                const std::complex<double> *b, size_t ldb,
                                const std::complex<double> &beta, std::complex<double> *c,
                                size_t ldc) {
	mekil::lapack::gemm<double>('N', 'N', m, n, k, alpha, a, lda, b, ldb, beta, c, ldc);
}

}  // namespace TBLAS
}  // namespace RNP

#endif  // _RNP_TBLAS_MEKIL_H_
