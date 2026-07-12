#pragma once

#include <array>
#include <cmath>
#include <cstddef>
#include <string>
#include <vector>

namespace s4_test {

constexpr double k_pi = 3.14159265358979323846;
constexpr double k_wl_um = 0.0135;
constexpr double k_period_um = 0.032;
constexpr double k_pattern_depth_um = 0.020;
constexpr std::array<std::size_t, 2> k_field_grid_nxy = {16, 16};

enum class pattern_shape_kind {
    tri,
    rect,
    circle,
    ellipse_xy,
    ellipse_yx,
    donut,
    multi,
    grating_interval,
};

struct pattern_case_spec {
    const char* name = nullptr;
    pattern_shape_kind shape = pattern_shape_kind::tri;
    unsigned n_G = 9;
    double phi_deg = 20.0;
    double theta_deg = 0.0;
    char pol = 'p';
    std::size_t probe_layer_index = 2;
    double probe_z_um = 0.004;
    bool lattice_1d = false;
    bool hi_contrast_substrate = false;
    bool rect_offset_rot = false;
    double rect_center_x = 0.0;
    double rect_center_y = 0.0;
    double rect_angle_deg = 0.0;
};

inline const char* probe_layer_name(std::size_t layer_index) {
    static constexpr const char* k_names[] = {"AirAbove", "Triangle", "Film1", "Film2", "Film3",
                                              "Substrate"};
    return layer_index < 6 ? k_names[layer_index] : "Film1";
}

inline std::vector<pattern_case_spec> all_pattern_case_specs() {
    const pattern_case_spec defaults{};
    auto spec = [&](const char* name, pattern_shape_kind shape) {
        pattern_case_spec s = defaults;
        s.name = name;
        s.shape = shape;
        return s;
    };
    auto with = [&](pattern_case_spec s) { return s; };

    std::vector<pattern_case_spec> out;
    out.push_back(spec("pat_tri_nG9_phi20", pattern_shape_kind::tri));
    out.push_back(spec("pat_rect_nG9_phi20", pattern_shape_kind::rect));
    out.push_back(spec("pat_circle_nG9_phi20", pattern_shape_kind::circle));
    out.push_back(spec("pat_ellipse_xy_nG9", pattern_shape_kind::ellipse_xy));
    out.push_back(spec("pat_ellipse_yx_nG9", pattern_shape_kind::ellipse_yx));
    out.push_back(spec("pat_donut_nG9", pattern_shape_kind::donut));
    out.push_back(spec("pat_multi_nG9", pattern_shape_kind::multi));
    {
        auto s = spec("grating_1d_rect_nG9", pattern_shape_kind::grating_interval);
        s.lattice_1d = true;
        out.push_back(s);
    }
    out.push_back(with({.name = "pat_tri_nG1", .shape = pattern_shape_kind::tri, .n_G = 1}));
    out.push_back(with({.name = "pat_tri_nG9", .shape = pattern_shape_kind::tri}));
    out.push_back(with({.name = "pat_tri_phi0_nG9", .shape = pattern_shape_kind::tri, .phi_deg = 0.0}));
    out.push_back(
        with({.name = "pat_tri_phi45_nG9", .shape = pattern_shape_kind::tri, .phi_deg = 45.0}));
    out.push_back(with({.name = "pat_tri_theta15_nG9",
                        .shape = pattern_shape_kind::tri,
                        .theta_deg = 15.0}));
    out.push_back(with({.name = "pat_tri_theta25_nG9",
                        .shape = pattern_shape_kind::tri,
                        .theta_deg = 25.0}));
    out.push_back(with({.name = "pat_tri_probe_pattern_nG9",
                        .shape = pattern_shape_kind::tri,
                        .probe_layer_index = 1}));
    out.push_back(with({.name = "pat_tri_probe_substrate_nG9",
                        .shape = pattern_shape_kind::tri,
                        .probe_layer_index = 4,
                        .probe_z_um = 0.001}));
    out.push_back(with({.name = "pat_tri_spol_nG9", .shape = pattern_shape_kind::tri, .pol = 's'}));
    out.push_back(
        with({.name = "pat_circle_spol_nG9", .shape = pattern_shape_kind::circle, .pol = 's'}));
    {
        auto s = spec("pat_rect_hi_contrast_nG9", pattern_shape_kind::rect);
        s.hi_contrast_substrate = true;
        out.push_back(s);
    }
    {
        auto s = spec("pat_rect_offset_rot_nG9", pattern_shape_kind::rect);
        s.rect_offset_rot = true;
        s.rect_center_x = 0.003;
        s.rect_center_y = -0.002;
        s.rect_angle_deg = 15.0;
        out.push_back(s);
    }
    return out;
}

}  // namespace s4_test

