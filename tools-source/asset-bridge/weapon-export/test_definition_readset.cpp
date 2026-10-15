// Authored native causal fixture; not executed by the Source-only tests.
// Uses the pinned declarations and the PRODUCTION gate/readset, with owned
// memory only. A future separately admitted CPP cohort compiles/runs this.
#define NOMINMAX
#include <Windows.h>
#include <array>
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <type_traits>
#include <vector>
#define assert_sizeof(T, N) static_assert(sizeof(T) == N)
#define assert_offsetof(T, M, N) static_assert(offsetof(T, M) == N)
#ifndef IW7_NATIVE_STRUCTS_HEADER
#error Exact pinned native structs header must be supplied by the cohort
#endif
#include IW7_NATIVE_STRUCTS_HEADER
namespace zonetool::iw7
{
#include "native_definition_access.hpp"
#include "native_definition_readset.hpp"
#include "native_definition_fields.inc"
#include "native_definition_gate.hpp"
}

namespace
{
    using namespace zonetool::iw7;
    using player_definition_readset::Reader;
    struct Range { std::uintptr_t start; size_t size; };
    struct Context
    {
        std::vector<Range> allowed, denied;
        const char* text = nullptr;
        scr_string_t seen = 0;
        unsigned calls = 0;
        const void* fail_copy_at = nullptr;
        bool copy_fault = false, conversion_fault = false;
    };
    bool contains(const Range& range, const void* address, size_t size)
    {
        const auto start = reinterpret_cast<std::uintptr_t>(address);
        return start >= range.start && start - range.start <= range.size &&
            size <= range.size - (start - range.start);
    }
    bool readable(const void* address, size_t size, void* raw)
    {
        auto& context = *static_cast<Context*>(raw);
        const auto start = reinterpret_cast<std::uintptr_t>(address);
        if (size > (std::numeric_limits<std::uintptr_t>::max)() - start) return false;
        for (const auto& denied : context.denied)
            if (start < denied.start + denied.size && denied.start < start + size) return false;
        for (const auto& range : context.allowed) if (contains(range, address, size)) return true;
        return false;
    }
    bool copy(void* output, const void* input, size_t size, void* raw)
    {
        if (static_cast<Context*>(raw)->copy_fault || static_cast<Context*>(raw)->fail_copy_at == input || !readable(input, size, raw)) return false;
        std::memcpy(output, input, size);
        return true;
    }
    const char* script(scr_string_t id, void* raw, bool* converted)
    {
        auto& context = *static_cast<Context*>(raw);
        context.seen = id; ++context.calls;
        *converted = !context.conversion_fault;
        return context.text;
    }
    struct Fixture
    {
        WeaponCompleteDef weapon{};
        WeaponDef definition{};
        WeaponAttachment pap{}, other{};
        WeaponAttachment* associations[2]{};
        char weapon_name[sizeof("iw7_shredder_zm")] = "iw7_shredder_zm";
        char pap_name[sizeof("shredderpap1")] = "shredderpap1";
        char other_name[6] = "other";
        char text[Reader::string_limit] = "owned";
        vec2_t original_curve[2]{}, current_curve[2]{};
        NoteTrackToSoundEntry mapping{};
        NoteTrackToSuitSoundEntry suit{};
        scr_string_t script_ids[64]{};
        AttDamage damage{};
        XModel model{};
        Material material{};
        XModel* model_references[1]{};
        Fixture()
        {
            weapon.name = weapon_name; weapon.weapDef = &definition;
            definition.weapType = static_cast<weapType_t>(1);
            pap.name = pap_name; pap.papAttachment = true;
            pap.weaponType = static_cast<weapType_t>(0);
            other.name = other_name;
            associations[0] = &pap; associations[1] = &other;
            weapon.numAttachments6 = 2; weapon.attachments6 = associations;
            model_references[0] = &model;
        }
        Context context()
        {
            Context result;
            result.allowed.push_back({reinterpret_cast<std::uintptr_t>(this), sizeof(*this)});
            result.text = text;
            return result;
        }
    };
    __declspec(noinline) char* converter_ok(unsigned int) { static char value[] = "owned"; return value; }
    __declspec(noinline) char* converter_null(unsigned int) { return nullptr; }
    __declspec(noinline) char* converter_av(unsigned int)
    {
        *reinterpret_cast<volatile char*>(std::uintptr_t{1}) = 0;
        return nullptr;
    }
}

