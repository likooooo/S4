#include "s4_bridge.h"

extern "C" {
#include "gsel.h"
}

#include <cmath>
#include <cstring>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace {

int lattice_reciprocate(const double Lr[4], double Lk[4]) {
    const double det = Lr[0] * Lr[3] - Lr[1] * Lr[2];
    if (det == 0.0) {
        if (Lr[2] != 0.0 || Lr[3] != 0.0) {
            return 1;
        }
        const double d = std::hypot(Lr[0], Lr[1]);
        if (d == 0.0) {
            return 2;
        }
        const double inv_d2 = 1.0 / (d * d);
        Lk[0] = Lr[0] * inv_d2;
        Lk[1] = Lr[1] * inv_d2;
        Lk[2] = 0.0;
        Lk[3] = 0.0;
        return 0;
    }
    const double inv_det = 1.0 / det;
    Lk[0] = inv_det * Lr[3];
    Lk[1] = -inv_det * Lr[2];
    Lk[2] = -inv_det * Lr[1];
    Lk[3] = inv_det * Lr[0];
    return 0;
}

void g_select_1d_lattice(unsigned& nG, int* G_out) {
    if (nG <= 1) {
        nG = 1;
        G_out[0] = 0;
        G_out[1] = 0;
        return;
    }
    const unsigned remaining = (nG - 1) / 2;
    nG = 1 + 2 * remaining;
    G_out[0] = 0;
    G_out[1] = 0;
    for (unsigned i = 0; i < remaining; ++i) {
        G_out[2 + 4 * i + 0] = static_cast<int>(i + 1);
        G_out[2 + 4 * i + 1] = 0;
        G_out[2 + 4 * i + 2] = -static_cast<int>(i + 1);
        G_out[2 + 4 * i + 3] = 0;
    }
}

int g_select_circular(unsigned& nG, const double Lk[4], int* G_out) {
    if (nG <= 1) {
        nG = 1;
        G_out[0] = 0;
        G_out[1] = 0;
        return 0;
    }
    unsigned nG_in = nG;
    if (G_select(0, &nG_in, Lk, G_out) != 0) {
        return -1;
    }
    nG = nG_in;
    return 0;
}

void compute_kx_ky(const double Lk[4], unsigned nG, const int* G, double k_incident_x,
                   double k_incident_y, double* kx_out, double* ky_out) {
    const double two_pi = 2.0 * M_PI;
    for (unsigned i = 0; i < nG; ++i) {
        const int mx = G[2 * i];
        const int my = G[2 * i + 1];
        kx_out[i] = k_incident_x + two_pi * (mx * Lk[0] + my * Lk[2]);
        ky_out[i] = k_incident_y + two_pi * (mx * Lk[1] + my * Lk[3]);
    }
}

}  // namespace

extern "C" int s4_bridge_build_glist(const double Lr[4], unsigned n_G, double k_incident_x,
                                     double k_incident_y, double Lk_out[4], unsigned* n_G_out,
                                     int* G_out, double* kx_out, double* ky_out) {
    if (Lr == nullptr || Lk_out == nullptr || n_G_out == nullptr || G_out == nullptr ||
        kx_out == nullptr || ky_out == nullptr) {
        return -1;
    }

    if (lattice_reciprocate(Lr, Lk_out) != 0) {
        return -2;
    }

    unsigned nG = n_G;
    if (nG <= 1) {
        *n_G_out = 1;
        G_out[0] = 0;
        G_out[1] = 0;
        kx_out[0] = k_incident_x;
        ky_out[0] = k_incident_y;
        return 0;
    }

    const bool is_2d = (Lr[2] != 0.0 || Lr[3] != 0.0);
    if (is_2d) {
        if (g_select_circular(nG, Lk_out, G_out) != 0) {
            return -3;
        }
    } else {
        g_select_1d_lattice(nG, G_out);
    }

    *n_G_out = nG;
    compute_kx_ky(Lk_out, nG, G_out, k_incident_x, k_incident_y, kx_out, ky_out);
    return 0;
}