#ifndef S4_TEST_COMMON_CATALOG_ONLY

#include "s4_dump.hpp"

#include <S4.h>

#include <complex>
#include <cstdio>
#include <stdexcept>

namespace s4_test {

using cT = std::complex<double>;

struct field_probe {
    std::size_t layer_index = 0;
    double z_offset = 0;
    const char* s4_layer_name = "Film1";
};

struct stack_case {
    double phi_rad = 0;
    double theta_rad = 0;
    unsigned n_G = 1;
    bool patterned = false;
    field_probe probe{};
    double period_um = k_period_um;
    double wl_um = k_wl_um;
    bool lattice_1d = false;
    char pol = 'p';
    pattern_shape_kind shape = pattern_shape_kind::tri;
    bool hi_contrast_substrate = false;
    double shape_center[2] = {0.0, 0.0};
    double shape_angle_rad = 0.0;
};

inline stack_case stack_case_from_spec(const pattern_case_spec& spec) {
    stack_case sc;
    sc.phi_rad = spec.phi_deg * k_pi / 180.0;
    sc.theta_rad = spec.theta_deg * k_pi / 180.0;
    sc.n_G = spec.n_G;
    sc.patterned = true;
    sc.probe.layer_index = spec.probe_layer_index;
    sc.probe.z_offset = spec.probe_z_um;
    sc.probe.s4_layer_name = probe_layer_name(spec.probe_layer_index);
    sc.period_um = k_period_um;
    sc.wl_um = k_wl_um;
    sc.lattice_1d = spec.lattice_1d;
    sc.pol = spec.pol;
    sc.shape = spec.shape;
    sc.hi_contrast_substrate = spec.hi_contrast_substrate;
    if (spec.rect_offset_rot) {
        sc.shape_center[0] = spec.rect_center_x;
        sc.shape_center[1] = spec.rect_center_y;
        sc.shape_angle_rad = spec.rect_angle_deg * k_pi / 180.0;
    }
    return sc;
}

inline void apply_pattern_shape(S4_Simulation* S, S4_LayerID layer_id, const stack_case& sc) {
    const S4_MaterialID pat_mid = S4_Simulation_GetMaterialByName(S, "PatternMat");
    const S4_MaterialID air_mid = S4_Simulation_GetMaterialByName(S, "Air");
    const S4_MaterialID pat_hi_mid = S4_Simulation_GetMaterialByName(S, "PatternMatHi");
    S4_real center[2] = {static_cast<S4_real>(sc.shape_center[0]),
                          static_cast<S4_real>(sc.shape_center[1])};
    S4_real angle_frac[1] = {static_cast<S4_real>(sc.shape_angle_rad / (2.0 * k_pi))};

    auto set_rect = [&](double hw0, double hw1) {
        S4_real hw[2] = {static_cast<S4_real>(hw0), static_cast<S4_real>(hw1)};
        if (sc.lattice_1d) {
            hw[1] = 0;
            S4_Layer_SetRegionHalfwidths(S, layer_id, pat_mid, S4_REGION_TYPE_INTERVAL, hw, center,
                                         angle_frac);
        } else {
            S4_Layer_SetRegionHalfwidths(S, layer_id, pat_mid, S4_REGION_TYPE_RECTANGLE, hw, center,
                                         angle_frac);
        }
    };
    auto set_circle = [&](double radius, S4_MaterialID mid) {
        S4_real hw[2] = {static_cast<S4_real>(radius), 0};
        if (sc.lattice_1d) {
            S4_Layer_SetRegionHalfwidths(S, layer_id, mid, S4_REGION_TYPE_INTERVAL, hw, center,
                                         angle_frac);
        } else {
            S4_Layer_SetRegionHalfwidths(S, layer_id, mid, S4_REGION_TYPE_CIRCLE, hw, center,
                                         angle_frac);
        }
    };
    auto set_ellipse = [&](double hw0, double hw1) {
        S4_real hw[2] = {static_cast<S4_real>(hw0), static_cast<S4_real>(hw1)};
        S4_Layer_SetRegionHalfwidths(S, layer_id, pat_mid, S4_REGION_TYPE_ELLIPSE, hw, center,
                                     angle_frac);
    };

    switch (sc.shape) {
    case pattern_shape_kind::rect:
        set_rect(0.008, 0.005);
        break;
    case pattern_shape_kind::circle:
        set_circle(0.007, pat_mid);
        break;
    case pattern_shape_kind::ellipse_xy:
        set_ellipse(0.008, 0.004);
        break;
    case pattern_shape_kind::ellipse_yx:
        set_ellipse(0.004, 0.008);
        break;
    case pattern_shape_kind::donut:
        set_circle(0.008, pat_mid);
        set_circle(0.004, air_mid);
        break;
    case pattern_shape_kind::multi: {
        S4_real c0[2] = {-0.003, 0.0};
        S4_real c1[2] = {0.004, 0.0};
        S4_real a0[1] = {0.0};
        S4_real hw_rect[2] = {0.007, 0.004};
        S4_Layer_SetRegionHalfwidths(S, layer_id, pat_mid, S4_REGION_TYPE_RECTANGLE, hw_rect, c0,
                                     a0);
        S4_real hw_circle[2] = {0.004, 0.0};
        S4_Layer_SetRegionHalfwidths(S, layer_id, pat_hi_mid, S4_REGION_TYPE_CIRCLE, hw_circle, c1,
                                     a0);
        break;
    }
    case pattern_shape_kind::grating_interval:
        set_rect(0.006, 0.002);
        break;
    case pattern_shape_kind::tri:
    default: {
        S4_real verts[6] = {-0.006, -0.004, 0.008, -0.004, 0.0, 0.007};
        S4_Layer_SetRegionVertices(S, layer_id, pat_mid, S4_REGION_TYPE_POLYGON, 3, verts, center,
                                   angle_frac);
        break;
    }
    }
}

struct case_result {
    std::vector<cT> smatrix;
    std::vector<cT> efield;
    std::vector<cT> hfield;
};

inline void set_aniso_material(S4_Simulation* S,
                               const char* name,
                               cT a,
                               cT b,
                               cT c,
                               cT d,
                               cT e) {
    S4_real eps[10] = {static_cast<S4_real>(a.real()), static_cast<S4_real>(a.imag()),
                       static_cast<S4_real>(b.real()), static_cast<S4_real>(b.imag()),
                       static_cast<S4_real>(c.real()), static_cast<S4_real>(c.imag()),
                       static_cast<S4_real>(d.real()), static_cast<S4_real>(d.imag()),
                       static_cast<S4_real>(e.real()), static_cast<S4_real>(e.imag())};
    S4_Simulation_SetMaterial(S, -1, name, S4_MATERIAL_TYPE_XYTENSOR_COMPLEX, eps);
}

inline void set_scalar_material(S4_Simulation* S, const char* name, cT eps) {
    S4_real v[2] = {static_cast<S4_real>(eps.real()), static_cast<S4_real>(eps.imag())};
    S4_Simulation_SetMaterial(S, -1, name, S4_MATERIAL_TYPE_SCALAR_COMPLEX, v);
}

inline S4_Simulation* build_pattern_stack_simulation(const stack_case& sc) {
    S4_real Lr[4] = {static_cast<S4_real>(sc.period_um), 0, 0,
                     static_cast<S4_real>(sc.lattice_1d ? 0 : sc.period_um)};
    S4_Simulation* S = S4_Simulation_New(Lr, sc.n_G, nullptr);
    if (S == nullptr) {
        throw std::runtime_error("S4_Simulation_New failed");
    }
    set_scalar_material(S, "Air", cT(1));
    set_scalar_material(S, "PatternMat", cT(0.9, 0.1));
    set_scalar_material(S, "PatternMatHi", cT(2.0, 0));
    set_aniso_material(S, "Film1", cT(2.1, 0.05), cT(0.03), cT(0.03), cT(2.0), cT(2.3));
    set_aniso_material(S, "Film2", cT(1.8), cT(0.0), cT(0.0), cT(1.9), cT(2.0));
    set_aniso_material(S, "Film3", cT(2.5, -0.02), cT(0.01), cT(0.01), cT(2.4), cT(2.6));
    if (sc.hi_contrast_substrate) {
        set_scalar_material(S, "Substrate", cT(1.5, 0));
    } else {
        set_scalar_material(S, "Substrate", cT(0.92, 0.08));
    }

    struct layer_spec {
        const char* name;
        S4_real thickness;
        const char* material;
        bool pattern;
    };
    const layer_spec stack[] = {{"AirAbove", 0, "Air", false},
                                {"Triangle", static_cast<S4_real>(k_pattern_depth_um), "Air", true},
                                {"Film1", 0.008, "Film1", false},
                                {"Film2", 0.006, "Film2", false},
                                {"Film3", 0.005, "Film3", false},
                                {"Substrate", 0, "Substrate", false}};
    for (const layer_spec& spec : stack) {
        S4_Simulation_SetLayer(S, -1, spec.name, &spec.thickness, -1,
                               S4_Simulation_GetMaterialByName(S, spec.material));
        if (spec.pattern) {
            apply_pattern_shape(S, S4_Simulation_GetLayerByName(S, spec.name), sc);
        }
    }

    const S4_real angle[2] = {static_cast<S4_real>(sc.theta_rad), static_cast<S4_real>(sc.phi_rad)};
    const S4_real pol_s[2] = {sc.pol == 's' ? 1.0 : 0.0, 0.0};
    const S4_real pol_p[2] = {sc.pol == 'p' ? 1.0 : 0.0, 0.0};
    if (Simulation_MakeExcitationPlanewave(S, angle, pol_s, pol_p, 0) != 0) {
        S4_Simulation_Destroy(S);
        throw std::runtime_error("Simulation_MakeExcitationPlanewave failed");
    }
    const S4_real freq[2] = {1.0 / static_cast<S4_real>(sc.wl_um), 0.0};
    if (S4_Simulation_SetFrequency(S, freq) != 0) {
        S4_Simulation_Destroy(S);
        throw std::runtime_error("S4_Simulation_SetFrequency failed");
    }
    return S;
}

inline std::vector<cT> fetch_smatrix(S4_Simulation* S) {
    const unsigned nG = static_cast<unsigned>(S->n_G);
    const std::size_t dim = 4 * static_cast<std::size_t>(nG);
    const std::size_t n_elem = dim * dim;
    std::vector<double> buf(2 * n_elem, 0.0);
    if (Simulation_GetSMatrixToBuffer(S, 0, -1, buf.data()) != 0) {
        throw std::runtime_error("Simulation_GetSMatrixToBuffer failed");
    }
    return std::vector<cT>(reinterpret_cast<cT*>(buf.data()),
                           reinterpret_cast<cT*>(buf.data()) + n_elem);
}

inline double absolute_z_for_probe(const stack_case& sc, double z_probe) {
    double z_abs = 0;
    static constexpr double k_depths[] = {0.0, k_pattern_depth_um, 0.008, 0.006, 0.005, 0.0};
    for (std::size_t li = 0; li < sc.probe.layer_index && li < 6; ++li) {
        z_abs += k_depths[li];
    }
    return z_abs + z_probe;
}

inline void fetch_field_plane(S4_Simulation* S,
                              double z_abs,
                              const std::size_t nxy[2],
                              std::vector<cT>& efield,
                              std::vector<cT>& hfield) {
    const std::size_t grid_n = nxy[0] * nxy[1];
    std::vector<double> E(grid_n * 6, 0.0);
    std::vector<double> H(grid_n * 6, 0.0);
    int snxy[2] = {static_cast<int>(nxy[0]), static_cast<int>(nxy[1])};
    if (Simulation_GetFieldPlane(S, snxy, z_abs, E.data(), H.data()) != 0) {
        throw std::runtime_error("Simulation_GetFieldPlane failed");
    }
    efield.resize(3 * grid_n);
    hfield.resize(3 * grid_n);
    for (std::size_t i = 0; i < grid_n; ++i) {
        for (int c = 0; c < 3; ++c) {
            efield[3 * i + static_cast<std::size_t>(c)] =
                cT(E[2 * (3 * i + c)], E[2 * (3 * i + c) + 1]);
            hfield[3 * i + static_cast<std::size_t>(c)] =
                cT(H[2 * (3 * i + c)], H[2 * (3 * i + c) + 1]);
        }
    }
}

inline case_result run_stack_case(const stack_case& sc) {
    S4_Simulation* S = build_pattern_stack_simulation(sc);
    case_result out;
    out.smatrix = fetch_smatrix(S);
    const double z_abs = absolute_z_for_probe(sc, sc.probe.z_offset);
    fetch_field_plane(S, z_abs, k_field_grid_nxy.data(), out.efield, out.hfield);
    S4_Simulation_Destroy(S);
    return out;
}

inline void write_case_result(s4_dump::writer& w, const std::string& name, const case_result& r) {
    w.begin_case(name);
    const std::size_t n = static_cast<std::size_t>(std::sqrt(r.smatrix.size()));
    w.write_block_c128("smatrix", r.smatrix, {n, n});
    if (!r.efield.empty()) {
        w.write_block_c128("field_E", r.efield, {k_field_grid_nxy[0], k_field_grid_nxy[1], 3});
    }
    if (!r.hfield.empty()) {
        w.write_block_c128("field_H", r.hfield, {k_field_grid_nxy[0], k_field_grid_nxy[1], 3});
    }
}

inline void register_all_cases(s4_dump::writer& w, const char* filter) {
    for (const pattern_case_spec& spec : all_pattern_case_specs()) {
        if (filter != nullptr && std::string(filter) != spec.name) {
            continue;
        }
        write_case_result(w, spec.name, run_stack_case(stack_case_from_spec(spec)));
    }
}

}  // namespace s4_test

#endif  // S4_TEST_COMMON_CATALOG_ONLY