int main()
{
    unsigned checks = 0;
    const auto check = [&](bool pass) { ++checks; if (!pass) throw std::runtime_error("Definition readset causal failed"); };
    try
    {
        const auto expect = [&](auto mutate, bool expected, unsigned expected_calls = 0)
        {
            Fixture source;
            Context context = source.context();
            Reader reader{readable, copy, script, &context};
            mutate(source, context, reader);
            std::array<unsigned char, sizeof(source.weapon)> weapon_before{};
            std::array<unsigned char, sizeof(source.definition)> definition_before{};
            std::array<unsigned char, sizeof(source.pap)> pap_before{};
            std::memcpy(weapon_before.data(), &source.weapon, weapon_before.size());
            std::memcpy(definition_before.data(), &source.definition, definition_before.size());
            std::memcpy(pap_before.data(), &source.pap, pap_before.size());
            unsigned serialized = 0;
            const bool result = player_definition_readset::with_pair(reader, &source.weapon, &source.pap,
                [&](const auto*, const auto*) { serialized += 2; });
            check(result == expected && serialized == (expected ? 2u : 0u) &&
                context.calls == expected_calls && (!expected_calls || context.seen == source.pap.attachPoint) &&
                (expected ? reader.refusal == nullptr : reader.refusal != nullptr) &&
                std::memcmp(&source.weapon, weapon_before.data(), weapon_before.size()) == 0 &&
                std::memcmp(&source.definition, definition_before.data(), definition_before.size()) == 0 &&
                std::memcmp(&source.pap, pap_before.data(), pap_before.size()) == 0);
        };
        expect([](auto&, auto&, auto&) {}, true);
        expect([](auto& f, auto&, auto&) { f.definition.weapType = static_cast<weapType_t>(3); }, false);
        expect([](auto& f, auto&, auto&) { f.pap.weaponType = static_cast<weapType_t>(3); }, false);
        for (const auto raw : {2u, 255u})
            expect([&](auto& f, auto&, auto&) { *reinterpret_cast<unsigned char*>(&f.pap.papAttachment) = static_cast<unsigned char>(raw); }, false);
        expect([](auto& f, auto&, auto&) { f.weapon.numAttachments6 = 0; }, false);
        expect([](auto& f, auto&, auto&) { f.associations[1] = &f.pap; }, false);
        expect([](auto& f, auto&, auto&) { f.weapon.numAttachments = 65; }, false);
        expect([](auto& f, auto&, auto&) { f.weapon.attachments6 = nullptr; }, false);
        expect([](auto& f, auto& c, auto&) { c.denied.push_back({reinterpret_cast<std::uintptr_t>(&f.weapon), sizeof(f.weapon)}); }, false);
        expect([](auto& f, auto& c, auto&) { c.denied.push_back({reinterpret_cast<std::uintptr_t>(&f.associations[1]), sizeof(f.associations[1])}); }, false);
        expect([](auto& f, auto&, auto&) { f.weapon.weapDef = reinterpret_cast<WeaponDef*>(std::uintptr_t{1}); }, false);
        expect([](auto& f, auto&, auto&) { std::fill(std::begin(f.text), std::end(f.text), 'a'); f.weapon.szDisplayName = f.text; }, false);
        expect([](auto& f, auto&, auto&) { f.text[0] = '\xC0'; f.weapon.szDisplayName = f.text; }, false);
        expect([](auto& f, auto&, auto&) { *reinterpret_cast<unsigned char*>(&f.weapon.motionTracker) = 2; }, false);
        expect([](auto& f, auto&, auto&) { f.definition.turretFov = std::numeric_limits<float>::quiet_NaN(); }, false);
        expect([](auto& f, auto&, auto&) { f.pap.damageScale = std::numeric_limits<float>::infinity(); }, false);
        expect([](auto& f, auto&, auto&) { f.pap.numReticles = -1; }, false);
        expect([](auto& f, auto&, auto&) { f.pap.numReticles = 65; }, false);
        expect([](auto& f, auto&, auto&) { f.pap.worldModelCamo = reinterpret_cast<XModel*>(std::uintptr_t{1}); }, false);
        expect([](auto& f, auto&, auto&) { f.pap.worldModelCamo = &f.model; }, false); // Null dependency name.
        expect([](auto& f, auto&, auto&) { f.model.name = f.text; f.pap.worldModelCamo = &f.model; }, true);
        expect([](auto&, auto& c, auto&) { c.copy_fault = true; }, false);
        expect([](auto&, auto&, auto& r) { r.copy = nullptr; }, false);
        expect([](auto& f, auto& c, auto&) { c.fail_copy_at = &f.weapon.iClipSize; }, false);
        for (unsigned which = 0; which < 2; ++which)
        {
            expect([&](auto& f, auto&, auto&) {
                auto& values = which ? f.definition.camoViewModelMaterialOverride : f.definition.camoWorldModelMaterialOverride;
                f.material.name = f.text; values[0] = values[15] = &f.material;
            }, true);
            expect([&](auto& f, auto&, auto&) {
                auto& values = which ? f.definition.camoViewModelMaterialOverride : f.definition.camoWorldModelMaterialOverride;
                values[15] = reinterpret_cast<Material*>(std::uintptr_t{1});
            }, false);
            expect([&](auto& f, auto& c, auto&) {
                auto& values = which ? f.definition.camoViewModelMaterialOverride : f.definition.camoWorldModelMaterialOverride;
                c.denied.push_back({reinterpret_cast<std::uintptr_t>(&values[15]), sizeof(values[15])});
            }, false);
            expect([&](auto& f, auto&, auto&) {
                auto& values = which ? f.definition.camoViewModelMaterialOverride : f.definition.camoWorldModelMaterialOverride;
                values[15] = &f.material; // Native material header has a null name.
            }, false);
        }
        expect([](auto& f, auto&, auto&) {
            f.model.name = f.text; f.definition.numComplexModels = 1; f.definition.complexWorldModel = f.model_references;
        }, true);
        expect([](auto& f, auto&, auto&) {
            f.definition.numComplexModels = 1; f.definition.complexWorldModel = reinterpret_cast<XModel**>(std::uintptr_t{1});
        }, false);
        expect([](auto& f, auto&, auto&) {
            f.model.name = f.text; f.pap.numModelVariations = 1; f.pap.worldModelVariations = f.model_references;
        }, true);
        expect([](auto& f, auto&, auto&) {
            f.pap.numModelVariations = 1; f.pap.worldModelVariations = reinterpret_cast<XModel**>(std::uintptr_t{1});
        }, false);
        for (const auto index : {0u, 1u, 2u})
            expect([&](auto& f, auto& c, auto&) {
                const void* address = index == 0 ? static_cast<void*>(&f.definition.animOverrides[20]) :
                    index == 1 ? static_cast<void*>(&f.definition.sfxOverrides[20]) : static_cast<void*>(&f.definition.vfxOverrides[20]);
                c.denied.push_back({reinterpret_cast<std::uintptr_t>(address), 1});
            }, false);
        expect([](auto& f, auto&, auto&) { f.weapon.accuracyGraphKnotCount[0] = 1; }, false);
        expect([](auto& f, auto&, auto&) {
            f.weapon.accuracyGraphKnotCount[0] = 1; f.definition.originalAccuracyGraphKnotCount[0] = 1;
            f.definition.originalAccuracyGraphKnots[0] = f.original_curve; f.weapon.accuracyGraphKnots[0] = f.current_curve;
        }, true);
        expect([](auto& f, auto&, auto&) {
            f.weapon.accuracyGraphKnotCount[0] = 1; f.definition.originalAccuracyGraphKnotCount[0] = 1;
            f.definition.originalAccuracyGraphKnots[0] = f.original_curve; f.original_curve[0][1] = std::numeric_limits<float>::infinity();
        }, false);
        expect([](auto& f, auto&, auto&) { f.weapon.numNotetrackOverrides = 1; f.weapon.notetrackOverrides = &f.mapping; f.mapping.numSoundMappings = 65; }, false);
        expect([](auto& f, auto&, auto&) { f.weapon.numNotetrackSuitEntries = 1; f.weapon.notetrackSuitEntries = &f.suit; f.suit.numSoundMappings = 65; }, false);
        expect([](auto& f, auto&, auto&) { f.pap.damage = &f.damage; f.damage.maxDamageRange = std::numeric_limits<float>::quiet_NaN(); }, false);
        // All sixteen null masks for each native STRING_ARR. Only the two
        // homogeneous masks are admissible; empty nonnull strings stay matrices.
        for (unsigned which = 0; which < 2; ++which)
            for (unsigned mask = 0; mask < 16; ++mask)
                expect([&](auto& f, auto&, auto&) {
                    auto& field = which ? f.definition.turretBarrelSpinDownSnd : f.definition.turretBarrelSpinUpSnd;
                    for (unsigned i = 0; i < 4; ++i) field[i] = mask & (1u << i) ? f.text : nullptr;
                }, mask == 0 || mask == 15);
        expect([](auto& f, auto&, auto&) {
            f.text[0] = 0; for (auto& value : f.definition.turretBarrelSpinUpSnd) value = f.text;
        }, true);
        expect([](auto& f, auto& c, auto&) {
            f.pap.attachPoint = 70001; c.text = nullptr;
        }, false, 1);
        expect([](auto& f, auto& c, auto&) { f.pap.attachPoint = 70001; c.conversion_fault = true; }, false, 1);
        expect([](auto& f, auto&, auto&) { f.pap.attachPoint = 70001; std::fill(std::begin(f.text), std::end(f.text), 'a'); }, false, 1);
        expect([](auto& f, auto& c, auto&) { f.pap.attachPoint = 70001; c.text = reinterpret_cast<const char*>(std::uintptr_t{1}); }, false, 1);
        expect([](auto& f, auto&, auto&) { f.pap.attachPoint = -1; }, false);
        expect([](auto& f, auto&, auto&) { f.pap.attachPoint = 70001; }, true, 1);
        expect([](auto&, auto&, auto& r) { r.bytes = Reader::byte_limit; }, false);
        expect([](auto&, auto&, auto& r) { r.elements = Reader::element_limit; }, false);
        expect([](auto&, auto&, auto& r) { r.json_bytes = Reader::json_limit; }, false);
        expect([](auto&, auto&, auto& r) { r.allocation_bytes = Reader::allocation_limit; }, false);
        expect([](auto& f, auto&, auto& r) { f.pap.attachPoint = 1; r.script_calls = Reader::script_call_limit; }, false);
        {
            Fixture f; auto context = f.context(); Reader r{readable, copy, script, &context};
            check(r.script(0, "zero") && context.calls == 0 && r.script_calls == 0);
            check(r.script(70001, "wide_id") && context.calls == 1 && context.seen == 70001);
            check(!r.span(reinterpret_cast<const void*>((std::numeric_limits<std::uintptr_t>::max)() - 1), 8, "overflow"));
        }
        {
            Fixture f; auto context = f.context(); Reader r{readable, copy, script, &context};
            for (auto& value : f.definition.turretBarrelSpinUpSnd) value = f.text;
            check(r.native_string_array(&f.definition.turretBarrelSpinUpSnd, 4, "matrix") && r.matrix_count == 1 && r.elements == 16 &&
                r.copied_text_bytes == 24 && r.bytes >= 4 * 24);
        }
        {
            char input[] = "owned", output[sizeof(input)]{};
            check(player_definition_access::copy(output, input, sizeof(input)) && std::memcmp(input, output, sizeof(input)) == 0);
            check(!player_definition_access::copy(output, reinterpret_cast<const void*>(std::uintptr_t{1}), 1));
            const char* text = nullptr;
            check(player_definition_access::script(converter_ok, 70001, &text) && text != nullptr);
            check(!player_definition_access::script(converter_null, 70001, &text) && text == nullptr);
            check(!player_definition_access::script(converter_av, 70001, &text) && text == nullptr);
            check(player_definition_access::av_filter(EXCEPTION_ACCESS_VIOLATION) == EXCEPTION_EXECUTE_HANDLER &&
                player_definition_access::av_filter(EXCEPTION_ILLEGAL_INSTRUCTION) == EXCEPTION_CONTINUE_SEARCH &&
                player_definition_access::av_filter(0xE06D7363u) == EXCEPTION_CONTINUE_SEARCH);
        }
        constexpr unsigned expected_checks = 100;
        if (checks != expected_checks) throw std::runtime_error("Exact authored definition check count differs");
        std::printf("IW7_PLAYER_DEFINITION_READSET_CHECKS=100\n");
        return 0;
    }
    catch (const std::exception& error) { std::fprintf(stderr, "%s\n", error.what()); return 1; }
}
