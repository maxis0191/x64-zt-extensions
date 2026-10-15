#pragma once
// Private adaptation of the pinned IW7 dependency walkers. Source-only until a
// distinct CPP cohort qualifies it. Include after the pinned native structs.
#include <array>
#include <cstdint>
#include <cstring>
#include <limits>
#include <new>
#include <string>
#include <string_view>
#include <vector>

namespace zonetool::iw7
{
#include "native_definition_access.hpp"
}

namespace zonetool::iw7::neutral_dependencies
{
    inline constexpr char weapon_name[] = "sdk_shredder_clone_zm";
    inline constexpr char attachment_name[] = "sdk_shredder_clone_pap_zm";
    enum class Owner { weapon, attachment };
    inline const char* owner_name(Owner owner)
    { return owner == Owner::weapon ? weapon_name : attachment_name; }
    struct Origin { const char* path; unsigned index = 0; };
    struct Reference { int type; std::string name; bool owned; };
    struct Edge { size_t reference; Owner owner; std::string path; };
    struct Row { int type; std::string_view name; };
    using Copy = bool (*)(void*, const void*, size_t, void*);
    inline bool av_copy(void* destination, const void* source, size_t bytes, void*)
    { return player_definition_access::copy(destination, source, bytes); }

    // Production arithmetic primitive also allows independent boundary fixtures
    // for caps that a stricter, earlier cap can dominate in a complete graph.
    struct Budget
    {
        size_t occurrences = 0, external = 0, edges = 0, text = 0, manifest = 256;
        bool permits(bool new_external, bool new_edge, size_t add_text, size_t add_manifest) const
        {
            return occurrences < 8192 && external <= 4096 && (!new_external || external < 4096) &&
                edges <= 8192 && (!new_edge || edges < 8192) && text <= 1048576 && manifest <= 1048576 &&
                add_text <= 1048576 - text && add_manifest <= 1048576 - manifest;
        }
    };

    // This closed policy proves only these three zero-body reference paths.
    // See NEUTRAL-DEPENDENCIES.md. Recognition by a walker is not support.
    inline bool reference_supported(int type)
    { return type == ASSET_TYPE_FX || type == ASSET_TYPE_VFX || type == ASSET_TYPE_RETICLE; }

