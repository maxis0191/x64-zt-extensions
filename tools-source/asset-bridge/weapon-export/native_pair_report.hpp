#pragma once
// Inactive report/raw binding only. Success is not provenance, PR216 eligibility,
// an ingest permission or an allocator/engine qualification. No body is decoded.
#include "native_pair_owned_input.hpp"
#if defined(JSON_DIAGNOSTICS) && JSON_DIAGNOSTICS != 1
#error "The existing primary JSON contract requires JSON_DIAGNOSTICS=1"
#endif
#ifndef JSON_DIAGNOSTICS
#define JSON_DIAGNOSTICS 1
#endif
// Existing primary: nlohmann/json 484483acad6d562306efc9b3c6d413404f1b1f8a,
// single_include/nlohmann/json.hpp, 993716 bytes, SHA256
// 53855e4a20d7bc92d9624bf0d83fba8e22d0d9de83f9480bd4895651602fa8cc.
#include <json.hpp>
#include <initializer_list>
#include <set>
#include <utility>

namespace player_pair_report
{
    struct ReportError : std::runtime_error
    {
        explicit ReportError(const char* message) : std::runtime_error(message) {}
    };
    namespace detail
    {
        using Json = nlohmann::ordered_json;
        using Role = player_pair_input::Role;
        inline void need(bool value, const char* message)
        {
            if (!value) throw ReportError(message);
        }
        inline constexpr std::array<std::pair<std::string_view, std::string_view>, 10> fixed_text{{
            {"schema", "iw7.neutral-weapon-clone/1"}, {"profile", "iw7-shredder-neutral-1-0"},
            {"weapon", "sdk_shredder_clone_zm"}, {"pap_attachment", "sdk_shredder_clone_pap_zm"},
            {"source_weapon", "iw7_shredder_zm"}, {"source_pap_attachment", "shredderpap1"},
            {"upgraded_engine_variant", "sdk_shredder_clone_zm+sdk_shredder_clone_pap_zm"},
            {"source_layout_pin", "fab935826c898806855376662a8a03317b3ad8f1"},
            {"external_name_driven_gameplay", "unverified: private names do not inherit Shredder GSC callbacks"},
            {"visuals", "unchanged IW7 references; dependency bodies not captured"}}};
        inline constexpr std::array<std::string_view, 13> false_flags{{
            "bo3_assets_authenticated", "external_name_driven_gameplay_verified", "native_parser_verified",
            "ff_built", "roundtrip_verified", "runtime_abi_verified", "lifetime_verified", "weapon_granted",
            "projectile_damage_verified", "physics_qualified", "retail_pap_transaction_verified",
            "gameplay_accepted", "ready"}};
        inline constexpr std::array<std::string_view, 3> paths{{
            "weapons/sdk_shredder_clone_zm.json", "attachments/sdk_shredder_clone_pap_zm.json",
            "zone_source/sdk_shredder_clone_zm.csv"}};
        inline constexpr std::string_view csv =
            "weapon,sdk_shredder_clone_zm\nattachment,sdk_shredder_clone_pap_zm\n";
        inline constexpr std::string_view csv_hash =
            "f539cb31e182b7648cac4eb4da369e344d0a8da1a877c4fbed1dc23ef105f2c8";
        inline bool hash_string(std::string_view value)
        {
            return value.size() == 64 && std::all_of(value.begin(), value.end(),
                [](char c) { return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'); });
        }
        inline std::string_view text(const Json& value)
        {
            need(value.is_string(), "Report string required");
            return value.get_ref<const Json::string_t&>();
        }
        inline void closed(const Json& value, std::initializer_list<std::string_view> keys)
        {
            need(value.is_object() && value.size() == keys.size(), "Closed report object required");
            for (const auto key : keys)
                need(value.find(std::string(key)) != value.end(), "Report key differs");
        }
        inline std::size_t bounded_integer(const Json& value, std::size_t cap)
        {
            // Check the actual variant and range BEFORE conversion/narrowing.
            // In this primary is_number_integer() also includes unsigned.
            if (value.type() == Json::value_t::number_unsigned)
            {
                const auto number = value.get<Json::number_unsigned_t>();
                need(number <= cap, "Report integer range differs");
                return static_cast<std::size_t>(number);
            }
            need(value.type() == Json::value_t::number_integer, "Report integer kind differs");
            const auto number = value.get<Json::number_integer_t>();
            need(number >= 0 && static_cast<std::uint64_t>(number) <= cap, "Report integer range differs");
            return static_cast<std::size_t>(number); // Includes Python-compatible integer -0.
        }

        // Pin-specific primary callback. Accepted events always return true;
        // refusing events throw before insertion/push/storage, never discard.
        // Lexer/scalar temporaries may already allocate before a callback.
        struct ReportGuard
        {
            struct Frame { bool array; std::size_t elements{}; std::set<std::string> keys; };
            std::vector<Frame> frames;
            std::size_t nodes{}, max_depth{}, max_array{};
            void value_start(int depth)
            {
                need(depth >= 0 && static_cast<std::size_t>(depth) == frames.size() && depth <= 64,
                    "Report depth bound exceeded");
                need(nodes < 32768, "Report node bound exceeded");
                ++nodes;
                max_depth = (std::max)(max_depth, static_cast<std::size_t>(depth));
                if (!frames.empty() && frames.back().array)
                {
                    need(frames.back().elements < 8192, "Report array bound exceeded");
                    ++frames.back().elements;
                    max_array = (std::max)(max_array, frames.back().elements);
                }
            }
            bool operator()(int depth, Json::parse_event_t event, Json& parsed)
            {
                using Event = Json::parse_event_t;
                if (event == Event::object_start || event == Event::array_start)
                {
                    value_start(depth);
                    frames.push_back({event == Event::array_start, 0, {}});
                }
                else if (event == Event::key)
                {
                    need(!frames.empty() && !frames.back().array && depth >= 0 &&
                        static_cast<std::size_t>(depth) == frames.size(), "Report key event differs");
                    const auto& key = parsed.get_ref<const Json::string_t&>();
                    need(frames.back().keys.insert(key).second, "Duplicate report key");
                }
                else if (event == Event::value)
                {
                    need(!parsed.is_structured(), "Report scalar event differs");
                    value_start(depth);
                }
                else
                {
                    need((event == Event::object_end || event == Event::array_end) &&
                        !frames.empty() && depth >= 0 && static_cast<std::size_t>(depth) + 1 == frames.size() &&
                        frames.back().array == (event == Event::array_end), "Report end event differs");
                    frames.pop_back();
                }
                return true;
            }
        };
        inline Json parse_report(std::string_view raw, ReportGuard& guard)
        {
            need(!raw.empty() && raw.size() <= player_pair_input::role_caps[0], "Report raw bound differs");
            need(raw.size() < 3 || raw.substr(0, 3) != std::string_view("\xef\xbb\xbf", 3),
                "Report BOM refused");
            need(raw.find('\0') == std::string_view::npos, "Report raw NUL refused");
            auto report = Json::parse(raw.begin(), raw.end(),
                [&guard](int depth, Json::parse_event_t event, Json& value) { return guard(depth, event, value); },
                true, false, false); // Strict EOF, exceptions, no comments/trailing commas.
            need(guard.frames.empty() && guard.nodes > 0, "Report event closure differs");
            return report;
        }
        inline void raw_pin(const player_pair_input::OwnedInput& owner, Role role)
        {
            const auto index = static_cast<std::size_t>(role);
            const auto& raw = owner.bytes(role);
            const auto pin = owner.pin(role);
            need(!raw.empty() && raw.size() <= player_pair_input::role_caps[index] &&
                pin.bytes == raw.size() && hash_string(pin.sha256), "Owned report role pin differs");
            need(player_pair_input::detail::sha256(raw) == pin.sha256, "Owned raw SHA256 differs");
        }
    }

    // SAME owner is the sole input. No DOM/reference/result escapes. This does
    // not replace the authored-case address gate or any before-arena body gate.
    inline void validate_owned_report(const player_pair_input::OwnedInput& owner)
    {
        using namespace detail;
        raw_pin(owner, Role::report); // Copied EXTERNAL raw pin, before any decode.
        ReportGuard guard;
        const auto report = parse_report(owner.bytes(Role::report), guard);
        closed(report, {"schema", "profile", "weapon", "pap_attachment", "source_weapon", "source_pap_attachment",
            "upgraded_engine_variant", "source_layout_pin", "external_name_driven_gameplay", "visuals",
            "bo3_assets_authenticated", "external_name_driven_gameplay_verified", "native_parser_verified",
            "ff_built", "roundtrip_verified", "runtime_abi_verified", "lifetime_verified", "weapon_granted",
            "projectile_damage_verified", "physics_qualified", "retail_pap_transaction_verified", "gameplay_accepted",
            "ready", "pap_attachment_slot", "observed_base_type", "observed_pap_type", "source_enum_map",
            "json_mechanics_fields_preserved", "input_sha256", "files"});
        for (const auto& entry : fixed_text)
            need(text(report.at(std::string(entry.first))) == entry.second, "Fixed report text differs");
        const auto slot = text(report.at("pap_attachment_slot"));
        need(slot == "attachments" || slot == "attachments2" || slot == "attachments3" ||
            slot == "attachments4" || slot == "attachments5" || slot == "attachments6", "Report slot differs");
        need(bounded_integer(report.at("observed_base_type"), 1) == 1 &&
            bounded_integer(report.at("observed_pap_type"), 0) == 0, "Report neutral profile differs");
        const auto& mechanics = report.at("json_mechanics_fields_preserved");
        need(mechanics.is_boolean() && mechanics.get<bool>(), "Report mechanics flag differs");
        for (const auto flag : false_flags)
        {
            const auto& value = report.at(std::string(flag));
            need(value.is_boolean() && !value.get<bool>(), "Report qualification flag differs");
        }
        const auto& enums = report.at("source_enum_map");
        closed(enums, {"base", "pap"});
        need(text(enums.at("base")) == "WEAPTYPE_BULLET" && text(enums.at("pap")) == "WEAPTYPE_NONE",
            "Report enum differs");
        const auto& provenance = report.at("input_sha256");
        closed(provenance, {"manifest", "weapon", "pap"});
        for (const auto& value : provenance)
            need(hash_string(text(value)), "Report input hash syntax differs"); // Metadata, not provenance proof.
        const auto& rows = report.at("files");
        need(rows.is_array() && rows.size() == 3, "Three report file rows required");
        std::array<bool, 3> seen{};
        for (const auto& row : rows)
        {
            closed(row, {"path", "bytes", "sha256"});
            const auto path = text(row.at("path"));
            const auto found = std::find(paths.begin(), paths.end(), path);
            need(found != paths.end(), "Report role path differs");
            const auto index = static_cast<std::size_t>(found - paths.begin());
            need(!seen[index], "Duplicate report role");
            seen[index] = true;
            const auto role = static_cast<Role>(index + 1);
            const auto size = bounded_integer(row.at("bytes"), player_pair_input::role_caps[index + 1]);
            const auto hash = text(row.at("sha256"));
            need(size > 0 && hash_string(hash), "Report row pin differs");
            const auto pin = owner.pin(role);
            need(size == owner.bytes(role).size() && size == pin.bytes && hash == pin.sha256,
                "Report row does not bind SAME owned role");
            raw_pin(owner, role);
            if (role == Role::csv)
                need(size == csv.size() && hash == csv_hash && std::string_view(owner.bytes(role)) == csv, "Exact CSV66 differs");
        }
    }
}
