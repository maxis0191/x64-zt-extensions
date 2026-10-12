#pragma once
// Source-only candidate. No payload pointer exists in this observation interface.
#include <array>
#include <cstddef>
#include <exception>
#include <iomanip>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace recipient_script_names
{
    inline constexpr std::array<const char*, 2> keys{"scripts/engine/utility", "2626"};
    inline constexpr std::size_t max_callbacks = 4096, max_name = 240, max_output = 4096;
    inline constexpr int script_type = 49, max_length = 64 * 1024 * 1024;

    inline void require(bool value, const char* message)
    {
        if (!value) throw std::runtime_error(message);
    }

    inline std::string bounded_name(const char* value)
    {
        require(value != nullptr, "script-name observation: null metadata name");
        std::string result;
        for (std::size_t i = 0; i <= max_name; ++i)
        {
            const auto c = static_cast<unsigned char>(value[i]);
            if (!c)
            {
                require(!result.empty(), "script-name observation: empty name");
                return result;
            }
            require(i < max_name, "script-name observation: name limit exceeded");
            require(c >= 0x20 && c <= 0x7e, "script-name observation: non-ASCII name");
            result.push_back(static_cast<char>(c));
        }
        throw std::runtime_error("script-name observation: unterminated name");
    }

    struct metadata
    {
        std::string content_name, database_name;
        int compressed_len{}, source_len{}, bytecode_len{};
        bool is_default{};
        bool operator==(const metadata&) const = default;
    };

    struct row
    {
        bool present{};
        std::size_t identity{};
        metadata value{};
    };

    class observation
    {
        struct identity_record { const void* pointer; metadata value; };
        std::vector<identity_record> identities_;
        std::array<row, 2> enumerated_{}, direct_{};
        std::array<bool, 2> direct_seen_{};
        std::array<std::size_t, 2> occurrences_{};
        std::size_t callbacks_{}, null_headers_{}, null_names_{}, named_{}, decimal_{}, unmatched_{};

        row capture(const void* pointer, metadata value)
        {
            require(pointer != nullptr, "script-name observation: null identity");
            require(bounded_name(value.content_name.c_str()) == value.content_name &&
                    bounded_name(value.database_name.c_str()) == value.database_name,
                    "script-name observation: embedded name terminator");
            for (const auto length : {value.compressed_len, value.source_len, value.bytecode_len})
                require(length >= 0 && length <= max_length, "script-name observation: invalid declared length");
            for (std::size_t i = 0; i < identities_.size(); ++i)
            {
                if (identities_[i].pointer != pointer) continue;
                require(identities_[i].value == value, "script-name observation: identity metadata changed");
                return {true, i + 1, std::move(value)};
            }
            require(identities_.size() < 4, "script-name observation: identity count exceeded");
            identities_.push_back({pointer, value});
            return {true, identities_.size(), std::move(value)};
        }

        static void write_row(std::ostream& out, const row& value)
        {
            if (!value.present) { out << "null"; return; }
            out << "{\"identity\":" << value.identity << ",\"type\":49,\"content_name\":"
                << std::quoted(value.value.content_name) << ",\"database_name\":"
                << std::quoted(value.value.database_name) << ",\"compressed_len\":" << value.value.compressed_len
                << ",\"source_len\":" << value.value.source_len << ",\"bytecode_len\":" << value.value.bytecode_len
                << ",\"is_default\":" << value.value.is_default << '}';
        }

    public:
        // The factory is invoked only for a matched name, never for other assets.
        template <typename MetadataFactory>
        void enumerate(const void* pointer, const char* raw_name, MetadataFactory factory)
        {
            require(callbacks_ < max_callbacks, "script-name observation: callback limit exceeded");
            ++callbacks_;
            if (!pointer) { ++null_headers_; return; }
            if (!raw_name) { ++null_names_; return; }
            const auto name = bounded_name(raw_name);
            ++named_;
            bool decimal = true;
            for (const auto c : name) decimal = decimal && c >= '0' && c <= '9';
            if (decimal) ++decimal_;
            std::size_t key = 0;
            while (key < keys.size() && name != keys[key]) ++key;
            if (key == keys.size()) { ++unmatched_; return; }
            auto value = factory();
            require(value.content_name == name, "script-name observation: enum name changed");
            auto current = capture(pointer, std::move(value));
            require(!enumerated_[key].present || enumerated_[key].identity == current.identity,
                    "script-name observation: ambiguous enum name");
            enumerated_[key] = std::move(current);
            ++occurrences_[key];
        }

        template <typename MetadataFactory>
        void direct(std::size_t key, bool entry_present, int entry_type, const void* pointer, MetadataFactory factory)
        {
            require(key < keys.size() && !direct_seen_[key], "script-name observation: duplicate/unknown direct key");
            direct_seen_[key] = true;
            if (!entry_present) return;
            require(entry_type == script_type, "script-name observation: direct type mismatch");
            direct_[key] = capture(pointer, factory());
        }

        std::string json() const
        {
            require(direct_seen_[0] && direct_seen_[1], "script-name observation: incomplete direct lookups");
            std::ostringstream out;
            out.imbue(std::locale::classic());
            out << std::boolalpha
                << "{\"schema\":\"iw7.recipient-script-names/1\",\"donor_map\":\"cp_zmb\",\"asset_type\":49,"
                << "\"token_alias_inferred\":false,\"enumeration\":{\"callbacks\":" << callbacks_
                << ",\"null_headers\":" << null_headers_ << ",\"null_names\":" << null_names_
                << ",\"named\":" << named_ << ",\"decimal_names\":" << decimal_
                << ",\"unmatched\":" << unmatched_ << ",\"matched\":" << occurrences_[0] + occurrences_[1]
                << "},\"targets\":[";
            for (std::size_t i = 0; i < keys.size(); ++i)
            {
                if (i) out << ',';
                out << "{\"key\":" << std::quoted(keys[i]) << ",\"enum_occurrences\":" << occurrences_[i]
                    << ",\"enum\":";
                write_row(out, enumerated_[i]);
                out << ",\"direct\":";
                write_row(out, direct_[i]);
                out << '}';
            }
            out << "],\"payload_bytes_read\":0,\"script_bytes_verified\":false,"
                << "\"closure_complete\":false,\"ready\":false}\n";
            auto result = out.str();
            require(result.size() <= max_output, "script-name observation: output limit exceeded");
            return result;
        }
    };
}
