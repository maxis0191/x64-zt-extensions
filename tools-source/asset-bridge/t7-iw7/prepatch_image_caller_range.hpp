#pragma once
// Finite code provenance only. This header never reads a process or an asset.
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace zonetool::t7_prepatch_image_caller_range
{
    inline constexpr uint32_t callsite_rva = 0x1B1E5D;
    inline constexpr uint32_t known_target_rva = 0x7DB4C0;
    inline constexpr uint32_t code_limit = 8192;
    inline constexpr size_t pdata_limit = 2 * 1024 * 1024;

    struct entry { uint32_t begin; uint32_t end; uint32_t unwind; };
    static_assert(sizeof(entry) == 12, "Windows x64 runtime-function record");
    struct window { uint32_t begin{}; uint32_t end{}; uint32_t unwind{}; };
    enum class status { ok, invalid_metadata, missing, ambiguous, over_limit, call_outside, opcode, target };

    // Inspect only the already copied, finite exception-directory metadata.
    // No supplied address, length override, nearest-function or fallback exists.
    inline status select(const uint8_t* pdata, size_t bytes, uint32_t image_size, window& out) noexcept
    {
        out = {};
        if (!pdata || !bytes || bytes > pdata_limit || bytes % sizeof(entry) || !image_size)
            return status::invalid_metadata;
        size_t matches{};
        uint32_t previous_end{};
        bool ordered = true;
        window selected{};
        for (size_t offset = 0; offset < bytes; offset += sizeof(entry))
        {
            entry fn{};
            std::memcpy(&fn, pdata + offset, sizeof(fn));
            if (fn.begin >= fn.end || fn.end > image_size || !fn.unwind || fn.unwind >= image_size)
                return status::invalid_metadata;
            if (fn.begin < previous_end) ordered = false;
            previous_end = fn.end;
            if (fn.begin <= callsite_rva && callsite_rva < fn.end)
            {
                ++matches;
                selected = {fn.begin, fn.end, fn.unwind};
            }
        }
        if (matches > 1) return status::ambiguous;
        if (!ordered) return status::invalid_metadata;
        if (matches != 1) return status::missing;
        // Must refuse BEFORE the caller can request any function-body bytes.
        if (selected.end - selected.begin > code_limit) return status::over_limit;
        if (selected.end - callsite_rva < 5) return status::call_outside;
        out = selected;
        return status::ok;
    }

    inline status validate_call(const uint8_t* code, size_t bytes, const window& range) noexcept
    {
        if (!code || range.begin >= range.end || range.begin > callsite_rva ||
            range.end <= callsite_rva || range.end - range.begin > code_limit ||
            bytes != range.end - range.begin || range.end - callsite_rva < 5)
            return status::call_outside;
        const size_t offset = callsite_rva - range.begin;
        if (code[offset] != 0xE8) return status::opcode;
        int32_t displacement{};
        std::memcpy(&displacement, code + offset + 1, sizeof(displacement));
        const auto target = static_cast<int64_t>(callsite_rva) + 5 + displacement;
        return target == known_target_rva ? status::ok : status::target;
    }
}
