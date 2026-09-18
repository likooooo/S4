#pragma once

// Header-only S4BDMP v1 writer (shared by S4 backend runner and simulation_core dump tests).

#include <chrono>
#include <complex>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace s4_dump {

enum class dtype : std::uint32_t { f64 = 0, c128 = 1 };

enum class backend_id : std::uint32_t { rnp = 0, mekil = 1, simulation = 2 };

inline backend_id backend_from_tag(const std::string& tag) {
    if (tag == "RNP" || tag == "rnp") {
        return backend_id::rnp;
    }
    if (tag == "MEKIL" || tag == "mekil") {
        return backend_id::mekil;
    }
    if (tag == "SIMULATION" || tag == "simulation" || tag == "sim") {
        return backend_id::simulation;
    }
    throw std::runtime_error("unknown backend tag: " + tag);
}

class writer {
public:
    explicit writer(const std::string& path, backend_id backend) : path_(path), backend_(backend) {}

    void begin_case(const std::string& name) {
        flush_case();
        cases_.push_back(case_entry{name, {}});
        current_ = &cases_.back();
    }

    void write_block_f64(const std::string& tag,
                         const std::vector<double>& data,
                         const std::vector<std::uint64_t>& dims) {
        if (current_ == nullptr) {
            throw std::runtime_error("write_block_f64 without begin_case");
        }
        block_entry b;
        b.tag = tag;
        b.dt = dtype::f64;
        b.dims = dims;
        b.payload.resize(data.size() * sizeof(double));
        if (!data.empty()) {
            std::memcpy(b.payload.data(), data.data(), b.payload.size());
        }
        current_->blocks.push_back(std::move(b));
    }

    void write_block_c128(const std::string& tag,
                          const std::vector<std::complex<double>>& data,
                          const std::vector<std::uint64_t>& dims) {
        if (current_ == nullptr) {
            throw std::runtime_error("write_block_c128 without begin_case");
        }
        block_entry b;
        b.tag = tag;
        b.dt = dtype::c128;
        b.dims = dims;
        b.payload.resize(data.size() * sizeof(std::complex<double>));
        if (!data.empty()) {
            std::memcpy(b.payload.data(), data.data(), b.payload.size());
        }
        current_->blocks.push_back(std::move(b));
    }

    void finalize() {
        if (finalized_) {
            return;
        }
        flush_case();
        std::ofstream os(path_, std::ios::binary);
        if (!os) {
            throw std::runtime_error("failed to open dump file: " + path_);
        }
        constexpr char k_magic[8] = {'S', '4', 'B', 'D', 'M', 'P', '\0', '\1'};
        constexpr std::uint32_t k_version = 1;
        os.write(k_magic, sizeof(k_magic));
        write_u32(os, k_version);
        write_u32(os, static_cast<std::uint32_t>(backend_));
        write_u32(os, static_cast<std::uint32_t>(cases_.size()));
        const auto now = std::chrono::system_clock::now().time_since_epoch().count();
        write_u64(os, static_cast<std::uint64_t>(now));

        for (const case_entry& c : cases_) {
            write_string(os, c.name);
            write_u32(os, static_cast<std::uint32_t>(c.blocks.size()));
            for (const block_entry& b : c.blocks) {
                write_string(os, b.tag);
                write_u32(os, static_cast<std::uint32_t>(b.dt));
                write_u32(os, static_cast<std::uint32_t>(b.dims.size()));
                for (std::uint64_t d : b.dims) {
                    write_u64(os, d);
                }
                write_u64(os, static_cast<std::uint64_t>(b.payload.size()));
                os.write(b.payload.data(), static_cast<std::streamsize>(b.payload.size()));
            }
        }
        finalized_ = true;
    }

private:
    struct block_entry {
        std::string tag;
        dtype dt;
        std::vector<std::uint64_t> dims;
        std::vector<char> payload;
    };

    struct case_entry {
        std::string name;
        std::vector<block_entry> blocks;
    };

    static void write_u32(std::ostream& os, std::uint32_t v) {
        os.write(reinterpret_cast<const char*>(&v), sizeof(v));
    }

    static void write_u64(std::ostream& os, std::uint64_t v) {
        os.write(reinterpret_cast<const char*>(&v), sizeof(v));
    }

    static void write_string(std::ostream& os, const std::string& s) {
        write_u32(os, static_cast<std::uint32_t>(s.size()));
        os.write(s.data(), static_cast<std::streamsize>(s.size()));
    }

    void flush_case() { current_ = nullptr; }

    std::string path_;
    backend_id backend_;
    std::vector<case_entry> cases_;
    case_entry* current_ = nullptr;
    bool finalized_ = false;
};

}  // namespace s4_dump
