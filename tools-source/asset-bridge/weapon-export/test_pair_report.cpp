// AUTHORED, NOT COMPILED/EXECUTED at Source preparation. Later CPP evidence is separate.
// Standalone report/raw binding only; no body/core/arena/factory/FILE/engine input.
#include "native_pair_report.hpp"
#include <cstdlib>
#include <iostream>
#include <limits>
#include <memory>
#include <new>
#include <type_traits>
#include <utility>

namespace input = player_pair_input;
namespace report = player_pair_report;
using Json = nlohmann::ordered_json;
namespace allocation_fault
{
    // Fixture-only real standard-new failure. No production injection API.
    struct Failure : std::bad_alloc {};
    bool armed = false;
    std::size_t live = 0, attempts = 0;
}
void* operator new(std::size_t bytes)
{
    if (allocation_fault::armed) { ++allocation_fault::attempts; throw allocation_fault::Failure(); }
    if (void* result = std::malloc(bytes ? bytes : 1)) { ++allocation_fault::live; return result; }
    throw std::bad_alloc();
}
void operator delete(void* pointer) noexcept
{
    if (pointer) { --allocation_fault::live; std::free(pointer); }
}
void* operator new[](std::size_t bytes) { return ::operator new(bytes); }
void operator delete[](void* pointer) noexcept { ::operator delete(pointer); }
void operator delete(void* pointer, std::size_t) noexcept { ::operator delete(pointer); }
void operator delete[](void* pointer, std::size_t) noexcept { ::operator delete(pointer); }

static void check(bool value) { if (!value) throw std::runtime_error("Report fixture refused"); }
template<class E, class F> static void refuses_as(F call, const char* message = nullptr)
{
    bool failed = false;
    try { call(); }
    catch (const E& error) { failed = true; if (message) check(std::string_view(error.what()) == message); }
    check(failed);
}
static std::string replace_once(std::string value, std::string_view old, std::string_view replacement)
{
    const auto at = value.find(old); check(at != std::string::npos);
    value.replace(at, old.size(), replacement); return value;
}
struct Data
{
    std::array<std::string, 4> raw;
    Json value;
    Data()
    {
        // Bodies are deliberately NOT JSON; raw NUL in opaque roles is legal.
        raw[1] = std::string("authored weapon\0opaque", 22);
        raw[2] = std::string("authored attachment\0opaque", 26);
        raw[3] = "weapon,sdk_shredder_clone_zm\nattachment,sdk_shredder_clone_pap_zm\n";
        value = Json::parse(R"({
            "schema":"iw7.neutral-weapon-clone/1","profile":"iw7-shredder-neutral-1-0",
            "weapon":"sdk_shredder_clone_zm","pap_attachment":"sdk_shredder_clone_pap_zm",
            "source_weapon":"iw7_shredder_zm","source_pap_attachment":"shredderpap1",
            "upgraded_engine_variant":"sdk_shredder_clone_zm+sdk_shredder_clone_pap_zm",
            "source_layout_pin":"fab935826c898806855376662a8a03317b3ad8f1",
            "external_name_driven_gameplay":"unverified: private names do not inherit Shredder GSC callbacks",
            "visuals":"unchanged IW7 references; dependency bodies not captured",
            "pap_attachment_slot":"attachments6","observed_base_type":1,"observed_pap_type":0,
            "source_enum_map":{"base":"WEAPTYPE_BULLET","pap":"WEAPTYPE_NONE"},
            "json_mechanics_fields_preserved":true,
            "bo3_assets_authenticated":false,"external_name_driven_gameplay_verified":false,
            "native_parser_verified":false,"ff_built":false,"roundtrip_verified":false,
            "runtime_abi_verified":false,"lifetime_verified":false,"weapon_granted":false,
            "projectile_damage_verified":false,"physics_qualified":false,
            "retail_pap_transaction_verified":false,"gameplay_accepted":false,"ready":false
        })");
        value["input_sha256"] = {{"manifest", input::detail::sha256("authored prior manifest")},
            {"weapon", input::detail::sha256("authored prior weapon")},
            {"pap", input::detail::sha256("authored prior pap")}};
        value["files"] = Json::array();
        const char* paths[] = {"weapons/sdk_shredder_clone_zm.json", "attachments/sdk_shredder_clone_pap_zm.json",
            "zone_source/sdk_shredder_clone_zm.csv"};
        for (std::size_t i = 0; i < 3; ++i)
            value["files"].push_back({{"path", paths[i]}, {"bytes", raw[i + 1].size()},
                {"sha256", input::detail::sha256(raw[i + 1])}});
        encode();
    }
    void encode() { raw[0] = value.dump(); }
    std::unique_ptr<input::OwnedInput> own() const
    {
        std::array<std::string, 4> hashes;
        input::Inputs incoming; input::Pins pins; input::Counters counters;
        for (std::size_t i = 0; i < 4; ++i)
        {
            hashes[i] = input::detail::sha256(raw[i]);
            incoming[i] = raw[i]; pins[i] = {raw[i].size(), hashes[i]};
        }
        auto owner = std::make_unique<input::OwnedInput>(incoming, pins, counters);
        check(counters.copies == 4 && counters.hashes == 4); return owner;
    }
};
static void validate(const Data& data) { const auto owner = data.own(); report::validate_owned_report(*owner); }
static void rejects(Data data) // Fresh external pins reach the production validator.
{
    const auto owner = data.own();
    bool failed = false;
    try { report::validate_owned_report(*owner); }
    catch (const report::ReportError&) { failed = true; }
    catch (const Json::exception&) { failed = true; }
    check(failed);
}
static void reject_raw(std::string raw, const char* message = nullptr)
{
    Data data; data.raw[0] = std::move(raw); const auto owner = data.own();
    if (message) refuses_as<report::ReportError>([&] { report::validate_owned_report(*owner); }, message);
    else rejects(std::move(data));
}

