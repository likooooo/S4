#ifndef S4_EIGEN_BACKEND_HPP_
#define S4_EIGEN_BACKEND_HPP_

#include <complex>
#include <cstddef>

#if defined(S4_EIGEN_BACKEND_MEKIL)
# include <mekil/lapack_eigensystem.hpp>
#elif defined(S4_EIGEN_BACKEND_RNP)
# include <Eigensystems_lapack.h>
#else
# include <Eigensystems.h>
#endif

namespace s4_eigen {

inline int Eigensystem(std::size_t n,
                       std::complex<double>* a,
                       std::size_t lda,
                       std::complex<double>* eval,
                       std::complex<double>* vl,
                       std::size_t ldvl,
                       std::complex<double>* vr,
                       std::size_t ldvr,
                       std::complex<double>* work,
                       double* rwork,
                       std::size_t lwork) {
#if defined(S4_EIGEN_BACKEND_MEKIL)
    return mekil::lapack::eigensystem<double>(n, a, lda, eval, vl, ldvl, vr, ldvr, work, rwork, lwork);
#elif defined(S4_EIGEN_BACKEND_RNP)
    return RNP::Eigensystem(n, a, lda, eval, vl, ldvl, vr, ldvr, work, rwork, lwork);
#else
    return RNP::Eigensystem(n, a, lda, eval, vl, ldvl, vr, ldvr, work, rwork, lwork);
#endif
}

inline int Eigensystem_real(std::size_t n,
                            double* a,
                            std::size_t lda,
                            std::complex<double>* eval,
                            std::complex<double>* vl,
                            std::size_t ldvl,
                            std::complex<double>* vr,
                            std::size_t ldvr,
                            double* work,
                            std::size_t lwork) {
#if defined(S4_EIGEN_BACKEND_MEKIL)
    return mekil::lapack::eigensystem_real<double>(n, a, lda, eval, vl, ldvl, vr, ldvr, work, lwork);
#elif defined(S4_EIGEN_BACKEND_RNP)
    return RNP::Eigensystem_real(n, a, lda, eval, vl, ldvl, vr, ldvr, work, lwork);
#else
    (void)n;
    (void)a;
    (void)lda;
    (void)eval;
    (void)vl;
    (void)ldvl;
    (void)vr;
    (void)ldvr;
    (void)work;
    (void)lwork;
    return -1;
#endif
}

}  // namespace s4_eigen

#if defined(S4_EIGEN_BACKEND_MEKIL) || defined(S4_EIGEN_BACKEND_RNP)
# define S4_HAVE_LAPACK_EIGEN 1
#endif

#if defined(S4_HAVE_LAPACK_EIGEN) && !defined(S4_EIGEN_BACKEND_RNP)
# if defined(MEKIL_HAVE_MKL) && MEKIL_HAVE_MKL
#  ifdef MKL_ILP64
typedef long long int integer;
#  else
typedef int integer;
#  endif
# else
typedef int integer;
# endif
#endif

#endif  // S4_EIGEN_BACKEND_HPP_
