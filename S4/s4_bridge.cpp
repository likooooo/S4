#include "s4_bridge.h"

extern "C" {
#include "pattern/pattern.h"
}

#include <cmath>
#include <cstdlib>
#include <cstring>
#include <vector>

namespace {

shape make_internal_shape(const S4BridgeShape& sh) {
    shape s{};
    s.center[0] = sh.center[0];
    s.center[1] = sh.center[1];
    s.angle = sh.angle;
    s.tag = sh.material_id;

    switch (sh.kind) {
    case S4_BRIDGE_CIRCLE:
        s.type = CIRCLE;
        s.vtab.circle.radius = sh.geom.radius;
        break;
    case S4_BRIDGE_ELLIPSE:
        s.type = ELLIPSE;
        s.vtab.ellipse.halfwidth[0] = sh.geom.halfwidth[0];
        s.vtab.ellipse.halfwidth[1] = sh.geom.halfwidth[1];
        break;
    case S4_BRIDGE_RECT:
        s.type = RECTANGLE;
        s.vtab.rectangle.halfwidth[0] = sh.geom.halfwidth[0];
        s.vtab.rectangle.halfwidth[1] = sh.geom.halfwidth[1];
        break;
    case S4_BRIDGE_POLYGON:
        s.type = POLYGON;
        s.vtab.polygon.n_vertices = sh.geom.polygon.n_vertices;
        s.vtab.polygon.vertex = static_cast<double*>(
            malloc(sizeof(double) * 2 * static_cast<std::size_t>(sh.geom.polygon.n_vertices)));
        if (s.vtab.polygon.vertex != nullptr) {
            std::memcpy(s.vtab.polygon.vertex, sh.geom.polygon.xy,
                        sizeof(double) * 2 * static_cast<std::size_t>(sh.geom.polygon.n_vertices));
        }
        break;
    default:
        s.type = CIRCLE;
        break;
    }
    return s;
}

void free_internal_shape(shape& s) {
    if (s.type == POLYGON && s.vtab.polygon.vertex != nullptr) {
        free(s.vtab.polygon.vertex);
        s.vtab.polygon.vertex = nullptr;
    }
}

}  // namespace

extern "C" int s4_bridge_generate_flow_field(const double Lr[4], int n_shapes,
                                             const S4BridgeShape* shapes, int nu, int nv,
                                             double* vfield) {
    if (nu <= 0 || nv <= 0 || vfield == nullptr || Lr == nullptr) {
        return -1;
    }

    const bool is_2d = (Lr[2] != 0.0 || Lr[3] != 0.0);
    if (!is_2d) {
        double nv_vec[2] = {-Lr[1], Lr[0]};
        const double nva = std::hypot(nv_vec[0], nv_vec[1]);
        if (nva > 0.0) {
            nv_vec[0] /= nva;
            nv_vec[1] /= nva;
        }
        for (int j = 0; j < nv; ++j) {
            for (int i = 0; i < nu; ++i) {
                vfield[2 * (i + j * nu) + 0] = nv_vec[0];
                vfield[2 * (i + j * nu) + 1] = nv_vec[1];
            }
        }
        return 0;
    }

    if (n_shapes <= 0 || shapes == nullptr) {
        return -2;
    }

    std::vector<shape> heap_shapes(static_cast<std::size_t>(n_shapes));
    for (int i = 0; i < n_shapes; ++i) {
        heap_shapes[static_cast<std::size_t>(i)] = make_internal_shape(shapes[i]);
    }

    std::vector<int> parent(static_cast<std::size_t>(n_shapes), -1);
    Pattern pat{};
    pat.nshapes = n_shapes;
    pat.shapes = heap_shapes.data();
    pat.parent = parent.data();
    if (Pattern_GetContainmentTree(&pat) != 0) {
        for (auto& s : heap_shapes) {
            free_internal_shape(s);
        }
        return -3;
    }

    const int rc = pattern_generate_flow_field(n_shapes, heap_shapes.data(), parent.data(), 0, Lr,
                                               nu, nv, vfield);

    for (auto& s : heap_shapes) {
        free_internal_shape(s);
    }
    return rc;
}