    class Collector
    {
    public:
        static constexpr size_t max_occurrences = 8192, max_external = 4096;
        static constexpr size_t max_edges = 8192, max_text = 1048576, max_manifest = 1048576;
        static constexpr size_t max_elements = 8192, max_dynamic = 64;
        explicit Collector(Copy copy = av_copy, void* context = nullptr) : copy_(copy), context_(context) {}
        Collector(const Collector&) = delete;
        Collector& operator=(const Collector&) = delete;
        bool good() const { return error_ == nullptr; }
        const char* error() const { return error_; }
        bool reject(const char* reason) { if (!error_) error_ = reason; return false; }
        bool begin(Owner owner, const char* name)
        {
            if (!good() || frozen_ || roots_ >= 2 ||
                owner != (roots_ == 0 ? Owner::weapon : Owner::attachment)) return reject("owner order");
            std::array<char, 512> text{}; size_t length = 0;
            if (!read_name(name, text, length) || std::string_view(text.data(), length) != owner_name(owner))
                return reject("private owner identity");
            owner_ = owner; ++roots_; return true;
        }
        bool required(bool value) { return value || reject("missing parsed root or array"); }
        bool count(size_t count, bool dynamic)
        {
            if (!good() || frozen_ || (dynamic && count > max_dynamic) || count > max_elements - elements_)
                return reject("element budget");
            elements_ += count; return true;
        }
        bool fx_kind(FxCombinedType kind)
        { return kind == FX_COMBINED_FX || kind == FX_COMBINED_VFX || reject("FX discriminant"); }
        bool asset(int type, const char* name, Origin origin)
        {
            if (!good() || frozen_ || roots_ == 0 || budget_.occurrences == max_occurrences)
                return reject("occurrence budget or state");
            std::array<char, 512> text{}; size_t length = 0;
            std::array<char, 257> path{}; size_t path_length = 0;
            if (!read_name(name, text, length) || !read_origin(origin, path, path_length)) return false;
            const std::string_view key(text.data(), length), field(path.data(), path_length);
            const bool owned = (type == ASSET_TYPE_WEAPON && key == weapon_name) ||
                (type == ASSET_TYPE_ATTACHMENT && key == attachment_name);
            // Any private root name with the wrong type must not become external.
            if (!owned && (key == weapon_name || key == attachment_name || !reference_supported(type)))
                return reject("unsupported external type or private type mismatch");
            size_t ref = 0;
            while (ref < references_.size() && !(references_[ref].type == type && references_[ref].name == key)) ++ref;
            const bool new_ref = ref == references_.size();
            bool new_edge = true;
            for (const auto& edge : edges_)
                if (edge.reference == ref && edge.owner == owner_ && edge.path == field) { new_edge = false; break; }
            const size_t add_text = (new_ref ? length + 1 : 0) + (new_edge ? path_length + 1 : 0);
            // Includes worst-case JSON escaping, owner identity and object syntax.
            const size_t add_manifest = (new_ref ? 6 * length + 128 : 0) +
                (new_edge ? 6 * path_length + 256 : 0);
            if (!budget_.permits(new_ref && !owned, new_edge, add_text, add_manifest)) return reject("graph budget");
            // All validation and accounting checks precede record/string allocation.
            try
            {
                if (new_ref) references_.push_back({type, std::string(key), owned});
                if (new_edge) edges_.push_back({ref, owner_, std::string(field)});
            }
            catch (const std::bad_alloc&) { return reject("local allocation"); }
            ++budget_.occurrences; if (new_ref && !owned) ++budget_.external;
            if (new_edge) ++budget_.edges;
            budget_.text += add_text; budget_.manifest += add_manifest;
            return true;
        }
        bool freeze()
        {
            if (!good() || frozen_ || roots_ != 2) return reject("incomplete pair");
            frozen_ = true; return true;
        }
        // Exact deterministic rows, no allocation and no ignore_assets access.
        // Call after freeze; missing, extra, reordered and private rows fail closed.
        bool verify_rows(const Row* rows, size_t count) const
        {
            if (!good() || !frozen_ || count != budget_.external || (count && !rows)) return false;
            size_t index = 0;
            for (const auto& ref : references_) if (!ref.owned)
            {
                if (rows[index].type != ref.type || rows[index].name != ref.name) return false;
                ++index;
            }
            return true;
        }
        bool frozen() const { return good() && frozen_; }
        size_t occurrences() const { return budget_.occurrences; }
        size_t external_count() const { return budget_.external; }
        size_t text_bytes() const { return budget_.text; }
        size_t manifest_bytes() const { return budget_.manifest; }
        const std::vector<Reference>& references() const { return references_; }
        const std::vector<Edge>& edges() const { return edges_; }
    private:
        static bool utf8(std::string_view value)
        {
            for (size_t i = 0; i < value.size();)
            {
                const auto first = static_cast<unsigned char>(value[i++]);
                if (first < 0x20 || first == 0x7f) return false;
                if (first < 0x80) continue;
                unsigned remaining = 0, code = 0, minimum = 0;
                if (first >= 0xc2 && first <= 0xdf) { remaining = 1; code = first & 31; minimum = 0x80; }
                else if (first >= 0xe0 && first <= 0xef) { remaining = 2; code = first & 15; minimum = 0x800; }
                else if (first >= 0xf0 && first <= 0xf4) { remaining = 3; code = first & 7; minimum = 0x10000; }
                else return false;
                if (remaining > value.size() - i) return false;
                while (remaining--) { const auto next = static_cast<unsigned char>(value[i++]);
                    if ((next & 0xc0) != 0x80) return false; code = (code << 6) | (next & 63); }
                if (code < minimum || code > 0x10ffff || (code >= 0xd800 && code <= 0xdfff) ||
                    (code >= 0x80 && code <= 0x9f)) return false;
            }
            return true;
        }
        bool read_name(const char* input, std::array<char, 512>& output, size_t& length)
        {
            if (!input || !copy_) return reject("missing name/copy");
            const auto base = reinterpret_cast<std::uintptr_t>(input);
            for (length = 0; length < output.size(); ++length)
            {
                if (length > (std::numeric_limits<std::uintptr_t>::max)() - base ||
                    !copy_(&output[length], reinterpret_cast<const void*>(base + length), 1, context_))
                    return reject("name copy");
                if (output[length] == 0)
                {
                    const std::string_view name(output.data(), length);
                    if (!length || output[0] == ',' || name == "default" || name == "$default" || !utf8(name))
                        return reject("name encoding/default");
                    return true;
                }
            }
            return reject("name NUL budget");
        }
        bool read_origin(Origin origin, std::array<char, 257>& output, size_t& length)
        {
            // Origin templates are production string literals, never asset bytes.
            if (!origin.path || !*origin.path) return reject("missing origin");
            size_t depth = 1; bool substituted = false;
            for (size_t i = 0; i <= 256 && origin.path[i]; ++i)
            {
                const char c = origin.path[i];
                if (c == '.' && ++depth > 32) return reject("origin depth");
                if (c == '[' && origin.path[i + 1] == ']')
                {
                    if (++depth > 32 || substituted || origin.index >= max_elements) return reject("origin index/depth");
                    substituted = true;
                    char digits[16]{}; size_t n = 0; unsigned index = origin.index;
                    do { digits[n++] = static_cast<char>('0' + index % 10); index /= 10; } while (index);
                    if (length + n + 2 > 256) return reject("origin length");
                    output[length++] = '['; while (n) output[length++] = digits[--n]; output[length++] = ']';
                    ++i; continue;
                }
                if (length == 256 || !((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
                    (c >= '0' && c <= '9') || c == '_' || c == '.')) return reject("origin syntax/length");
                output[length++] = c;
            }
            if (!length || length > 256) return reject("origin length");
            return true;
        }
        Copy copy_; void* context_; Owner owner_ = Owner::weapon;
        const char* error_ = nullptr;
        size_t roots_ = 0, elements_ = 0;
        Budget budget_;
        bool frozen_ = false;
        std::vector<Reference> references_;
        std::vector<Edge> edges_;
    };

