// AUTHORED, NOT COMPILED OR RUN in the Source milestone. Future distinct CPP GO.
// Exact production walkers/collector + pinned native declarations, owned memory.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>
#define assert_sizeof(T, N) static_assert(sizeof(T) == N)
#define assert_offsetof(T, M, N) static_assert(offsetof(T, M) == N)
#ifndef IW7_NATIVE_STRUCTS_HEADER
#error Exact pinned native structs header required from a separately admitted CPP cohort
#endif
#include IW7_NATIVE_STRUCTS_HEADER
#include "native_neutral_dependencies.hpp"

namespace
{
    using namespace zonetool::iw7;
    namespace nd = neutral_dependencies;
    void check(bool value) { if (!value) throw std::runtime_error("fixture check failed"); }
    struct Range { const void* data; size_t size; };
    struct Memory
    {
        std::vector<Range> ranges;
        void allow(const char* name) { ranges.push_back({name, std::strlen(name) + 1}); }
        static bool copy(void* out, const void* input, size_t size, void* context)
        {
            auto& memory = *static_cast<Memory*>(context);
            const auto address = reinterpret_cast<std::uintptr_t>(input);
            for (const auto& range : memory.ranges)
            {
                const auto start = reinterpret_cast<std::uintptr_t>(range.data);
                if (address >= start && address - start <= range.size && size <= range.size - (address - start))
                { std::memcpy(out, input, size); return true; }
            }
            return false;
        }
    };
    struct Pair
    {
        WeaponCompleteDef weapon{}; WeaponDef fields{}; WeaponAttachment attachment{};
        FxEffectDef fx{}; ParticleSystemDef vfx{}; Memory memory;
        Pair()
        {
            weapon.name = nd::weapon_name; weapon.weapDef = &fields; attachment.name = nd::attachment_name;
            fx.name = "fixture_fx"; vfx.name = "fixture_vfx";
            for (const auto* name : {weapon.name, attachment.name, fx.name, vfx.name}) memory.allow(name);
        }
        void scalar_fx() { fields.projExplosionEffect.type = FX_COMBINED_FX; fields.projExplosionEffect.u.fx = &fx; }
    };
    struct SpyZone
    {
        std::vector<std::pair<int, std::string>> calls;
        void add_asset_of_type(int type, const char* name) { calls.emplace_back(type, name); }
    };
    struct RecordingSink
    {
        std::vector<std::pair<int, std::string>> calls;
        bool required(bool value) { return value; }
        bool count(size_t value, bool dynamic) { return !dynamic || value <= 64; }
        bool fx_kind(FxCombinedType type) { return type == FX_COMBINED_FX || type == FX_COMBINED_VFX; }
        bool asset(int type, const char* name, nd::Origin) { calls.emplace_back(type, name); return true; }
    };
    void before_real_zone()
    {
        Pair pair; pair.scalar_fx(); nd::Collector collector(Memory::copy, &pair.memory);
        check(nd::collect_pair(&pair.weapon, &pair.attachment, collector));
        check(collector.frozen() && collector.external_count() == 1);
        // The production collecting API accepts no zone/factory/effects callback.
        // Its Source check additionally bans these calls from all pure code.
    }
    void public_parse_not_init()
    {
        Pair pair;
        struct WP { WeaponCompleteDef* result; unsigned calls = 0;
            WeaponCompleteDef* parse(const std::string& name, Memory*) { check(name == nd::weapon_name); ++calls; return result; }
            void init(const std::string&, Memory*) { throw std::runtime_error("init forbidden"); } } wp{&pair.weapon};
        struct AP { WeaponAttachment* result; unsigned calls = 0;
            WeaponAttachment* parse(const std::string& name, Memory*) { check(name == nd::attachment_name); ++calls; return result; }
            void init(const std::string&, Memory*) { throw std::runtime_error("init forbidden"); } } ap{&pair.attachment};
        nd::Collector collector(Memory::copy, &pair.memory);
        check(nd::parse_and_collect_pair(wp, ap, &pair.memory, collector) && wp.calls == 1 && ap.calls == 1);
        wp.result = nullptr; nd::Collector missing(Memory::copy, &pair.memory);
        check(!nd::parse_and_collect_pair(wp, ap, &pair.memory, missing) && !missing.frozen());
    }
    void owner_origin_required()
    {
        Pair pair; pair.scalar_fx();
        std::remove_pointer_t<decltype(pair.attachment.projectile)> projectile{};
        pair.attachment.projectile = &projectile; projectile.projTrailEffect = pair.fields.projExplosionEffect;
        nd::Collector collector(Memory::copy, &pair.memory);
        check(nd::collect_pair(&pair.weapon, &pair.attachment, collector));
        check(collector.references().size() == 1 && collector.edges().size() == 2);
        check(collector.edges()[0].owner == nd::Owner::weapon && collector.edges()[0].path == "weapDef.projExplosionEffect");
        check(collector.edges()[1].owner == nd::Owner::attachment && collector.edges()[1].path == "projectile.projTrailEffect");
        check(std::string(nd::owner_name(collector.edges()[1].owner)) == nd::attachment_name);
    }
    void dedup_keeps_origins()
    {
        Pair pair; nd::Collector collector(Memory::copy, &pair.memory);
        check(collector.begin(nd::Owner::weapon, pair.weapon.name));
        for (unsigned i = 0; i < 3; ++i) check(collector.asset(ASSET_TYPE_FX, pair.fx.name, {"field[]", i % 2}));
        check(collector.occurrences() == 3 && collector.references().size() == 1 && collector.edges().size() == 2);
        check(collector.edges()[1].path == "field[1]");
    }
    void private_roots_never_ignored()
    {
        Pair pair; WeaponAttachment* attachments[]{&pair.attachment};
        pair.weapon.attachments6 = attachments; pair.weapon.numAttachments6 = 1;
        nd::Collector collector(Memory::copy, &pair.memory);
        check(nd::collect_pair(&pair.weapon, &pair.attachment, collector));
        check(collector.references().size() == 1 && collector.references()[0].owned && collector.external_count() == 0);
        check(collector.edges()[0].path == "attachments6[0]" && collector.verify_rows(nullptr, 0));
        nd::Row owned{ASSET_TYPE_ATTACHMENT, nd::attachment_name}; check(!collector.verify_rows(&owned, 1));
    }
    void no_external_body_recursion()
    {
        Pair pair; pair.scalar_fx();
        pair.fx.elemDefCountLooping = 1; pair.fx.elemDefs = reinterpret_cast<FxElemDef*>(1);
        pair.vfx.numEmitters = 1; pair.vfx.emitterDefs = reinterpret_cast<ParticleEmitterDef*>(1);
        pair.fields.projDudEffect.type = FX_COMBINED_VFX; pair.fields.projDudEffect.u.vfx = &pair.vfx;
        nd::Collector collector(Memory::copy, &pair.memory);
        check(nd::collect_pair(&pair.weapon, &pair.attachment, collector) && collector.external_count() == 2);
    }
    void fx_scalar()
    {
        Pair pair; pair.scalar_fx(); nd::Collector first(Memory::copy, &pair.memory);
        check(nd::collect_pair(&pair.weapon, &pair.attachment, first) && first.references()[0].type == ASSET_TYPE_FX);
        pair.fields.projExplosionEffect.type = FX_COMBINED_VFX; pair.fields.projExplosionEffect.u.vfx = &pair.vfx;
        nd::Collector second(Memory::copy, &pair.memory);
        check(nd::collect_pair(&pair.weapon, &pair.attachment, second) && second.references()[0].type == ASSET_TYPE_VFX);
        check(first.edges()[0].path == second.edges()[0].path);
    }
    void fx_arrays()
    {
        Pair pair; FxCombinedDef values[16]{}; pair.fields.notetrackFXMapValues = values;
        values[3].type = FX_COMBINED_FX; values[3].u.fx = &pair.fx;
        values[9].type = FX_COMBINED_VFX; values[9].u.vfx = &pair.vfx;
        nd::Collector collector(Memory::copy, &pair.memory);
        check(nd::collect_pair(&pair.weapon, &pair.attachment, collector) && collector.occurrences() == 2);
        check(collector.edges()[0].path == "weapDef.notetrackFXMapValues[3]" && collector.edges()[1].path == "weapDef.notetrackFXMapValues[9]");
    }
    void attachment_fx()
    {
        Pair pair; std::remove_pointer_t<decltype(pair.attachment.projectile)> projectile{};
        std::remove_pointer_t<decltype(pair.attachment.charged)> charged{};
        pair.attachment.projectile = &projectile; pair.attachment.charged = &charged;
        projectile.projExplosionEffect.type = FX_COMBINED_FX; projectile.projExplosionEffect.u.fx = &pair.fx;
        charged.chargeMeterEffect.type = FX_COMBINED_VFX; charged.chargeMeterEffect.u.vfx = &pair.vfx;
        nd::Collector collector(Memory::copy, &pair.memory);
        check(nd::collect_pair(&pair.weapon, &pair.attachment, collector) && collector.external_count() == 2);
        check(collector.edges()[0].path == "projectile.projExplosionEffect" && collector.edges()[1].path == "charged.chargeMeterEffect");
    }
    void fx_invalid_kind()
    {
        Pair pair; pair.scalar_fx(); pair.fields.projExplosionEffect.type = static_cast<FxCombinedType>(7);
        nd::Collector collector(Memory::copy, &pair.memory);
        check(!nd::collect_pair(&pair.weapon, &pair.attachment, collector) && !collector.frozen() && collector.references().empty());
        SpyZone zone; nd::LegacyAdapter<SpyZone> legacy{&zone};
        check(nd::visit_weapon(&pair.weapon, legacy) && zone.calls.size() == 1 && zone.calls[0].first == ASSET_TYPE_FX);
    }
    void name_bound()
    {
        Pair pair; std::string accepted(511, 'a'); pair.memory.allow(accepted.c_str());
        nd::Collector collector(Memory::copy, &pair.memory); check(collector.begin(nd::Owner::weapon, pair.weapon.name));
        check(collector.asset(ASSET_TYPE_FX, accepted.c_str(), {"field"}));
        for (const auto& name : {std::string(512, 'a'), std::string("bad\nname"), std::string("\xc0\x80"), std::string("default"), std::string(",ref"), std::string()})
        {
            pair.memory.allow(name.c_str()); nd::Collector invalid(Memory::copy, &pair.memory);
            check(invalid.begin(nd::Owner::weapon, pair.weapon.name));
            check(!invalid.asset(ASSET_TYPE_FX, name.c_str(), {"field"}) && invalid.references().empty());
        }
        char unterminated[512]; std::memset(unterminated, 'a', sizeof unterminated);
        pair.memory.ranges.push_back({unterminated, sizeof unterminated}); nd::Collector missing(Memory::copy, &pair.memory);
        check(missing.begin(nd::Owner::weapon, pair.weapon.name) && !missing.asset(ASSET_TYPE_FX, unterminated, {"field"}));
        nd::Collector unreadable(Memory::copy, &pair.memory); check(unreadable.begin(nd::Owner::weapon, pair.weapon.name));
        check(!unreadable.asset(ASSET_TYPE_FX, reinterpret_cast<const char*>(1), {"field"}));
    }
    void origin_bound()
    {
        Pair pair;
        std::string deep = "a"; for (unsigned i = 0; i < 32; ++i) deep += ".a";
        for (const auto& path : {std::string(), std::string(257, 'a'), deep})
        {
            nd::Collector collector(Memory::copy, &pair.memory); check(collector.begin(nd::Owner::weapon, pair.weapon.name));
            check(!collector.asset(ASSET_TYPE_FX, pair.fx.name, {path.c_str()}) && collector.references().empty());
        }
        nd::Collector no_owner(Memory::copy, &pair.memory); check(!no_owner.asset(ASSET_TYPE_FX, pair.fx.name, {"field"}));
        nd::Collector boundary(Memory::copy, &pair.memory); check(boundary.begin(nd::Owner::weapon, pair.weapon.name));
        std::string accepted(256, 'a'); check(boundary.asset(ASSET_TYPE_FX, pair.fx.name, {accepted.c_str()}));
    }
    void count_and_byte_boundaries()
    {
        nd::Budget budget;
        budget.occurrences = 8191; check(budget.permits(false, false, 0, 0));
        budget.occurrences = 8192; check(!budget.permits(false, false, 0, 0)); budget = {};
        budget.external = 4095; check(budget.permits(true, false, 0, 0));
        budget.external = 4096; check(!budget.permits(true, false, 0, 0)); budget = {};
        budget.edges = 8191; check(budget.permits(false, true, 0, 0));
        budget.edges = 8192; check(!budget.permits(false, true, 0, 0)); budget = {};
        budget.text = 1048575; check(budget.permits(false, false, 1, 0)); check(!budget.permits(false, false, 2, 0)); budget = {};
        budget.manifest = 1048575; check(budget.permits(false, false, 0, 1)); check(!budget.permits(false, false, 0, 2));
        Pair pair; nd::Collector collector(Memory::copy, &pair.memory); check(collector.count(64, true));
        check(collector.count(8192 - 64, false)); check(!collector.count(1, false));
        nd::Collector dynamic(Memory::copy, &pair.memory); check(!dynamic.count(65, true));
        nd::Collector repeated(Memory::copy, &pair.memory); check(repeated.begin(nd::Owner::weapon, pair.weapon.name));
        for (unsigned i = 0; i < 8192; ++i) check(repeated.asset(ASSET_TYPE_FX, pair.fx.name, {"field"}));
        check(!repeated.asset(ASSET_TYPE_FX, pair.fx.name, {"field"}) && repeated.references().size() == 1);
    }
    void unsupported_type()
    {
        Pair pair;
        for (const int type : {static_cast<int>(ASSET_TYPE_IMAGE), static_cast<int>(ASSET_TYPE_ATTACHMENT),
            static_cast<int>(ASSET_TYPE_XMODEL), -1})
        {
            nd::Collector collector(Memory::copy, &pair.memory); check(collector.begin(nd::Owner::weapon, pair.weapon.name));
            check(!collector.asset(type, pair.fx.name, {"field"}) && collector.references().empty());
        }
        ReticleDef reticle{}; reticle.name = "fixture_reticle"; pair.memory.allow(reticle.name);
        ReticleDef* reticles[]{&reticle}; pair.attachment.reticles = reticles; pair.attachment.numReticles = 1;
        nd::Collector supported(Memory::copy, &pair.memory);
        check(nd::collect_pair(&pair.weapon, &pair.attachment, supported) && supported.references()[0].type == ASSET_TYPE_RETICLE);
    }
    void reference_preflight_freeze()
    {
        Pair pair; pair.scalar_fx(); nd::Collector collector(Memory::copy, &pair.memory);
        nd::Row row{ASSET_TYPE_FX, pair.fx.name}; check(!collector.verify_rows(&row, 1));
        check(nd::collect_pair(&pair.weapon, &pair.attachment, collector) && collector.verify_rows(&row, 1));
        check(!collector.verify_rows(nullptr, 0)); row.name = "changed"; check(!collector.verify_rows(&row, 1));
        row = {ASSET_TYPE_ATTACHMENT, nd::attachment_name}; check(!collector.verify_rows(&row, 1));
        check(!collector.asset(ASSET_TYPE_FX, pair.fx.name, {"field"}) && !collector.frozen());
    }
    void legacy_parity()
    {
        Pair pair; pair.scalar_fx(); FxCombinedDef values[16]{}; pair.fields.notetrackFXMapValues = values;
        values[2].type = FX_COMBINED_VFX; values[2].u.vfx = &pair.vfx;
        WeaponAttachment* attachments[]{&pair.attachment}; pair.weapon.attachments6 = attachments; pair.weapon.numAttachments6 = 1;
        Material material{}; material.name = "fixture_material"; pair.weapon.killIcon = &material;
        pair.fields.camoWorldModelMaterialOverride[3] = &material;
        XModel model{}; model.name = "fixture_model"; XModel* models[]{nullptr, &model};
        pair.fields.complexWorldModel = models; pair.fields.numComplexModels = 2;
        SpyZone zone; nd::LegacyAdapter<SpyZone> legacy{&zone}; RecordingSink recording;
        check(nd::visit_weapon(&pair.weapon, legacy) && nd::visit_weapon(&pair.weapon, recording));
        const std::vector<std::pair<int, std::string>> expected{
            {ASSET_TYPE_ATTACHMENT, pair.attachment.name}, {ASSET_TYPE_MATERIAL, material.name},
            {ASSET_TYPE_XMODEL, model.name}, {ASSET_TYPE_MATERIAL, material.name},
            {ASSET_TYPE_VFX, pair.vfx.name}, {ASSET_TYPE_FX, pair.fx.name}};
        check(zone.calls == expected && recording.calls == expected);
        std::remove_pointer_t<decltype(pair.attachment.projectile)> projectile{};
        pair.attachment.projectile = &projectile; projectile.projectileModel = &model;
        projectile.projTrailEffect = pair.fields.projExplosionEffect;
        SpyZone attachment_zone; nd::LegacyAdapter<SpyZone> attachment_legacy{&attachment_zone};
        check(nd::visit_attachment(&pair.attachment, attachment_legacy));
        const std::vector<std::pair<int, std::string>> expected_attachment{
            {ASSET_TYPE_XMODEL, model.name}, {ASSET_TYPE_FX, pair.fx.name}};
        check(attachment_zone.calls == expected_attachment);
    }
}
int main()
{
    struct Case { const char* name; void (*run)(); };
    const Case cases[]{
        {"before_real_zone", before_real_zone}, {"public_parse_not_init", public_parse_not_init},
        {"owner_origin_required", owner_origin_required}, {"dedup_keeps_origins", dedup_keeps_origins},
        {"private_roots_never_ignored", private_roots_never_ignored}, {"no_external_body_recursion", no_external_body_recursion},
        {"fx_scalar", fx_scalar}, {"fx_arrays", fx_arrays}, {"attachment_fx", attachment_fx},
        {"fx_invalid_kind", fx_invalid_kind}, {"name_bound", name_bound}, {"origin_bound", origin_bound},
        {"count_and_byte_boundaries", count_and_byte_boundaries}, {"unsupported_type", unsupported_type},
        {"reference_preflight_freeze", reference_preflight_freeze}, {"legacy_parity", legacy_parity}};
    static_assert(sizeof cases / sizeof cases[0] == 16);
    unsigned passed = 0;
    for (const auto& test : cases)
    {
        try { test.run(); ++passed; std::printf("PASS %s\n", test.name); }
        catch (const std::exception& error) { std::printf("FAIL %s: %s\n", test.name, error.what()); return 1; }
    }
    std::printf("%u/16 PASS\n", passed); return passed == 16 ? 0 : 1;
}
