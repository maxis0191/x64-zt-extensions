#pragma once

#include <cstddef>
#include <cstdint>

// Private fixed/multiframe/explicit16/hybrid0 dump profile. No decoding,
// allocation, file access, ABI changes or claim about later frame validity.
namespace zonetool::iw7::sound_asset_bank::flac_metadata
{
    struct Entry
    {
        std::uint32_t encoded_bytes;
        std::uint32_t seek_bytes;
        std::uint32_t total_samples;
        std::uint32_t hybrid_bytes;
        std::int32_t rate;
        int channels;
    };

    struct Result
    {
        std::uint32_t block_size{};
        std::size_t header_bytes{};
        const char* error{};
        explicit operator bool() const noexcept { return error == nullptr; }
    };

    inline bool contains(const std::uint64_t extent, const std::uint64_t offset,
                         const std::uint64_t count) noexcept
    {
        return offset <= extent && count <= extent - offset;
    }

    inline const char* validate_entry(const Entry& entry, std::uint64_t& bytes) noexcept
    {
        bytes = 0;
        if (entry.hybrid_bytes != 0) return "hybrid PCM is outside dump profile";
        if (entry.rate <= 0 || entry.rate > 0xfffff) return "invalid SAB sample rate";
        if (entry.channels < 1 || entry.channels > 8) return "invalid SAB channel count";
        if (entry.total_samples == 0) return "unknown SAB sample count";
        if (entry.encoded_bytes == 0) return "empty encoded stream";
        if (entry.seek_bytes > 0xffffff || entry.seek_bytes % 18 != 0)
            return "invalid seek prefix length";
        bytes = static_cast<std::uint64_t>(entry.encoded_bytes) + entry.seek_bytes;
        return nullptr;
    }

    class HeaderReader
    {
    public:
        HeaderReader(const std::uint8_t* data, const std::size_t size) noexcept
            : data_(data), size_(size) {}

        bool byte(std::uint32_t& value) noexcept
        {
            if (position_ >= size_) return false;
            value = data_[position_++];
            return true;
        }

        bool big16(std::uint32_t& value) noexcept
        {
            std::uint32_t high{}, low{};
            if (!byte(high) || !byte(low)) return false;
            value = (high << 8) | low;
            return true;
        }

        std::size_t position() const noexcept { return position_; }

    private:
        const std::uint8_t* data_;
        std::size_t size_;
        std::size_t position_{};
    };

    inline std::uint8_t header_crc(const std::uint8_t* data, const std::size_t size) noexcept
    {
        std::uint8_t crc{};
        for (std::size_t i = 0; i < size; ++i)
        {
            crc ^= data[i];
            for (unsigned bit = 0; bit < 8; ++bit)
                crc = static_cast<std::uint8_t>((crc & 0x80) ? (crc << 1) ^ 0x07 : crc << 1);
        }
        return crc;
    }

    inline Result derive(const Entry& entry, const std::uint8_t* data,
                         const std::size_t size) noexcept
    {
        const auto refuse = [](const char* reason) -> Result { return {0, 0, reason}; };
        std::uint64_t expected{};
        if (const auto* error = validate_entry(entry, expected)) return refuse(error);
        if (!data || expected != size || !contains(size, entry.seek_bytes, entry.encoded_bytes))
            return refuse("encoded span length mismatch");
        const auto* frame = data + entry.seek_bytes;
        HeaderReader reader(frame, entry.encoded_bytes);
        std::uint32_t sync1{}, sync2{}, codes{}, channels_depth{}, number{};
        if (!reader.byte(sync1) || !reader.byte(sync2) || !reader.byte(codes) ||
            !reader.byte(channels_depth) || !reader.byte(number))
            return refuse("truncated fixed frame header");
        if (sync1 != 0xff || sync2 != 0xf8) return refuse("fixed frame sync required");
        if ((channels_depth & 1) != 0) return refuse("reserved header bit set");
        if (number != 0) return refuse("canonical first frame number zero required");
        if (((channels_depth >> 1) & 7) != 4) return refuse("explicit 16-bit depth required");
        const auto channel_code = channels_depth >> 4;
        if (channel_code > 10) return refuse("reserved channel assignment");
        const auto channels = channel_code <= 7 ? channel_code + 1 : 2;
        if (channels != static_cast<unsigned>(entry.channels)) return refuse("SAB channel mismatch");

        const auto block_code = codes >> 4;
        std::uint32_t block{};
        if (block_code == 0) return refuse("reserved block size code");
        if (block_code == 1) block = 192;
        else if (block_code <= 5) block = 576u << (block_code - 2);
        else if (block_code == 6)
        {
            if (!reader.byte(block)) return refuse("truncated block extension");
            ++block;
        }
        else if (block_code == 7)
        {
            if (!reader.big16(block)) return refuse("truncated block extension");
            ++block;
        }
        else block = 256u << (block_code - 8);
        if (block < 16 || block > 65535) return refuse("block size outside profile");
        if (entry.total_samples <= block) return refuse("nonfinal first frame required");

        constexpr std::uint32_t rates[]{0, 88200, 176400, 192000, 8000, 16000,
                                        22050, 24000, 32000, 44100, 48000, 96000};
        const auto rate_code = codes & 15;
        std::uint32_t rate{};
        if (rate_code == 0) rate = static_cast<std::uint32_t>(entry.rate);
        else if (rate_code <= 11) rate = rates[rate_code];
        else if (rate_code == 12)
        {
            if (!reader.byte(rate)) return refuse("truncated rate extension");
            rate *= 1000;
        }
        else if (rate_code <= 14)
        {
            if (!reader.big16(rate)) return refuse("truncated rate extension");
            if (rate_code == 14) rate *= 10;
        }
        else return refuse("forbidden sample rate code");
        if (rate != static_cast<std::uint32_t>(entry.rate)) return refuse("SAB sample rate mismatch");

        const auto crc_offset = reader.position();
        std::uint32_t crc{};
        if (!reader.byte(crc)) return refuse("truncated header CRC");
        if (header_crc(frame, crc_offset) != crc) return refuse("header CRC mismatch");
        return {block, reader.position(), nullptr};
    }
}