    // Only the legacy adapter has a zone. It forwards the original sequence and
    // deliberately preserves the old invalid-discriminant else-as-FX fallback.
    template<class Zone> struct LegacyAdapter
    {
        Zone* zone;
        bool required(bool) { return true; }
        bool count(size_t, bool) { return true; }
        bool fx_kind(FxCombinedType) { return true; }
        bool asset(int type, const char* name, Origin) { zone->add_asset_of_type(type, name); return true; }
    };
    template<class Sink> bool emit_fx(const FxCombinedDef& value, Origin origin, Sink& sink)
    {
        if (!value.u.data) return true;
        if (!sink.fx_kind(value.type)) return false;
        return value.type == FX_COMBINED_VFX ? sink.asset(ASSET_TYPE_VFX, value.u.vfx->name, origin) :
            sink.asset(ASSET_TYPE_FX, value.u.fx->name, origin);
    }

#include "native_weapon_dependencies.inc"
#include "native_attachment_dependencies.inc"

    inline bool collect_pair(WeaponCompleteDef* weapon, WeaponAttachment* attachment, Collector& collector)
    {
        if (!weapon || !attachment) return collector.reject("missing parsed pair");
        return collector.begin(Owner::weapon, weapon->szInternalName) && visit_weapon(weapon, collector) &&
            collector.begin(Owner::attachment, attachment->name) && visit_attachment(attachment, collector) && collector.freeze();
    }
    // Small public-parse seam; no init, member asset_, real zone or CLI host.
    template<class WeaponParser, class AttachmentParser, class Memory>
    bool parse_and_collect_pair(WeaponParser& weapon, AttachmentParser& attachment, Memory* memory, Collector& collector)
    {
        auto* parsed_weapon = weapon.parse(weapon_name, memory);
        auto* parsed_attachment = attachment.parse(attachment_name, memory);
        return collect_pair(parsed_weapon, parsed_attachment, collector);
    }
}
