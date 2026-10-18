#pragma once
// Inactive SAME-owned input dialect and relative Source trace only. No native
// parser, arena, FILE/route, builder, success token or engine ABI authority.
#include "native_pair_report.hpp"
#include "native_pair_body_schema.hpp"
#include <cmath>
#include <limits>

namespace iw7::neutral::player_pair_bodies
{
    namespace detail
    {
        namespace table = iw7::neutral::body_schema;
        using Json = nlohmann::ordered_json;
        struct BodyError : std::runtime_error
        {
            BodyError(const std::string& path, const char* reason) : std::runtime_error(path + ": " + reason) {}
        };
        inline void need(bool value, const std::string& path, const char* reason)
        {
            if (!value) throw BodyError(path, reason);
        }
        template<class T, std::size_t N>
        inline void span(const std::array<T, N>&, table::StringSpan value)
        {
            need(value.offset <= N && value.count <= N - value.offset, "Source", "table span differs");
        }
        inline std::string_view text(std::uint32_t id)
        {
            need(id < table::strings.size(), "Source", "string ID differs");
            const auto value = table::strings[id];
            need(value.offset <= sizeof(table::string_pool) && value.count <= sizeof(table::string_pool) - value.offset,
                "Source", "string span differs");
            return {table::string_pool + value.offset, value.count};
        }
        inline const table::TypeRecord& type(std::uint32_t id)
        {
            need(id < table::types.size(), "Source", "type ID differs");
            return table::types[id];
        }
        inline const table::TypeRecord& layout(std::string_view name)
        {
            for (const auto& value : table::types) if (text(value.name) == name) return value;
            throw BodyError("Source", "unknown type/layout");
        }
        inline std::string_view kind(const table::TypeRecord& value)
        {
            need(value.kind < table::type_tags.size(), "Source", "unknown type kind");
            return text(table::type_tags[value.kind]);
        }
        inline std::string_view element(const table::TypeRecord& value)
        {
            const auto k = kind(value);
            need((value.present & (1U << 2)) != 0, "Source", "element absent");
            if (value.element_tag == 1) return text(type(value.element).name);
            need(value.element_tag == 2 && k == "pointer", "Source", "unknown element tag");
            const auto name = text(value.element);
            for (const auto& known : table::types)
                need(text(known.name) != name, "Source", "noncanonical known element label");
            return name; // No invented layout for an unexpanded pointer label.
        }
        inline std::string_view operation(const table::Operation& op)
        {
            need(op.tag < table::op_tags.size(), "Source", "unknown operation tag");
            return text(table::op_tags[op.tag]);
        }
        inline bool integer(const Json& value)
        {
            return value.type() == Json::value_t::number_integer || value.type() == Json::value_t::number_unsigned;
        }
        inline table::Integer number(const Json& value, const std::string& path)
        {
            need(integer(value), path, "uncoerced target integer required");
            if (value.type() == Json::value_t::number_unsigned)
                return {false, value.get<Json::number_unsigned_t>()};
            const auto n = value.get<Json::number_integer_t>();
            return n < 0 ? table::Integer{true, static_cast<std::uint64_t>(-(n + 1)) + 1}
                         : table::Integer{false, static_cast<std::uint64_t>(n)};
        }
        inline bool less(table::Integer a, table::Integer b)
        {
            if (a.negative != b.negative) return a.negative;
            return a.negative ? a.magnitude > b.magnitude : a.magnitude < b.magnitude;
        }
        inline bool equal(table::Integer a, table::Integer b)
        {
            return a.negative == b.negative && a.magnitude == b.magnitude;
        }
        inline std::uint64_t count(const Json& value, const std::string& path)
        {
            const auto n = number(value, path);
            need(!n.negative, path, "nonnegative count required");
            return n.magnitude;
        }
        inline void scalar(const Json& value, std::string_view name, const std::string& path)
        {
            const auto& desc = layout(name);
            const auto k = kind(desc);
            if (k == "bool") need(value.is_boolean(), path, "literal boolean required");
            else if (k == "int" || k == "enum")
            {
                const auto n = number(value, path);
                need((desc.present & 48U) == 48U && !less(n, desc.minimum) && !less(desc.maximum, n),
                    path, "uncoerced target integer range required");
                if (k == "enum")
                {
                    if (desc.semantic_domain_unknown)
                        need(name == "WeaponChargeType" && desc.storage_domain_only,
                            path, "unknown semantic enum domain refused");
                    else
                    {
                        span(table::integers, desc.values);
                        bool found = false;
                        for (std::uint32_t i = 0; i < desc.values.count; ++i)
                            found = found || equal(n, table::integers[desc.values.offset + i]);
                        need(found, path, "declared nonsentinel enum value required");
                    }
                }
            }
            else if (k == "float")
            {
                static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559 &&
                    std::numeric_limits<float>::radix == 2 && std::numeric_limits<float>::digits == 24 &&
                    std::numeric_limits<float>::max_exponent == 128, "Pinned Python <f domain requires IEEE binary32");
                need(value.is_number(), path, "uncoerced numeric value required");
                const auto n = value.get<double>();
                const auto maximum = static_cast<double>((std::numeric_limits<float>::max)());
                // Python struct.pack('<f') rounds values just above FLT_MAX to
                // signed FLT_MAX until this halfway boundary. Do not cast an
                // out-of-range C++ floating value merely to test its overflow.
                constexpr double overflow = 0x1.ffffffp+127;
                need(std::isfinite(n) && std::abs(n) < overflow, path, "finite floating target required");
                const auto converted = n > maximum ? (std::numeric_limits<float>::max)()
                    : n < -maximum ? -(std::numeric_limits<float>::max)() : static_cast<float>(n);
                need(std::isfinite(converted) && (n == 0 || converted != 0), path, "nonzero floating target underflow refused");
            }
            else throw BodyError(path, "unsupported scalar target");
        }
        inline void scalar(const Json& value, std::uint32_t id, const std::string& path)
        {
            scalar(value, text(type(id).name), path);
        }
        inline void array(const Json& value, std::uint64_t size, const std::string& path)
        {
            need(value.is_array() && value.size() == size, path, "exact array cardinality required");
        }
        inline void string(const Json& value, const std::string& path, bool nullable = true, bool empty = false)
        {
            if (value.is_null() && nullable) return;
            need(value.is_string(), path, "string required");
            const auto& s = value.get_ref<const Json::string_t&>();
            need(s.find('\0') == std::string::npos && (empty || !s.empty()), path, "NUL-free supported string shape required");
        }

