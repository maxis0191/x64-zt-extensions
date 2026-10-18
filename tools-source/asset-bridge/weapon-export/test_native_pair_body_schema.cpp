// AUTHORED, NOT COMPILED/EXECUTED at Source preparation. New reviewed CPP GO required.
// Constants-only: no input body, schema interpreter, native layout, arena or engine.
// Interface: frozen generator cfd291253f8d836bb9e6b1d818272f5568990eef,
// blob cf33622aa09ccb871d92c059d3df4cfe19691a78. Later Source-only read of
// frozen header 1073140B, SHA256
// dbedd4632d8bb20686c8c1355d4b0200fc2c6149ba141897007f41252f555b75. No CPP execution.
#include "native_pair_body_schema.hpp"
#include <array>
#include <cstdint>
#include <climits>
#include <cstddef>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string_view>
#include <type_traits>

namespace table = iw7::neutral::body_schema;
using u32 = std::uint32_t;
using u64 = std::uint64_t;
using Span = table::StringSpan;
using Integer = table::Integer;
static_assert(CHAR_BIT == 8 && std::numeric_limits<u32>::digits == 32 && std::numeric_limits<u64>::digits == 64);
static_assert(std::is_same_v<decltype(Span{}.offset), u32> && std::is_same_v<decltype(Span{}.count), u32>);
static_assert(std::is_same_v<decltype(Integer{}.negative), bool> && std::is_same_v<decltype(Integer{}.magnitude), u64>);
static_assert(std::is_same_v<decltype(table::TypeRecord{}.size), u64> && std::is_same_v<decltype(table::TypeRecord{}.element), u32>);
static_assert(std::is_same_v<decltype(table::Operation{}.fixed_count), u64> && std::is_same_v<decltype(table::Operation{}.semantic_domain_unknown), bool>);
static_assert(std::is_same_v<decltype(table::Metadata{}.actual_input_admissibility), bool>);
static_assert(std::is_same_v<decltype(table::extents[0]), const u64&> && std::is_same_v<decltype(table::key_ids[0]), const u32&>);

