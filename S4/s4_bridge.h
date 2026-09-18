/* S4_bridge: minimal S4 capability subset for simulation_core (C API). */

#ifndef S4_BRIDGE_H_INCLUDED
#define S4_BRIDGE_H_INCLUDED

#ifdef __cplusplus
extern "C" {
#endif

typedef enum S4BridgeShapeKind {
    S4_BRIDGE_CIRCLE = 0,
    S4_BRIDGE_ELLIPSE = 1,
    S4_BRIDGE_RECT = 2,
    S4_BRIDGE_POLYGON = 3
} S4BridgeShapeKind;

typedef struct S4BridgeComplex {
    double re;
    double im;
} S4BridgeComplex;

typedef struct S4BridgeShape {
    S4BridgeShapeKind kind;
    double center[2];
    double angle;
    int material_id;
    union {
        double radius;
        double halfwidth[2];
        struct {
            const double* xy;
            int n_vertices;
        } polygon;
    } geom;
} S4BridgeShape;

/* Full glist pipeline: reciprocal lattice, G selection, kx/ky assembly.
 * G_out must hold at least 2*n_G ints; kx_out/ky_out at least n_G doubles.
 * On success returns 0 and sets *n_G_out to the actual G count. */
int s4_bridge_build_glist(const double Lr[4], unsigned n_G, double k_incident_x,
                            double k_incident_y, double Lk_out[4], unsigned* n_G_out,
                            int* G_out, double* kx_out, double* ky_out);

/* NV polarization flow field (type=0). vfield length = 2*nu*nv. */
int s4_bridge_generate_flow_field(const double Lr[4], int n_shapes,
                                  const S4BridgeShape* shapes, int nu, int nv,
                                  double* vfield);

#ifdef __cplusplus
}
#endif

#endif /* S4_BRIDGE_H_INCLUDED */