        // Both the public SAX guard and DOM callback count values/containers,
        // never keys. Lexer/number/string temporaries may allocate first.
        struct Bounds
        {
            struct Frame { bool array; std::size_t elements{}; std::set<std::string> keys; };
            std::vector<Frame> frames;
            std::size_t nodes{}, max_depth{}, max_array{};
            const char* path;
            explicit Bounds(const char* label) : path(label) {}
            void start_value(std::size_t depth)
            {
                need(depth == frames.size() && depth <= 64, path, "JSON depth bound exceeded");
                need(nodes < 32768, path, "JSON node bound exceeded");
                ++nodes; max_depth = (std::max)(max_depth, depth);
                if (!frames.empty() && frames.back().array)
                {
                    need(frames.back().elements < 8192, path, "JSON array bound exceeded");
                    ++frames.back().elements; max_array = (std::max)(max_array, frames.back().elements);
                }
            }
            void key(const std::string& s)
            {
                need(!frames.empty() && !frames.back().array, path, "JSON key event differs");
                need(s.find('\0') == std::string::npos, path, "decoded NUL refused");
                need(frames.back().keys.insert(s).second, path, "Duplicate decoded key");
            }
            void end(bool is_array)
            {
                need(!frames.empty() && frames.back().array == is_array, path, "JSON container closure differs");
                frames.pop_back();
            }
        };
        struct SaxGuard : Bounds
        {
            explicit SaxGuard(const char* label) : Bounds(label) {}
            bool value() { start_value(frames.size()); return true; }
            bool null() { return value(); }
            bool boolean(bool) { return value(); }
            bool number_integer(Json::number_integer_t) { return value(); }
            bool number_unsigned(Json::number_unsigned_t) { return value(); }
            bool number_float(Json::number_float_t n, const Json::string_t& lexeme)
            {
                bool nonzero = false;
                for (const auto c : lexeme)
                {
                    if (c == 'e' || c == 'E') break;
                    nonzero = nonzero || (c >= '1' && c <= '9');
                }
                need(std::isfinite(n) && (n != 0 || !nonzero), path, "nonzero JSON floating literal underflow refused");
                return value(); // -0.0/0e-9999 are legitimate zeros, not integers.
            }
            bool string(Json::string_t& s)
            {
                need(s.find('\0') == std::string::npos, path, "decoded NUL refused"); return value();
            }
            bool binary(Json::binary_t&) { throw BodyError(path, "JSON binary refused"); }
            bool start_object(std::size_t) { start_value(frames.size()); frames.push_back({false, 0, {}}); return true; }
            bool start_array(std::size_t) { start_value(frames.size()); frames.push_back({true, 0, {}}); return true; }
            bool key(Json::string_t& s) { Bounds::key(s); return true; }
            bool end_object() { end(false); return true; }
            bool end_array() { end(true); return true; }
            bool parse_error(std::size_t, const std::string&, const nlohmann::detail::exception&) { return false; }
        };
        struct DomGuard : Bounds
        {
            explicit DomGuard(const char* label) : Bounds(label) {}
            bool operator()(int depth, Json::parse_event_t event, Json& value)
            {
                using Event = Json::parse_event_t;
                need(depth >= 0, path, "JSON negative depth");
                const auto d = static_cast<std::size_t>(depth);
                if (event == Event::object_start || event == Event::array_start)
                {
                    start_value(d); frames.push_back({event == Event::array_start, 0, {}});
                }
                else if (event == Event::key)
                {
                    need(d == frames.size() && value.is_string(), path, "JSON key depth differs");
                    key(value.get_ref<const Json::string_t&>());
                }
                else if (event == Event::value)
                {
                    need(!value.is_structured(), path, "JSON scalar event differs");
                    if (value.is_string()) need(value.get_ref<const Json::string_t&>().find('\0') == std::string::npos, path, "decoded NUL refused");
                    start_value(d);
                }
                else
                {
                    need((event == Event::object_end || event == Event::array_end) && d + 1 == frames.size(), path, "JSON end depth differs");
                    end(event == Event::array_end);
                }
                return true; // No DOM callback false/discard path.
            }
        };
        inline Json decode(std::string_view raw, const char* path)
        {
            need(!raw.empty() && raw.size() <= 2097152, path, "body raw bound differs");
            need(raw.size() < 3 || raw.substr(0, 3) != std::string_view("\xef\xbb\xbf", 3), path, "body BOM refused");
            need(raw.find('\0') == std::string_view::npos, path, "body raw NUL refused");
            SaxGuard sax(path);
            need(Json::sax_parse(raw.begin(), raw.end(), &sax, Json::input_format_t::json, true, false, false),
                path, "strict SAX JSON refused");
            need(sax.frames.empty() && sax.nodes > 0, path, "SAX event closure differs");
            DomGuard dom(path);
            auto result = Json::parse(raw.begin(), raw.end(),
                [&dom](int depth, Json::parse_event_t event, Json& value) { return dom(depth, event, value); }, true, false, false);
            need(dom.frames.empty() && dom.nodes == sax.nodes && dom.max_depth == sax.max_depth && dom.max_array == sax.max_array,
                path, "two-pass JSON bounds differ");
            return result;
        }