static void need(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
static bool within(Span value, std::size_t length)
{
    return value.offset <= length && value.count <= length - value.offset;
}
static bool same_span(Span a, Span b) { return a.offset == b.offset && a.count == b.count; }
static bool integer_ok(Integer v) { return !v.negative || v.magnitude != 0; }
static bool equal(Integer a, Integer b) { return a.negative == b.negative && a.magnitude == b.magnitude; }
static bool less(Integer a, Integer b)
{
    if (a.negative != b.negative) return a.negative;
    return a.negative ? a.magnitude > b.magnitude : a.magnitude < b.magnitude;
}
static bool bit(u32 mask, unsigned index) { return (mask & (u32{1} << index)) != 0; }
static std::string_view text(u32 id)
{
    need(id < table::strings.size(), "String ID outside frozen table");
    const auto span = table::strings[id];
    need(within(span, sizeof table::string_pool), "String span outside compiled pool");
    return {table::string_pool + span.offset, span.count};
}
static std::size_t find_type(std::string_view name)
{
    for (std::size_t i = 0; i < table::types.size(); ++i) if (text(table::types[i].name) == name) return i;
    return table::types.size();
}
static const table::TypeRecord& type(std::string_view name)
{
    const auto id = find_type(name); need(id < table::types.size(), "Named type missing"); return table::types[id];
}
static std::size_t find_structure(std::string_view name)
{
    for (std::size_t i = 0; i < table::structures.size(); ++i) if (text(table::structures[i].name) == name) return i;
    return table::structures.size();
}
static const table::Structure& structure(std::string_view name)
{
    const auto id = find_structure(name); need(id < table::structures.size(), "Named structure missing"); return table::structures[id];
}
static const table::Operation& operation(const table::Structure& owner, std::size_t index)
{
    need(within(owner.ops, table::operations.size()) && index < owner.ops.count, "Operation span/index differs");
    return table::operations[static_cast<std::size_t>(owner.ops.offset) + index];
}
static bool lower_hex(std::string_view value, std::size_t size)
{
    if (value.size() != size) return false;
    for (const auto c : value) if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return false;
    return true;
}
static bool utf8(std::string_view value)
{
    // Fixture-only byte integrity check, never an input/body decoder.
    for (std::size_t i = 0; i < value.size();)
    {
        const auto first = static_cast<unsigned char>(value[i++]);
        if (first < 0x80) { if (first == 0) return false; continue; }
        unsigned continuation = 0; u32 scalar = 0, minimum = 0;
        if (first >= 0xc2 && first <= 0xdf) { continuation = 1; scalar = first & 0x1fU; minimum = 0x80; }
        else if (first >= 0xe0 && first <= 0xef) { continuation = 2; scalar = first & 0x0fU; minimum = 0x800; }
        else if (first >= 0xf0 && first <= 0xf4) { continuation = 3; scalar = first & 0x07U; minimum = 0x10000; }
        else return false;
        if (continuation > value.size() - i) return false;
        for (unsigned n = 0; n < continuation; ++n)
        {
            const auto next = static_cast<unsigned char>(value[i++]);
            if ((next & 0xc0U) != 0x80U) return false;
            scalar = (scalar << 6) | (next & 0x3fU);
        }
        if (scalar < minimum || scalar > 0x10ffff || (scalar >= 0xd800 && scalar <= 0xdfff)) return false;
    }
    return true;
}
static bool byte_less(std::string_view a, std::string_view b)
{
    const auto count = a.size() < b.size() ? a.size() : b.size();
    for (std::size_t i = 0; i < count; ++i)
    {
        const auto x = static_cast<unsigned char>(a[i]), y = static_cast<unsigned char>(b[i]);
        if (x != y) return x < y;
    }
    return a.size() < b.size();
}
static bool element_ok(const table::TypeRecord& row)
{
    if (!bit(row.present, 2)) return row.element_tag == 0 && row.element == 0 && row.kind != 1 && row.kind != 3;
    if (row.element_tag == 1) return row.element < table::types.size();
    if (row.element_tag != 2 || row.kind != 1 || row.element >= table::strings.size()) return false;
    return find_type(text(row.element)) == table::types.size(); // Known labels MUST use tag1.
}
static void type_presence(const table::TypeRecord& row)
{
    need(row.kind < table::type_tags.size() && row.present < (u32{1} << 12), "Type tag/presence differs");
    u32 required = 0, optional = 0;
    switch (row.kind)
    {
    case 0: required = (1U << 0) | (1U << 1); optional = 1U << 8; break;
    case 1: required = 1U << 2; break;
    case 2: required = (1U << 4) | (1U << 5) | (1U << 6) | (1U << 7); optional = (1U << 9) | (1U << 10) | (1U << 11); break;
    case 3: required = (1U << 2) | (1U << 3); break;
    case 4: case 6: break;
    case 5: required = (1U << 4) | (1U << 5); break;
    default: need(false, "Unknown type kind");
    }
    need((row.present & required) == required && (row.present & ~(required | optional)) == 0, "Closed type fields differ");
    need(row.align > 0 && (bit(row.present, 0) || row.pack == 0), "Absent pack differs");
    need(bit(row.present, 1) || text(row.size_basis).empty(), "Absent size basis differs");
    need(bit(row.present, 9) || text(row.conversion_basis).empty(), "Absent conversion basis differs");
    need(bit(row.present, 10) || !row.semantic_domain_unknown, "Absent semantic boolean differs");
    need(bit(row.present, 11) || !row.storage_domain_only, "Absent storage boolean differs");
    need(integer_ok(row.minimum) && integer_ok(row.maximum), "Negative zero in type bound");
    need(bit(row.present, 4) || equal(row.minimum, {false, 0}), "Absent minimum differs");
    need(bit(row.present, 5) || equal(row.maximum, {false, 0}), "Absent maximum differs");
    if (bit(row.present, 4) && bit(row.present, 5)) need(!less(row.maximum, row.minimum), "Reversed integer bounds");
    need(bit(row.present, 3) || row.extents.count == 0, "Absent extents differ");
    need(bit(row.present, 6) || row.values.count == 0, "Absent allowed values differ");
    need(bit(row.present, 7) || row.members.count == 0, "Absent declarations differ");
    need(bit(row.present, 8) || row.bitfields.count == 0, "Absent bitfields differ");
}
static void fixed_width_sign_magnitude()
{
    for (const auto value : table::integers) need(integer_ok(value), "Negative zero in allowed enum value");
    for (const auto& value : table::enum_members) need(integer_ok(value.value), "Negative zero in enum declaration");
    for (const auto& row : table::types) type_presence(row);
    const auto& wide = type("std::uint64_t");
    need(equal(wide.minimum, {false, 0}) && equal(wide.maximum, {false, (std::numeric_limits<u64>::max)()}), "uint64 bounds narrowed");
    const auto& signed32 = type("int");
    need(equal(signed32.minimum, {true, 2147483648ULL}) && equal(signed32.maximum, {false, 2147483647ULL}), "Signed magnitude differs");
    need(!integer_ok({true, 0}) && integer_ok({false, 0}), "Fixture sign/magnitude negative-zero check failed");
    const auto& unknown = type("WeaponChargeType");
    need(bit(unknown.present, 6) && unknown.values.count == 0 && bit(unknown.present, 7) && unknown.members.count == 0,
        "Present empty enum metadata collapsed into absence");
    need(bit(unknown.present, 10) && unknown.semantic_domain_unknown && bit(unknown.present, 11) && unknown.storage_domain_only,
        "Storage-only Source labels differ");
    need(table::metadata.size() == 1, "One metadata record required");
    const auto& meta = table::metadata[0];
    need(meta.complete_pinned_extraction && !meta.actual_input_admissibility && !meta.runtime_abi_verified,
        "Source extraction became runtime authority");
    unsigned present_booleans = 3, true_booleans = 1;
    for (const auto& row : table::types)
    {
        if (bit(row.present, 10)) { ++present_booleans; if (row.semantic_domain_unknown) ++true_booleans; }
        if (bit(row.present, 11)) { ++present_booleans; if (row.storage_domain_only) ++true_booleans; }
    }
    for (const auto& row : table::operations) if (bit(row.present, 6)) { ++present_booleans; if (row.semantic_domain_unknown) ++true_booleans; }
    need(present_booleans == 7 && true_booleans == 5, "Five true/two false literal flags differ");
}
static void operation_record(const table::Operation& row)
{
    need(row.tag < table::op_tags.size() && row.present < 256 && row.count_tag <= 2, "Operation tag/presence/count differs");
    text(row.field); text(row.key); text(row.flavor); text(row.named_count);
    const auto tag = text(table::op_tags[row.tag]);
    if (tag == "MANUAL")
    {
        need(row.present == 128 && row.manual < table::manuals.size() && row.count_tag == 0 &&
            row.type == 0 && row.count_type == 0 && row.fixed_count == 0 && !row.semantic_domain_unknown &&
            text(row.field).empty() && text(row.key).empty() && text(row.flavor).empty() && text(row.named_count).empty(),
            "Closed manual operation differs");
        return;
    }
    const bool dynamic = tag == "ASSET_ALLOC_ARR_MODVAL" || tag == "ASSET_ARR" || tag == "SCRIPT_STRING_ALLOC_ARR_MODVAL";
    const bool fixed = tag == "FIELD_ALLOC_ARR" || tag == "FIELD_ARR" || tag == "SCRIPT_STRING_ALLOC_ARR" ||
        tag == "ASSET_FIELD_ARR" || tag == "FXCOMBINED_ALLOC_ARR" || tag == "STRING_ARR";
    const u32 required = 15U | (dynamic ? 48U : fixed ? 16U : 0U);
    const u32 optional = tag == "FIELD" ? 64U : 0U;
    need((row.present & required) == required && (row.present & ~(required | optional)) == 0, "Closed operation fields differ");
    need(row.type < table::types.size() && !text(row.field).empty() && !text(row.key).empty() &&
        (text(row.flavor) == "weapon" || text(row.flavor) == "attachment"), "Operation labels/type differ");
    need(bit(row.present, 6) || !row.semantic_domain_unknown, "Absent operation boolean differs");
    if (dynamic) need(row.count_tag == 2 && row.count_type < table::types.size() && !text(row.named_count).empty() && row.fixed_count == 0,
        "Named count/reference differs");
    else if (fixed) need(row.count_tag == 1 && row.count_type == 0 && text(row.named_count).empty(), "Fixed count metadata differs");
    else need(row.count_tag == 0 && row.count_type == 0 && row.fixed_count == 0 && text(row.named_count).empty(), "Absent count differs");
    need(row.manual == 0, "Nonmanual operation has a manual reference");
}
static void ids_spans_element_canonicality()
{
    need(table::strings.size() == 1981 && table::extents.size() == 33 && table::integers.size() == 468 &&
        table::enum_members.size() == 500 && table::bitfields.size() == 5 && table::key_ids.size() == 1165 &&
        table::argument_ids.size() == 8 && table::direct_sites.size() == 31 && table::direct_owners.size() == 41 &&
        table::types.size() == 239 && table::structures.size() == 41 && table::operations.size() == 1213 && table::manuals.size() == 10,
        "Frozen finite table cardinalities differ");
    for (const auto id : table::key_ids) text(id);
    for (const auto id : table::argument_ids) text(id);
    for (const auto id : table::type_tags) text(id);
    for (const auto id : table::op_tags) text(id);
    for (const auto id : table::manual_tags) text(id);
    for (const auto& value : table::enum_members) text(value.name);
    for (const auto& value : table::bitfields) { text(value.name); need(value.value > 0 && value.value <= 64, "Bitfield width differs"); }
    std::size_t unexpanded = 0, known_pointer = table::types.size();
    std::size_t next_extent = 0, next_integer = 0, next_member = 0, next_bitfield = 0;
    for (std::size_t i = 0; i < table::types.size(); ++i)
    {
        const auto& row = table::types[i]; text(row.name); text(row.size_basis); text(row.conversion_basis);
        need(element_ok(row) && (row.kind != 3 || row.element_tag == 1), "Noncanonical element reference");
        if (row.element_tag == 2) ++unexpanded; // Descriptor count, not unique labels or invented layouts.
        if (row.kind == 1 && row.element_tag == 1) known_pointer = i;
        need(within(row.extents, table::extents.size()) && within(row.values, table::integers.size()) &&
            within(row.members, table::enum_members.size()) && within(row.bitfields, table::bitfields.size()), "Type span outside frozen table");
        need(row.extents.offset == next_extent && row.values.offset == next_integer &&
            row.members.offset == next_member && row.bitfields.offset == next_bitfield, "Type aggregate spans are not ordered/complete");
        next_extent += row.extents.count; next_integer += row.values.count;
        next_member += row.members.count; next_bitfield += row.bitfields.count;
        if (i) need(byte_less(text(table::types[i - 1].name), text(row.name)), "Type identities are not byte-sorted/unique");
    }
    need(next_extent == table::extents.size() && next_integer == table::integers.size() &&
        next_member == table::enum_members.size() && next_bitfield == table::bitfields.size(), "Orphaned type aggregate records");
    need(unexpanded == 30 && known_pointer < table::types.size(), "Exact unexpanded pointer descriptors differ");
    for (const auto& row : table::operations) operation_record(row);
    std::size_t next_argument = 0;
    for (const auto& row : table::manuals)
    {
        need(row.owner < table::structures.size() && row.tag < table::manual_tags.size() && within(row.arguments, table::argument_ids.size()), "Manual reference/span differs");
        need(row.arguments.offset == next_argument, "Ordered manual argument spans differ");
        next_argument += row.arguments.count;
        const auto tag = text(table::manual_tags[row.tag]);
        need(row.arguments.count == ((tag == "object" || tag == "entries") ? 2U : 0U), "Manual arity differs");
        if (row.arguments.count == 2)
        {
            const auto target = table::argument_ids[static_cast<std::size_t>(row.arguments.offset) + 1];
            need(find_structure(text(target)) < table::structures.size(), "Manual target structure missing");
        }
    }
    need(next_argument == table::argument_ids.size(), "Orphaned manual argument IDs");
    for (const auto& row : table::direct_sites) text(row.text);
    std::size_t next_op = 0, next_key = 0, next_site = 0;
    std::array<unsigned, 10> used_manuals{};
    for (std::size_t i = 0; i < table::structures.size(); ++i)
    {
        const auto& row = table::structures[i]; text(row.name); text(row.source);
        need(row.layout < table::types.size() && table::types[row.layout].name == row.name && row.first <= row.last,
            "Structure identity/layout/range differs");
        need(within(row.keys, table::key_ids.size()) && within(row.ops, table::operations.size()) && within(row.direct_sites, table::direct_sites.size()),
            "Structure span outside frozen table");
        need(row.ops.offset == next_op && row.keys.offset == next_key && row.direct_sites.offset == next_site, "Ordered aggregate spans differ");
        next_op += row.ops.count; next_key += row.keys.count; next_site += row.direct_sites.count;
        if (i) need(byte_less(text(table::structures[i - 1].name), text(row.name)), "Structure identities are not byte-sorted/unique");
        u32 last_site_line = 0;
        for (std::size_t j = 0; j < row.direct_sites.count; ++j)
        {
            const auto& site = table::direct_sites[static_cast<std::size_t>(row.direct_sites.offset) + j];
            need(site.line >= last_site_line && site.line >= row.first && site.line <= row.last, "Direct Source site order/range differs");
            last_site_line = site.line;
        }
        u32 last_line = 0;
        for (std::size_t j = 0; j < row.ops.count; ++j)
        {
            const auto& op = operation(row, j);
            need(op.line >= last_line && op.line >= row.first && op.line <= row.last, "Source operation order/range differs"); last_line = op.line;
            if (text(table::op_tags[op.tag]) == "MANUAL")
            {
                need(op.manual < used_manuals.size(), "Manual index outside exact finite set"); ++used_manuals[op.manual];
                need(table::manuals[op.manual].owner == i && table::manuals[op.manual].line == op.line, "Manual owner/site differs");
            }
        }
    }
    need(next_op == table::operations.size() && next_key == table::key_ids.size() && next_site == table::direct_sites.size(), "Unreferenced aggregate suffix");
    for (const auto count : used_manuals) need(count == 1, "Manual operation is duplicated or orphaned");
    std::array<unsigned, 41> direct_owners{};
    for (const auto& row : table::direct_owners)
    {
        need(row.owner < direct_owners.size() && within(row.items, table::direct_sites.size()), "Direct owner/span differs");
        need(same_span(row.items, table::structures[row.owner].direct_sites), "Direct owner does not alias structure span"); ++direct_owners[row.owner];
    }
    for (const auto count : direct_owners) need(count == 1, "Missing/duplicate direct-site owner");
    std::array<unsigned, 10> covered_manuals{}; std::array<bool, 41> covered_owners{};
    std::size_t next_manual_id = 0;
    for (const auto& row : table::manual_owners)
    {
        need(row.owner < table::structures.size() && within(row.items, table::manual_ids.size()), "Manual owner/span differs");
        need(!covered_owners[row.owner] && row.items.offset == next_manual_id, "Duplicate/out-of-order manual coverage owner");
        covered_owners[row.owner] = true; next_manual_id += row.items.count;
        for (std::size_t j = 0; j < row.items.count; ++j)
        {
            const auto id = table::manual_ids[static_cast<std::size_t>(row.items.offset) + j];
            need(id < covered_manuals.size() && table::manuals[id].owner == row.owner, "Coverage manual reference differs");
            ++covered_manuals[id];
        }
    }
    need(next_manual_id == table::manual_ids.size(), "Orphaned manual coverage suffix");
    for (const auto count : covered_manuals) need(count == 1, "Missing/duplicate manual coverage ID");
    // Different array lengths are deliberately handled separately, without type erasure.
    const auto pins_ok = [](const auto& pins) {
        for (std::size_t i = 0; i < pins.size(); ++i)
        {
            const auto& pin = pins[i];
            need(!text(pin.name).empty() && lower_hex(text(pin.sha256), 64), "Source hash label differs");
            for (std::size_t j = 0; j < i; ++j)
                need(pins[j].name != pin.name, "Duplicate Source pin name");
        }
    };
    pins_ok(table::source_pins); pins_ok(table::conversion_pins); pins_ok(table::manual_body_pins);
    for (const auto& row : table::provenance)
    {
        text(row.role); need(lower_hex(text(row.git_blob), 40) && lower_hex(text(row.sha256_lf), 64) && row.bytes_lf > 0 && row.bytes_lf <= 2097152,
            "Closed provenance record differs");
    }
    for (const auto& row : table::metadata) { text(row.pin); text(row.platform); text(row.json_revision); }
    // Local copies test THIS fixture's checks, not a production validator or ABI.
    need(within({static_cast<u32>(table::types.size()), 0}, table::types.size()) &&
        !within({static_cast<u32>(table::types.size()), 1}, table::types.size()) &&
        !within({(std::numeric_limits<u32>::max)(), 1}, table::types.size()), "Fixture span boundary check failed");
    auto changed = table::types[known_pointer]; changed.element = static_cast<u32>(table::types.size());
    need(!element_ok(changed), "Fixture one-past type ID check failed");
    changed = table::types[known_pointer]; const auto label = table::types[changed.element].name;
    changed.element_tag = 2; changed.element = label;
    need(!element_ok(changed), "Known-label tag1-to-tag2 noncanonicality escaped fixture check");
    changed.element_tag = 3; need(!element_ok(changed), "Unknown element tag escaped fixture check");
    changed.kind = 3; changed.element_tag = 2; need(!element_ok(changed), "Array label fallback escaped fixture check");
}
static void utf8_pool_bytes()
{
    std::size_t end = 0;
    for (std::size_t i = 0; i < table::strings.size(); ++i)
    {
        const auto span = table::strings[i]; need(within(span, sizeof table::string_pool) && span.offset == end, "String pool span/contiguity differs");
        const auto value = text(static_cast<u32>(i)); need(utf8(value), "Compiled string bytes are not strict NUL-free UTF8");
        need(i == 0 ? value.empty() : !value.empty(), "Present empty string ID differs");
        if (i) need(byte_less(text(static_cast<u32>(i - 1)), value), "String IDs are not UTF8-byte sorted/unique");
        end += span.count;
    }
    need(end == sizeof table::string_pool, "Compiled pool has unreferenced bytes");
    const auto& owner = structure("WeaponDef"); bool quoted_site = false;
    for (std::size_t i = 0; i < owner.direct_sites.count; ++i)
    {
        const auto& site = table::direct_sites[static_cast<std::size_t>(owner.direct_sites.offset) + i];
        if (site.line == 412) quoted_site = text(site.text) == R"(parse(&asset->overlay, data["overlay"], mem);)";
    }
    need(quoted_site, "Compiled quote/punctuation Source bytes differ");
    const char good[]{static_cast<char>(0xc3), static_cast<char>(0xa9)};
    const char overlong[]{static_cast<char>(0xc0), static_cast<char>(0xaf)};
    const char surrogate[]{static_cast<char>(0xed), static_cast<char>(0xa0), static_cast<char>(0x80)};
    need(utf8({good, sizeof good}) && !utf8({overlong, sizeof overlong}) && !utf8({surrogate, sizeof surrogate}) &&
        !utf8(std::string_view("\0", 1)), "Fixture UTF8 checker sentinels differ");
    // These authored bytes test the fixture checker only. An ASCII-only frozen
    // pool does NOT establish non-ASCII generator/emitter coverage in C++.
}
static bool allowed(const table::TypeRecord& owner, Integer value)
{
    need(within(owner.values, table::integers.size()), "Allowed values span differs");
    for (std::size_t i = 0; i < owner.values.count; ++i)
        if (equal(table::integers[static_cast<std::size_t>(owner.values.offset) + i], value)) return true;
    return false;
}
static Integer member(const table::TypeRecord& owner, std::string_view name)
{
    need(within(owner.members, table::enum_members.size()), "Declaration members span differs");
    for (std::size_t i = 0; i < owner.members.count; ++i)
    {
        const auto& row = table::enum_members[static_cast<std::size_t>(owner.members.offset) + i];
        if (text(row.name) == name) return row.value;
    }
    throw std::runtime_error("Declaration member missing");
}
static void ordered_records_aliases_manual_sites()
{
    need(table::type_tags.size() == 7 && table::op_tags.size() == 17 && table::manual_tags.size() == 8, "Closed tag counts differ");
    const std::string_view types[]{"object", "pointer", "enum", "array", "bool", "int", "float"};
    const std::string_view operations[]{"ASSET", "ASSET_ALLOC_ARR_MODVAL", "ASSET_ARR", "ASSET_FIELD_ARR",
        "FIELD", "FIELD_ALLOC_ARR", "FIELD_ARR", "FIELD_RENAME", "FXCOMBINED", "FXCOMBINED_ALLOC_ARR",
        "MANUAL", "OPTIONAL", "SCRIPT_STRING", "SCRIPT_STRING_ALLOC_ARR", "SCRIPT_STRING_ALLOC_ARR_MODVAL", "STRING", "STRING_ARR"};
    const std::string_view handlers[]{"object", "entries", "graphs", "definition", "original_graphs", "overrides", "unk_material", "internal_script"};
    for (std::size_t i = 0; i < 7; ++i) need(text(table::type_tags[i]) == types[i], "Type tag order differs");
    for (std::size_t i = 0; i < 17; ++i) need(text(table::op_tags[i]) == operations[i], "Operation tag order differs");
    for (std::size_t i = 0; i < 8; ++i) need(text(table::manual_tags[i]) == handlers[i], "Manual tag order differs");
    const auto& meta = table::metadata[0];
    need(meta.typed_structures == 41 && meta.macro_sites == 1203 && text(meta.pin) == "fab935826c898806855376662a8a03317b3ad8f1" &&
        text(meta.platform) == "Windows-x64-LLP64-default-pack8" && text(meta.json_revision) == "484483acad6d562306efc9b3c6d413404f1b1f8a", "Historical Source metadata differs");
    need(table::source_pins.size() == 6 && table::conversion_pins.size() == 3 && table::manual_body_pins.size() == 3 && table::provenance.size() == 4,
        "Provenance cardinalities differ");
    // Four Source provenance witnesses, not a second copy of the extraction rules.
    const struct { std::string_view role, blob, sha; u64 bytes; } provenance[]{
        {"schema", "99e084aeac3e26798a9b4349e22c245b5a15b664", "5e18fe147f2bbc55459f60c4e724dbdd15b86fe4bb23de92562016c2345813db", 262207},
        {"extraction_generator", "4717a82a21117be7f744bc6e0e6ce56cf9c7db92", "4ddfdf8a9c46b2d78af8ccc70f74524596c16a116f5d04423cfe7d6cb413f9e6", 24497},
        {"projection_generator", "cf33622aa09ccb871d92c059d3df4cfe19691a78", "35770c090a883e5edc2b28783a92d2954563b4fd1a62ca27949efbee54732939", 50953},
        {"body_validator", "86f6f6c42840913bddeda864053475884ab493fc", "820c8580549c3d0e5022e58d5f5bfc120d23db64b9f9f6e4513e05494c178626", 17221}};
    for (std::size_t i = 0; i < 4; ++i)
    {
        const auto& actual = table::provenance[i]; const auto& expected = provenance[i];
        need(text(actual.role) == expected.role && text(actual.git_blob) == expected.blob &&
            text(actual.sha256_lf) == expected.sha && actual.bytes_lf == expected.bytes, "Frozen Source provenance identity/order differs");
    }
    const auto& overlay = structure("ADSOverlay");
    need(text(overlay.source) == "weapondef.cpp" && overlay.first == 238 && overlay.last == 248 &&
        text(operation(overlay, 0).key) == "shader" && operation(overlay, 0).line == 239 &&
        text(operation(overlay, 1).key) == "shaderLowRes" && operation(overlay, 1).line == 240, "Source operation order/labels differ");
    const auto& attachment = structure("WeaponAttachment"); const auto& rename = operation(attachment, 6);
    need(text(table::op_tags[rename.tag]) == "FIELD_RENAME" && text(rename.key) == "weaponClass" && text(rename.field) == "weapClass" && rename.line == 702,
        "Renamed JSON key and native Source field collapsed");
    const auto& internal = operation(attachment, 2);
    need(text(operation(attachment, 0).key) == "szInternalName" && operation(attachment, 0).line == 696 &&
        text(table::op_tags[internal.tag]) == "MANUAL" && internal.line == 698 &&
        text(table::manual_tags[table::manuals[internal.manual].tag]) == "internal_script", "Internal script Source order differs");
    const auto& notes = structure("NoteTrackToSoundEntry");
    for (std::size_t i = 1; i <= 2; ++i)
    {
        const auto& op = operation(notes, i);
        need(op.count_tag == 2 && text(op.named_count) == "numSoundMappings" && text(table::types[op.count_type].name) == "unsigned int" &&
            op.line == 1041 + i, "Shared named count/type/order differs");
    }
    const auto& penetration = type("PenetrateType");
    need(equal(member(penetration, "PENETRATE_TYPE_MAXIMUM"), {false, 4}) &&
        equal(member(penetration, "PENETRATE_TYPE_TABLE_ENTRY_COUNT"), {false, 4}) &&
        equal(member(penetration, "PENETRATE_TYPE_COUNT"), {false, 6}) && allowed(penetration, {false, 4}) && !allowed(penetration, {false, 6}),
        "Enum aliases/sentinel declaration and allowed values collapsed");
    const auto& suit = type("SuitAnimType");
    need(equal(member(suit, "NUM_ANIM_SUIT_STATE"), {false, 4}) && equal(member(suit, "ANIM_SUIT_INVALID"), {false, 4}) && !allowed(suit, {false, 4}),
        "Two excluded sentinel aliases differ");
    need(table::manual_owners.size() == 3 && table::manual_ids.size() == 10, "Manual coverage cardinality differs");
    const std::string_view manual_owners[]{"WeaponDef", "WeaponCompleteDef", "WeaponAttachment"};
    for (std::size_t i = 0; i < 3; ++i) need(text(table::structures[table::manual_owners[i].owner].name) == manual_owners[i], "Manual owner Source order differs");
    const auto& bits = type("GfxDrawSurfFields"); need(within(bits.bitfields, table::bitfields.size()) && bits.bitfields.count == 5, "Bitfield metadata span differs");
    const std::string_view names[]{"objectId", "pad0", "tessellation", "pad1", "pad2"}; const u64 widths[]{16, 32, 2, 14, 64};
    for (std::size_t i = 0; i < 5; ++i)
    {
        const auto& field = table::bitfields[static_cast<std::size_t>(bits.bitfields.offset) + i];
        need(text(field.name) == names[i] && field.value == widths[i], "Bitfield name/width order differs");
    }
    need(bits.size == 16 && bits.align == 8 && bits.pack == 8 && text(bits.size_basis) == "reviewed-msvc-x64-uint64-bitfield-units",
        "Source layout data differs; this is not runtime ABI proof");
}
int main()
{
    const struct { const char* name; void (*run)(); } groups[]{
        {"fixed_width_sign_magnitude", fixed_width_sign_magnitude},
        {"ids_spans_element_canonicality", ids_spans_element_canonicality},
        {"utf8_pool_bytes", utf8_pool_bytes},
        {"ordered_records_aliases_manual_sites", ordered_records_aliases_manual_sites}};
    try
    {
        for (const auto& group : groups) { group.run(); std::cout << "PASS " << group.name << '\n'; }
        std::cout << "IW7_BODY_SCHEMA_CONSTANTS=4\n"; return 0;
    }
    catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 2; }
}
