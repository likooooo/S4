#include "s4_test_common.hpp"

#include <cstdio>
#include <cstdlib>
#include <string>

namespace {

void print_usage(const char* prog) {
    std::fprintf(stderr,
                 "Usage: %s --output <path.bin> --backend-tag <RNP|MEKIL> [--case-filter NAME]\n"
                 "       [--discretized-only] [--discretized-mode fft|kottke]\n",
                 prog);
}

s4_test::discretized_method parse_discretized_mode(const std::string& tag) {
    if (tag == "fft" || tag == "FFT") return s4_test::discretized_method::fft;
    if (tag == "kottke" || tag == "Kottke" || tag == "KOTTKE") return s4_test::discretized_method::kottke;
    throw std::runtime_error("unknown discretized mode: " + tag);
}

}  // namespace

int main(int argc, char** argv) {
    std::string output_path;
    std::string backend_tag = "MEKIL";
    const char* case_filter = nullptr;
    bool discretized_only = false;
    s4_test::discretized_method discretized_mode = s4_test::discretized_method::fft;
    bool has_discretized_mode = false;

    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--output" && i + 1 < argc) {
            output_path = argv[++i];
        } else if (arg == "--backend-tag" && i + 1 < argc) {
            backend_tag = argv[++i];
        } else if (arg == "--case-filter" && i + 1 < argc) {
            case_filter = argv[++i];
        } else if (arg == "--discretized-only") {
            discretized_only = true;
        } else if (arg == "--discretized-mode" && i + 1 < argc) {
            discretized_mode = parse_discretized_mode(argv[++i]);
            has_discretized_mode = true;
        } else if (arg == "--help" || arg == "-h") {
            print_usage(argv[0]);
            return 0;
        } else {
            std::fprintf(stderr, "Unknown argument: %s\n", arg.c_str());
            print_usage(argv[0]);
            return 2;
        }
    }

    if (output_path.empty()) {
        print_usage(argv[0]);
        return 2;
    }

    try {
        s4_dump::writer w(output_path, s4_dump::backend_from_tag(backend_tag));
        if (discretized_only)
            s4_test::register_discretized_cases(w, case_filter,
                                                has_discretized_mode ? &discretized_mode : nullptr);
        else
            s4_test::register_all_cases(w, case_filter);
        w.finalize();
        std::printf("s4_backend_test_runner wrote %s (%s backend%s)\n", output_path.c_str(),
                    backend_tag.c_str(), discretized_only ? ", discretized" : "");
        return 0;
    } catch (const std::exception& ex) {
        std::fprintf(stderr, "s4_backend_test_runner FAILED: %s\n", ex.what());
        return 1;
    }
}