        struct Event { std::string path, type; std::uint64_t offset, bytes, alignment; };
        struct Trace
        {
            std::uint64_t offset{}, cells{}, script_entries{}, string_bytes{};
            std::vector<Event> events;
            bool alignment;
            explicit Trace(bool enabled = true) : alignment(enabled) {}
            void allocate(std::string_view name, std::uint64_t count_value, const std::string& path,
                std::uint64_t size = 0, bool allocated_cells = false, std::string_view effective = {})
            {
                const auto& desc = layout(name);
                const auto unit = size ? size : desc.size;
                const auto align = (std::max)(desc.align, effective.empty() ? std::uint64_t{1} : layout(effective).align);
                need(unit > 0 && align > 0, path, "known positive Source size/alignment required");
                if (count_value == 0) return;
                constexpr auto maximum = (std::numeric_limits<std::uint64_t>::max)();
                need(count_value <= maximum / unit, path, "allocation multiplication overflow");
                const auto total = unit * count_value;
                need(offset <= maximum - total, path, "allocation addition overflow");
                if (alignment) need(offset % align == 0, path, "legacy cursor misalignment");
                if (allocated_cells)
                {
                    need(count_value <= 8192 && cells <= 8192 - count_value, path, "two-root aggregate native array-cell bound exceeded");
                    cells += count_value;
                }
                events.push_back({path, std::string(name), offset, total, align}); offset += total;
            }
            void string(std::string_view value, const std::string& path)
            {
                need(value.size() < (std::numeric_limits<std::uint64_t>::max)(), path, "string byte addition overflow");
                const auto bytes = static_cast<std::uint64_t>(value.size()) + 1;
                allocate("char", bytes, path);
                constexpr std::uint64_t cap = 2 * 2097152ULL + 65536;
                need(bytes <= cap && string_bytes <= cap - bytes, path, "two-root string storage bound exceeded");
                string_bytes += bytes;
            }
            void script(const std::string& path)
            {
                need(script_entries < 65536, path, "two-root script-map entry bound exceeded"); ++script_entries;
            }
        };
        inline void cstring(const Json& value, const std::string& path, Trace& trace,
            bool empty = false, bool script = false, bool nullable = true)
        {
            string(value, path, nullable, empty);
            if (!value.is_null())
            {
                trace.string(value.get_ref<const Json::string_t&>(), path);
                if (script) trace.script(path);
            }
        }
        inline void asset(const Json& value, std::string_view name, const std::string& path, Trace& trace, bool full = false)
        {
            string(value, path);
            if (!value.is_null())
            {
                trace.allocate(name, 1, path, full ? 0 : 8);
                trace.string(value.get_ref<const Json::string_t&>(), path + ".name");
            }
        }
        inline void closed(const Json& value, const std::set<std::string>& keys, const std::string& path)
        {
            need(value.is_object() && value.size() == keys.size(), path, "exact closed object keys required");
            for (const auto& key : keys) need(value.contains(key), path, "exact closed object keys required");
        }
        inline void fx(const Json& value, const std::string& path, Trace& trace)
        {
            if (value.is_null()) return;
            closed(value, {"type", "fx"}, path);
            need(integer(value.at("type")) && count(value.at("type"), path) <= 1, path, "FX tag0 or1 required");
            string(value.at("fx"), path + ".fx", false);
            trace.allocate("char", 1, path, 8, false, "FxEffectDef");
            trace.string(value.at("fx").get_ref<const Json::string_t&>(), path + ".fx");
        }
        inline std::string index(const std::string& path, std::size_t i) { return path + '[' + std::to_string(i) + ']'; }
        inline std::array<std::uint64_t, 2> graphs(const Json& value, const std::string& path)
        {
            array(value, 2, path); std::array<std::uint64_t, 2> result{};
            for (std::size_t i = 0; i < 2; ++i)
            {
                const auto& graph = value[i];
                if (graph.is_null()) continue;
                const auto p = index(path, i);
                need(graph.is_array() && !graph.empty() && graph.size() <= 65535, p, "null or positive uint16 graph required");
                result[i] = graph.size();
                for (const auto& knot : graph) { array(knot, 2, p); for (const auto& cell : knot) scalar(cell, "float", p); }
            }
            return result;
        }
        inline const table::Structure& structure(std::string_view name)
        {
            for (const auto& value : table::structures) if (text(value.name) == name) return value;
            throw BodyError("Source", "unknown structure");
        }
        inline void walk(std::string_view, const Json&, const std::string&, Trace&, const Json* = nullptr);
        inline void shared_groups(const table::Structure& desc, const Json& data, const std::string& path)
        {
            span(table::operations, desc.ops);
            for (std::uint32_t i = 0; i < desc.ops.count; ++i)
            {
                const auto& rule = table::operations[desc.ops.offset + i];
                if (rule.count_tag != 2) continue;
                const auto& value = data.at(std::string(text(rule.key)));
                if (!value.is_null()) need(value.is_array() && !value.empty(), path, "positive dynamic arrays required");
                for (std::uint32_t j = 0; j < desc.ops.count; ++j)
                {
                    const auto& other = table::operations[desc.ops.offset + j];
                    if (other.count_tag != 2 || other.named_count != rule.named_count) continue;
                    const auto& peer = data.at(std::string(text(other.key)));
                    need(value.is_null() == peer.is_null(), path, "shared count requires one explicit null policy");
                    if (!value.is_null())
                    {
                        need(peer.is_array() && value.size() == peer.size(), path, "shared count lengths differ");
                        need((other.present & (1U << 5)) != 0, "Source", "named count type absent");
                        scalar(Json(value.size()), other.count_type, path + '.' + std::string(text(other.key)));
                    }
                }
            }
        }
        inline void array_rule(const table::Operation& rule, const Json& data, const std::string& path, Trace& trace)
        {
            const auto& value = data.at(std::string(text(rule.key)));
            const auto& desc = type(rule.type); const auto op = operation(rule);
            const auto inlined = kind(desc) == "array";
            need(rule.count_tag == 1 || rule.count_tag == 2, "Source", "unknown array count tag");
            if (value.is_null()) { need(!inlined, path, "inline arrays cannot be null/defaulted"); return; }
            const auto n = rule.count_tag == 1 ? rule.fixed_count : static_cast<std::uint64_t>(value.size());
            array(value, n, path); need(n > 0, path, "zero pointer arrays normalize to null and are unsupported");
            const auto elem = element(desc);
            if (inlined)
            {
                span(table::extents, desc.extents);
                need(desc.extents.count == 1 && table::extents[desc.extents.offset] == n, path, "native inline extent differs");
            }
            else trace.allocate(elem, n, path, 0, true);
            for (std::size_t i = 0; i < value.size(); ++i)
            {
                const auto p = index(path, i); const auto& item = value[i];
                if (op.substr(0, 5) == "ASSET") asset(item, element(layout(elem)), p, trace);
                else if (op.substr(0, 13) == "SCRIPT_STRING") cstring(item, p, trace, false, true);
                else if (op.substr(0, 10) == "FXCOMBINED") fx(item, p, trace);
                else if (op == "STRING_ARR") cstring(item, p, trace);
                else scalar(item, elem, p);
            }
        }
        inline void manual(const table::Operation& op, const table::Structure& owner, const Json& data,
            const std::string& path, Trace& trace, const Json* parent)
        {
            need(op.manual < table::manuals.size(), "Source", "manual ID differs");
            const auto& m = table::manuals[op.manual];
            need(m.owner < table::structures.size() && &table::structures[m.owner] == &owner && m.line == op.line &&
                m.tag < table::manual_tags.size(), "Source", "manual Source site differs");
            span(table::argument_ids, m.arguments);
            const auto tag = text(table::manual_tags[m.tag]);
            need(m.arguments.count == (tag == "object" || tag == "entries" ? 2U : 0U), "Source", "manual argument count differs");
            const auto arg = [&m](std::uint32_t i)
            {
                need(i < m.arguments.count, "Source", "manual argument missing"); return text(table::argument_ids[m.arguments.offset + i]);
            };
            if (tag == "object") walk(arg(1), data.at(std::string(arg(0))), path + '.' + std::string(arg(0)), trace, parent);
            else if (tag == "entries")
            {
                const auto& value = data.at(std::string(arg(0))); const auto p = path + '.' + std::string(arg(0));
                if (!value.is_null())
                {
                    need(value.is_array() && !value.empty() && value.size() <= 65535, p, "positive outer uint16 cast length required");
                    trace.allocate(arg(1), value.size(), p, 0, true);
                    for (std::size_t i = 0; i < value.size(); ++i) walk(arg(1), value[i], index(p, i), trace, parent);
                }
            }
            else if (tag == "graphs")
            {
                const auto counts = graphs(data.at("accuracyGraphKnots"), path + ".accuracyGraphKnots");
                for (std::size_t i = 0; i < 2; ++i) trace.allocate("vec2_t", counts[i], index(path + ".accuracyGraphKnots", i), 0, true);
            }
            else if (tag == "definition")
            {
                trace.allocate("WeaponDef", 1, path + ".weapDef"); walk("WeaponDef", data.at("weapDef"), path + ".weapDef", trace, &data);
            }
            else if (tag == "original_graphs")
            {
                need(parent != nullptr, path, "parent graphs required");
                const auto counts = graphs(parent->at("accuracyGraphKnots"), path + ".parent.accuracyGraphKnots");
                const auto& names = data.at("accuracyGraphName"); const auto& originals = data.at("originalAccuracyGraphKnotCount");
                array(names, 2, path + ".accuracyGraphName"); array(originals, 2, path + ".originalAccuracyGraphKnotCount");
                const std::size_t highest = counts[1] ? 2 : counts[0] ? 1 : 0;
                const Json* knots = highest ? &data.at("originalAccuracyGraphKnots") : nullptr;
                if (highest) array(*knots, highest, path + ".originalAccuracyGraphKnots");
                for (std::size_t i = 0; i < 2; ++i)
                {
                    const auto p = index(path + ".originalAccuracyGraphKnots", i);
                    const auto nullable = counts[i] == 0 && integer(originals[i]) && equal(number(originals[i], p), {false, 0});
                    string(names[i], path + ".accuracyGraphName", nullable, true);
                    if (!names[i].is_null()) trace.string(names[i].get_ref<const Json::string_t&>(), index(path + ".accuracyGraphName", i));
                    trace.allocate("vec2_t", counts[i], p, 0, true);
                    if (i < highest)
                    {
                        if (!counts[i]) need((*knots)[i].is_null(), p, "zero original graph hole must be null");
                        else { array((*knots)[i], counts[i], p); for (const auto& knot : (*knots)[i]) { array(knot, 2, p); for (const auto& cell : knot) scalar(cell, "float", p); } }
                    }
                    scalar(originals[i], "unsigned short", path + ".originalAccuracyGraphKnotCount");
                    need(count(originals[i], p) == counts[i], p, "original count must equal parent allocation count");
                }
            }
            else if (tag == "overrides")
            {
                constexpr std::array<std::string_view, 3> keys{"animOverrides", "sfxOverrides", "vfxOverrides"};
                constexpr std::array<std::string_view, 3> names{"AnimOverride", "SFXOverride", "VFXOverride"};
                for (const auto key : keys) array(data.at(std::string(key)), 21, path + '.' + std::string(key));
                for (std::size_t i = 0; i < 21; ++i)
                    for (std::size_t j = 0; j < 3; ++j) walk(names[j], data.at(std::string(keys[j]))[i], index(path + '.' + std::string(keys[j]), i), trace, parent);
            }
            else if (tag == "unk_material") asset(data.at("unk0").at("material"), "Material", path + ".unk0.material", trace, true);
            else if (tag == "internal_script") trace.script(path + ".internalName");
            else throw BodyError(path, "unknown manual Source handler");
        }
        inline void walk(std::string_view name, const Json& data, const std::string& path, Trace& trace, const Json* parent)
        {
            const auto& desc = structure(name); span(table::key_ids, desc.keys); span(table::operations, desc.ops);
            std::set<std::string> keys;
            for (std::uint32_t i = 0; i < desc.keys.count; ++i) keys.emplace(text(table::key_ids[desc.keys.offset + i]));
            if (name == "WeaponDef")
            {
                need(parent != nullptr, path, "parent graphs required");
                const auto counts = graphs(parent->at("accuracyGraphKnots"), path + ".parent.accuracyGraphKnots");
                if (!counts[0] && !counts[1]) keys.erase("originalAccuracyGraphKnots");
            }
            closed(data, keys, path);
            if (name == "WeaponDef")
            {
                std::set<std::string> unknown{"material"};
                for (std::uint32_t i = 0; i < desc.ops.count; ++i)
                {
                    const auto key = text(table::operations[desc.ops.offset + i].key);
                    if (key.substr(0, 5) == "unk0.") unknown.emplace(key.substr(5));
                }
                closed(data.at("unk0"), unknown, path + ".unk0");
            }
            shared_groups(desc, data, path);
            for (std::uint32_t i = 0; i < desc.ops.count; ++i)
            {
                const auto& op = table::operations[desc.ops.offset + i]; const auto tag = operation(op);
                if (tag == "MANUAL") { manual(op, desc, data, path, trace, parent); continue; }
                need((op.present & 10U) == 10U, "Source", "operation key/type absent");
                const auto key = text(op.key); const auto p = path + '.' + std::string(key);
                const auto& value = key.substr(0, 5) == "unk0." ? data.at("unk0").at(std::string(key.substr(5))) : data.at(std::string(key));
                if (tag == "FIELD" || tag == "FIELD_RENAME") scalar(value, op.type, p);
                else if (tag == "STRING") cstring(value, p, trace, text(op.flavor) == "weapon");
                else if (tag == "SCRIPT_STRING") cstring(value, p, trace, false, true);
                else if (tag == "ASSET") asset(value, element(type(op.type)), p, trace);
                else if (tag == "FXCOMBINED") fx(value, p, trace);
                else if (tag == "OPTIONAL")
                {
                    if (!value.is_null()) { const auto target = element(type(op.type)); trace.allocate(target, 1, p); walk(target, value, p, trace, parent); }
                }
                else if (tag.find("ARR") != std::string_view::npos) array_rule(op, data, p, trace);
                else throw BodyError(p, "unknown generated Source operation");
            }
        }
        inline Trace inspect(const Json& weapon, const Json& attachment, bool alignment = true)
        {
            Trace trace(alignment); trace.allocate("WeaponCompleteDef", 1, "weapon");
            walk("WeaponCompleteDef", weapon, "weapon", trace);
            trace.allocate("WeaponAttachment", 1, "attachment"); walk("WeaponAttachment", attachment, "attachment", trace);
            return trace;
        }
    }

    inline void validate_owned_pair_bodies(const player_pair_input::OwnedInput& owner)
    {
        // Real J9 raw/report validation wins before either body is decoded.
        player_pair_report::validate_owned_report(owner);
        // J9 returns no DOM/authority. Reuse its bounded parser on the SAME raw
        // report solely to read the already-validated names and slot metadata.
        player_pair_report::detail::ReportGuard report_guard;
        const auto metadata = player_pair_report::detail::parse_report(owner.bytes(player_pair_input::Role::report), report_guard);
        const auto weapon = detail::decode(owner.bytes(player_pair_input::Role::weapon), "weapon");
        const auto attachment = detail::decode(owner.bytes(player_pair_input::Role::attachment), "attachment");
        detail::inspect(weapon, attachment, false); // Every shape/domain/demand before alignment.
        detail::need(weapon.at("szInternalName") == metadata.at("weapon"), "weapon.szInternalName", "private identity differs");
        detail::need(attachment.at("szInternalName") == metadata.at("pap_attachment"), "attachment.szInternalName", "private identity differs");
        detail::need(detail::integer(weapon.at("weapDef").at("weapType")) && detail::count(weapon.at("weapDef").at("weapType"), "weapon.weapDef.weapType") == 1,
            "weapon.weapDef.weapType", "neutral BULLET1 required");
        detail::need(detail::integer(attachment.at("weaponType")) && detail::count(attachment.at("weaponType"), "attachment.weaponType") == 0,
            "attachment.weaponType", "neutral NONE0 required");
        detail::need(attachment.at("papAttachment").is_boolean() && attachment.at("papAttachment").get<bool>(), "attachment.papAttachment", "literal true PAP flag required");
        constexpr std::array<std::string_view, 6> slots{"attachments", "attachments2", "attachments3", "attachments4", "attachments5", "attachments6"};
        std::vector<std::string_view> matches;
        const auto w = metadata.at("weapon").get<std::string>(); const auto a = metadata.at("pap_attachment").get<std::string>();
        for (const auto key : slots)
            for (const auto& value : weapon.at(std::string(key)))
            {
                if (value == a) matches.push_back(key);
                detail::need(value != ',' + a && value != w && value != ',' + w, "weapon.attachments", "private identity alias or wrong association");
            }
        detail::need(matches.size() == 1 && matches[0] == metadata.at("pap_attachment_slot").get<std::string>(),
            "weapon.attachments", "one private PAP association in declared slot required");
        detail::inspect(weapon, attachment, true);
    }
}
