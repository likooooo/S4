#include "s4_test_common.hpp"

#include <cstdio>
#include <cstdlib>
#include <string>

namespace {

void print_usage(const char* prog) {
    std::fprintf(stderr,
                 "Usage: %s --output <path.bin> --backend-tag <RNP|MEKIL> [--case-filter NAME]\n",
                 prog);
}

}  // namespace

int main(int argc, char** argv) {
    std::string output_path;
    std::string backend_tag = "MEKIL";
    const char* case_filter = nullptr;

    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--output" && i + 1 < argc) {
            output_path = argv[++i];
        } else if (arg == "--backend-tag" && i + 1 < argc) {
            backend_tag = argv[++i];
        } else if (arg == "--case-filter" && i + 1 < argc) {
            case_filter = argv[++i];
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
        s4_test::register_all_cases(w, case_filter);
        w.finalize();
        std::printf("s4_backend_test_runner wrote %s (%s backend)\n", output_path.c_str(),
                    backend_tag.c_str());
        return 0;
    } catch (const std::exception& ex) {
        std::fprintf(stderr, "s4_backend_test_runner FAILED: %s\n", ex.what());
        return 1;
    }
}