static void same_owned_report_only()
{
    static_assert(std::is_same_v<decltype(report::validate_owned_report(std::declval<const input::OwnedInput&>())), void>);
    std::unique_ptr<input::OwnedInput> owner;
    {
        Data caller; owner = caller.own();
        for (auto& bytes : caller.raw) bytes.assign(1, 'x');
        caller.value = nullptr;
    }
    check(owner->bytes(input::Role::weapon).find('\0') != std::string::npos);
    check(owner->bytes(input::Role::attachment).find('\0') != std::string::npos);
    report::validate_owned_report(*owner); // No attempt to parse either opaque body.
    report::detail::ReportGuard guard;
    const auto parsed = report::detail::parse_report(owner->bytes(input::Role::report), guard);
    check(parsed.size() == 30 && guard.nodes == 48 && guard.max_depth == 3 && guard.max_array == 3);
}
static void external_pins_before_decode()
{
    Data data; data.raw[0].insert(0, 1, ' ');
    std::array<std::string, 4> hashes;
    input::Inputs incoming; input::Pins pins;
    for (std::size_t i = 0; i < 4; ++i)
    {
        hashes[i] = input::detail::sha256(data.raw[i]); incoming[i] = data.raw[i];
        pins[i] = {data.raw[i].size(), hashes[i]};
    }
    // Equivalent serialization remains different RAW bytes; old hash refuses.
    auto changed = data.raw[0].substr(1) + " "; incoming[0] = changed;
    input::Counters different;
    refuses_as<input::PinError>([&] { input::OwnedInput owner(incoming, pins, different); });
    check(different.copies == 4 && different.hashes == 1);
    incoming[0] = data.raw[0];
    for (const auto length : {std::size_t(0), std::size_t(65537), pins[0].bytes - 1})
    {
        auto bad = pins; bad[0].bytes = length; input::Counters counters;
        refuses_as<input::PinError>([&] { input::OwnedInput owner(incoming, bad, counters); });
        check(counters.copies == 0 && counters.hashes == 0);
    }
    for (const auto hash : {std::string(64, 'A'), std::string(63, 'a'), std::string(64, 'g')})
    {
        auto bad = pins; bad[0].sha256 = hash; input::Counters counters;
        refuses_as<input::PinError>([&] { input::OwnedInput owner(incoming, bad, counters); });
        check(counters.copies == 0 && counters.hashes == 0);
    }
    for (std::size_t role = 0; role < 4; ++role)
    {
        const std::string oversized(input::role_caps[role] + 1, 'x');
        for (const auto bytes : {std::string_view(), std::string_view(oversized)})
        {
            auto bad = incoming; bad[role] = bytes; input::Counters counters;
            refuses_as<input::PinError>([&] { input::OwnedInput owner(bad, pins, counters); });
            check(counters.copies == 0 && counters.hashes == 0);
        }
        auto bad = pins; bad[role].bytes = input::role_caps[role] + 1; input::Counters counters;
        refuses_as<input::PinError>([&] { input::OwnedInput owner(incoming, bad, counters); });
        check(counters.copies == 0 && counters.hashes == 0);
    }
    // Existing production aggregate primitive: role caps sum to total_cap.
    check(input::detail::checked_total(0, input::total_cap) == input::total_cap);
    refuses_as<input::PinError>([] { input::detail::checked_total(input::total_cap, 1); });
    refuses_as<input::PinError>([] { input::detail::checked_total(1, (std::numeric_limits<std::size_t>::max)()); });
}
static void closed_keys_and_early_duplicates()
{
    const Data good;
    for (auto it = good.value.begin(); it != good.value.end(); ++it)
    {
        Data data = good; data.value.erase(it.key()); data.encode(); rejects(std::move(data));
    }
    Data extra = good; extra.value["unknown"] = 0; extra.encode(); rejects(std::move(extra));
    for (const auto key : {"source_enum_map", "input_sha256"})
    {
        Data unknown = good; unknown.value[key]["unknown"] = 0; unknown.encode(); rejects(std::move(unknown));
        Data missing = good; missing.value[key].erase(missing.value[key].begin()); missing.encode(); rejects(std::move(missing));
    }
    Data row = good; row.value["files"][0]["unknown"] = 0; row.encode(); rejects(std::move(row));
    row = good; row.value["files"][0].erase("sha256"); row.encode(); rejects(std::move(row));
    // The SECOND value is malformed. A parse_error is NOT the required result.
    for (const auto raw : {R"({"schema":0,"schema":]})", R"({"schema":0,"sche\u006da":]})",
                          R"({"outer":{"key":0,"k\u0065y":]}})"})
        reject_raw(raw, "Duplicate report key");
}
static void literal_schema_and_numbers()
{
    const Data good;
    for (const auto& fixed : report::detail::fixed_text)
    {
        for (const auto& value : {Json("different"), Json(0), Json(false), Json(nullptr)})
        {
            Data data = good; data.value[std::string(fixed.first)] = value; data.encode(); rejects(std::move(data));
        }
    }
    for (const auto flag : report::detail::false_flags)
        for (const auto& value : {Json(true), Json(0), Json(0.0), Json("false"), Json(nullptr)})
        {
            Data data = good; data.value[std::string(flag)] = value; data.encode(); rejects(std::move(data));
        }
    for (const auto& value : {Json(false), Json(1), Json("true"), Json(nullptr)})
    {
        Data data = good; data.value["json_mechanics_fields_preserved"] = value; data.encode(); rejects(std::move(data));
    }
    for (const auto slot : {"attachments", "attachments2", "attachments3", "attachments4", "attachments5", "attachments6"})
    {
        Data data = good; data.value["pap_attachment_slot"] = slot; data.encode(); validate(data);
    }
    for (const auto slot : {"attachments1", "attachments7", "Attachments", "attachments6 "})
    {
        Data data = good; data.value["pap_attachment_slot"] = slot; data.encode(); rejects(std::move(data));
    }
    for (const auto key : {"base", "pap"})
    {
        Data data = good; data.value["source_enum_map"][key] = "WEAPTYPE_OTHER"; data.encode(); rejects(std::move(data));
    }
    for (const auto field : {"observed_base_type", "observed_pap_type"})
        for (const auto& value : {Json(true), Json(-1), Json(2), Json(1.0), Json(0.0), Json("0"), Json(nullptr)})
        {
            Data data = good; data.value[field] = value; data.encode(); rejects(std::move(data));
        }
    reject_raw(replace_once(good.raw[0], "\"observed_base_type\":1", "\"observed_base_type\":1e0"));
    reject_raw(replace_once(good.raw[0], "\"observed_base_type\":1", "\"observed_base_type\":18446744073709551616"));
    Data negative_zero = good;
    negative_zero.raw[0] = replace_once(good.raw[0], "\"observed_pap_type\":0", "\"observed_pap_type\":-0");
    validate(negative_zero); // Preserve Python integer -0.
    for (const auto& value : {Json(true), Json(-1), Json(0), Json(2097153), Json(22.0), Json("22"), Json(nullptr)})
    {
        Data data = good; data.value["files"][0]["bytes"] = value; data.encode(); rejects(std::move(data));
    }
    for (const auto key : {"manifest", "weapon", "pap"})
        for (const auto& value : {Json(std::string(64, 'A')), Json(std::string(63, 'a')), Json(0), Json(nullptr)})
        {
            Data data = good; data.value["input_sha256"][key] = value; data.encode(); rejects(std::move(data));
        }
}
static void framing_and_actual_event_bounds()
{
    const Data good;
    reject_raw(std::string("\xef\xbb\xbf", 3) + good.raw[0], "Report BOM refused");
    reject_raw(good.raw[0] + std::string(1, '\0') + "ignored suffix", "Report raw NUL refused");
    reject_raw(good.raw[0] + std::string(1, '\0'), "Report raw NUL refused");
    reject_raw(replace_once(good.raw[0], "iw7.neutral-weapon-clone/1", "iw7\\u0000neutral-weapon-clone/1"));
    for (const auto raw : {std::string("{\"x\":\"\xff\"}"), std::string(R"({"x":"\ud800"})"),
                          std::string(R"({"x":"\udc00"})"), std::string("NaN"), std::string("Infinity"),
                          std::string("1e9999"), std::string("/*comment*/{}"), std::string("{\"x\":0,}")})
        reject_raw(raw);
    reject_raw(good.raw[0] + " {}");
    reject_raw(std::string(65, '[') + "0" + std::string(65, ']'), "Report depth bound exceeded");
    std::string array = "[0";
    for (std::size_t i = 1; i < 8193; ++i) array += ",0";
    array += ']'; reject_raw(array, "Report array bound exceeded");
    report::detail::ReportGuard array_boundary;
    const auto full_array = report::detail::parse_report(array.substr(0, array.size() - 3) + "]", array_boundary);
    check(full_array.size() == 8192 && array_boundary.nodes == 8193 && array_boundary.max_array == 8192);
    // Call the SAME production parser/guard, not a duplicate event algorithm.
    for (const auto& sample : {std::string("0"), std::string("[]"), std::string("{}")})
    {
        report::detail::ReportGuard guard;
        const auto parsed = report::detail::parse_report(sample, guard);
        check(!parsed.is_discarded() && guard.nodes == 1 && guard.max_depth == 0 && guard.max_array == 0);
    }
    report::detail::ReportGuard escaped_guard;
    const auto escaped = report::detail::parse_report(R"("\u0000")", escaped_guard);
    check(report::detail::text(escaped).size() == 1 && report::detail::text(escaped)[0] == '\0');
    reject_raw(R"({"sche\u0000ma":0})"); // Legal escape, wrong closed decoded key.
    report::detail::ReportGuard mixed;
    const auto parsed = report::detail::parse_report(R"([[0,{},[]],{"k":true}])", mixed);
    check(parsed.is_array() && mixed.nodes == 7 && mixed.max_depth == 2 && mixed.max_array == 3);
    report::detail::ReportGuard boundary;
    const auto deep = report::detail::parse_report(std::string(64, '[') + "0" + std::string(64, ']'), boundary);
    check(deep.is_array() && boundary.nodes == 65 && boundary.max_depth == 64);
    // 32769 nodes need at least65537 JSON bytes, so raw65536 dominates. This is
    // the actual arithmetic guard at its boundary, NOT a parsed report witness.
    report::detail::ReportGuard node_limit; node_limit.nodes = 32767; node_limit.value_start(0);
    check(node_limit.nodes == 32768);
    refuses_as<report::ReportError>([&] { node_limit.value_start(0); }, "Report node bound exceeded");
    Data oversized; oversized.raw[0].assign(65537, ' ');
    refuses_as<input::PinError>([&] { oversized.own(); });
}
static void closed_roles_and_csv66()
{
    const Data good;
    Data reordered = good; std::swap(reordered.value["files"][0], reordered.value["files"][2]);
    reordered.encode(); validate(reordered);
    for (const auto path : {"WEAPONS/sdk_shredder_clone_zm.json", "weapons\\sdk_shredder_clone_zm.json",
        "../weapons/sdk_shredder_clone_zm.json", "weapons/sdk_shredder_clone_zm.json.extra"})
    {
        Data data = good; data.value["files"][0]["path"] = path; data.encode(); rejects(std::move(data));
    }
    Data duplicate = good; duplicate.value["files"][1] = duplicate.value["files"][0]; duplicate.encode(); rejects(std::move(duplicate));
    Data missing = good; missing.value["files"].erase(missing.value["files"].begin()); missing.encode(); rejects(std::move(missing));
    Data extra = good; extra.value["files"].push_back(extra.value["files"][0]); extra.encode(); rejects(std::move(extra));
    for (const auto hash : {std::string(64, '0'), std::string(64, 'A'), std::string(63, 'a')})
    {
        Data data = good; data.value["files"][0]["sha256"] = hash; data.encode(); rejects(std::move(data));
    }
    for (const auto at : {std::size_t(6), std::size_t(26)})
    {
        Data data = good; data.raw[3][at] = '?';
        data.value["files"][2]["sha256"] = input::detail::sha256(data.raw[3]); data.encode(); rejects(std::move(data));
    }
    Data crlf = good; crlf.raw[3] = replace_once(crlf.raw[3], "\n", "\r\n");
    crlf.value["files"][2]["bytes"] = crlf.raw[3].size();
    crlf.value["files"][2]["sha256"] = input::detail::sha256(crlf.raw[3]); crlf.encode();
    refuses_as<input::PinError>([&] { crlf.own(); }); // Role cap66 refuses first.
}
static void changed_owner_and_fourth_binding_only()
{
    Data changed; changed.raw[1][0] = 'X';
    rejects(changed); // Fresh caller hash passes construction; old report row refuses.
    changed.value["files"][0]["sha256"] = input::detail::sha256(changed.raw[1]);
    changed.encode(); validate(changed);
    // A self-consistent fourth authored tuple is ONLY report/raw binding. This
    // module has no parse selection; test_authored_pair_json's address gate is unchanged.
}
static void primary_exception_and_standard_memory_unwind()
{
    Data malformed; malformed.raw[0] = "{\"malformed\":";
    const auto bad = malformed.own();
    const auto old_bytes = bad->bytes(input::Role::report);
    const auto old_hash = std::string(bad->pin(input::Role::report).sha256);
    refuses_as<Json::parse_error>([&] { report::validate_owned_report(*bad); });
    check(bad->bytes(input::Role::report) == old_bytes && bad->pin(input::Role::report).sha256 == old_hash);
    Data good; const auto owner = good.own();
    std::array<std::string, 4> original, hashes;
    for (std::size_t i = 0; i < 4; ++i)
    {
        const auto role = static_cast<input::Role>(i);
        original[i] = owner->bytes(role); hashes[i] = owner->pin(role).sha256;
    }
    const auto before = allocation_fault::live; bool same_type = false;
    allocation_fault::attempts = 0; allocation_fault::armed = true;
    try { report::validate_owned_report(*owner); }
    catch (const allocation_fault::Failure&) { same_type = true; }
    catch (...) { allocation_fault::armed = false; throw; }
    allocation_fault::armed = false;
    check(same_type && allocation_fault::attempts == 1 && allocation_fault::live == before);
    // First allocation is the report SHA256 vector, BEFORE decode. This is NOT
    // parser-allocation or fatal allocator evidence. Real JSON error is separate above.
    for (std::size_t i = 0; i < 4; ++i)
    {
        const auto role = static_cast<input::Role>(i);
        check(owner->bytes(role) == original[i] && owner->pin(role).bytes == original[i].size() &&
            owner->pin(role).sha256 == hashes[i]);
    }
    report::validate_owned_report(*owner); // Same original owner remains usable.
}
int main()
{
    const struct { const char* name; void (*run)(); } groups[] = {
        {"same_owned_report_only", same_owned_report_only}, {"external_pins_before_decode", external_pins_before_decode},
        {"closed_keys_early_duplicates", closed_keys_and_early_duplicates}, {"literal_schema_numbers", literal_schema_and_numbers},
        {"framing_event_bounds", framing_and_actual_event_bounds}, {"closed_roles_csv66", closed_roles_and_csv66},
        {"changed_owner_binding_only", changed_owner_and_fourth_binding_only},
        {"primary_exception_standard_memory", primary_exception_and_standard_memory_unwind}};
    try
    {
        for (const auto& group : groups) { group.run(); std::cout << "PASS " << group.name << '\n'; }
        std::cout << "IW7_PAIR_REPORT=8\n"; return 0;
    }
    catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 2; }
}
