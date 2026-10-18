"""Source causals only. Does not compile/run C++, open data or stage a package."""
import hashlib
import re
import unittest
from unittest.mock import patch

import prepare_dependency_visitors as production


class NeutralDependencySourceTests(unittest.TestCase):
    def source(self, name):
        return (production.HERE / name).read_text(encoding='utf-8')

    def corpus(self):
        # Owned Source fixtures exercise the actual patcher, not a test walker.
        return {
            'weapondef.cpp': '''#include "weapondef.hpp"
namespace zonetool::iw7 {
#define WEAPON_SUBASSET_DEPENDING(f,t) original(f,t)
void weapon_def::load_depending_weapondef(WeaponDef* asset, zone_base* zone) {
 WEAPON_SUBASSET_DEPENDING_FXCOMBINED(projExplosionEffect);
 WEAPON_SUBASSET_DEPENDING_FXCOMBINED_ARR(notetrackFXMapValues, 16);
 for (auto i = 0; i < 21; i++)
 {
 WEAPON_SUBASSET_DEPENDING(animOverrides[i].overrides, ASSET_TYPE_ANIM_PACKAGE);
 }
}
void weapon_def::load_depending(zone_base* zone) {
 auto* asset = this->asset_;
 WEAPON_SUBASSET_DEPENDING_ARR(attachments6, ASSET_TYPE_ATTACHMENT, asset->numAttachments6);
 load_depending_weapondef(asset->weapDef, zone);
}
void weapon_def::untouched() { original_write(); }
}
''',
            'weaponattachment.cpp': '''#include "weaponattachment.hpp"
namespace zonetool::iw7 {
void weapon_attachment::init() { original_parse_fallback_without_return(); }
#define ATTACHMENT_SUBASSET_DEPENDING(f,t) original(f,t)
void weapon_attachment::load_depending(zone_base* zone) {
 auto* asset = this->asset_;
 for (auto i = 0; i < asset->numReticles; i++)
 {
 ATTACHMENT_SUBASSET_DEPENDING(reticles[i], ASSET_TYPE_RETICLE);
 }
 ATTACHMENT_ATT_SUBASSET_DEPENDING_FXCOMBINED(projectile, projTrailEffect);
}
void weapon_attachment::untouched() { original_write(); }
}
''', 'weapondef.hpp': '// owned public parse declaration fixture\n',
            'weaponattachment.hpp': '// owned public parse declaration fixture\n'}

    def pins(self, sources):
        return {name: hashlib.sha256(text.encode()).hexdigest() for name, text in sources.items()}

    def test_real_renderer_replaces_only_dependency_regions(self):
        sources = self.corpus()
        with patch.object(production, 'PINS', self.pins(sources)):
            derived = production.derive(sources)
            original_read = production.Path.read_text
            def read(path, **kwargs):
                return derived[path.name] if path.name in derived else original_read(path, **kwargs)
            with patch.object(production.Path, 'read_text', read):
                rendered = production.render(sources)
        self.assertEqual(rendered['weapondef.hpp'], sources['weapondef.hpp'])
        self.assertEqual(rendered['weaponattachment.hpp'], sources['weaponattachment.hpp'])
        for name in ('weapondef.cpp', 'weaponattachment.cpp'):
            self.assertIn('original_write();', rendered[name])
            self.assertNotIn('#define ', rendered[name])
            self.assertIn('LegacyAdapter<zone_base> sink{zone}', rendered[name])
        self.assertIn('original_parse_fallback_without_return();', rendered['weaponattachment.cpp'])
        self.assertIn('"weapDef.animOverrides[].overrides", static_cast<unsigned>(i)', derived['native_weapon_dependencies.inc'])

    def test_all_source_identity_drifts_refuse(self):
        sources = self.corpus()
        with patch.object(production, 'PINS', self.pins(sources)):
            for name in sources:
                with self.subTest(name=name):
                    changed = dict(sources); changed[name] += '// drift\n'
                    with self.assertRaisesRegex(ValueError, 'Source differs'):
                        production.render(changed)
            with self.assertRaisesRegex(ValueError, 'four pinned'):
                production.render({})

    def test_optional_static_pointer_array_skips_null_but_counted_array_requires_storage(self):
        sources = self.corpus()
        with patch.object(production, 'PINS', self.pins(sources)):
            text = production.derive(sources)['native_weapon_dependencies.inc']
        start = text.index('if (asset->notetrackFXMapValues)')
        block = text[start:text.index('for (auto i =', start)]
        self.assertLess(block.index('if (asset->notetrackFXMapValues)'), block.index('sink.count('))
        self.assertNotIn('sink.required', block)
        self.assertIn('sink.required(!(asset->numAttachments6) || asset->attachments6 != nullptr)', text)

    def test_unmapped_traversal_refuses_and_reviewed_walker_drift_refuses(self):
        sources = self.corpus(); sources['weapondef.cpp'] = sources['weapondef.cpp'].replace(
            'WEAPON_SUBASSET_DEPENDING_FXCOMBINED(projExplosionEffect);', 'future_unmapped_effect();')
        with patch.object(production, 'PINS', self.pins(sources)):
            with self.assertRaisesRegex(ValueError, 'Unmapped'):
                production.derive(sources)
        sources = self.corpus()
        with patch.object(production, 'PINS', self.pins(sources)):
            with self.assertRaisesRegex(ValueError, 'Reviewed production walker differs'):
                production.render(sources)

    def test_pure_surface_excludes_builder_body_and_global_state(self):
        common = self.source('native_neutral_dependencies.hpp')
        pure = common[:common.index('// Only the legacy adapter')] + common[common.index('inline bool collect_pair'):]
        pure = re.sub(r'//[^\n]*', '', pure)
        for forbidden in ('zone_base', 'add_asset_of_type', 'load_depending(', 'db_find_', 'dump(',
                          'ignore_assets', 'globals.', 'filesystem::', 'static Collector'):
            self.assertNotIn(forbidden, pure)
        for name in ('native_weapon_dependencies.inc', 'native_attachment_dependencies.inc'):
            text = self.source(name)
            for forbidden in ('zone_base', 'add_asset_of_type', 'db_find_', 'dump(', 'load_depending(', 'globals.'):
                self.assertNotIn(forbidden, text)
        self.assertIn('weapon.parse(weapon_name, memory)', pure)
        self.assertIn('attachment.parse(attachment_name, memory)', pure)

    def test_source_only_opt_in_preserves_historical_module(self):
        historical = self.source('prepare_module.py')
        self.assertNotIn('prepare_dependency_visitors', historical)
        self.assertNotIn('neutral_dependencies', historical)
        preparer = self.source('prepare_dependency_visitors.py')
        for forbidden in ('subprocess', 'write_text(', 'mkdir(', 'argparse', 'buildzone', 'loadzone'):
            self.assertNotIn(forbidden, preparer)

    def test_cpp_fixture_has_nineteen_real_cases_without_duplicate_walker(self):
        fixture = self.source('test_neutral_dependencies.cpp')
        cases = re.findall(r'\{"([a-z_]+)", ([a-z_]+)\}', fixture)
        self.assertEqual(len(cases), 19)
        self.assertEqual(len(set(cases)), 19)
        for name, function in cases:
            self.assertEqual(name, function)
            self.assertIn('void ' + function + '()', fixture)
        self.assertNotRegex(fixture, r'(?<!_)assert\(')
        for forbidden in ('template<class Sink>', 'bool visit_weapon(', 'bool visit_attachment('):
            self.assertNotIn(forbidden, fixture)
        self.assertIn('#include "native_neutral_dependencies.hpp"', fixture)
        self.assertIn('IW7_NATIVE_STRUCTS_HEADER', fixture)

    def test_rumble_causals_call_real_walkers_and_row_verifier(self):
        fixture = self.source('test_neutral_dependencies.cpp')
        def case(name):
            _, opening, end = production.body(fixture, 'void ' + name + '()')
            return fixture[opening:end]
        origins = case('rumble_origins_and_freeze')
        for required in ('pair.fields.fireRumble = &rumble', 'rumbles.fireRumble = &rumble',
                         'rumble.highRumbleGraph = reinterpret_cast<RumbleGraph*>(1)',
                         'rumble.lowRumbleGraph = reinterpret_cast<RumbleGraph*>(1)',
                         'nd::collect_pair(', 'collector.occurrences() == 2',
                         'collector.edges().size() == 2', '"weapDef.fireRumble"',
                         '"rumbles.fireRumble"', 'collector.verify_rows(&row, 1)',
                         '!collector.asset(ASSET_TYPE_RUMBLE'):
            self.assertIn(required, origins)
        rows = case('rumble_rows_exact')
        for required in ('nd::collect_pair(', 'collector.verify_rows(rows, 2)',
                         '!collector.verify_rows(rows, 1)', '!collector.verify_rows(nullptr, 2)',
                         '!collector.verify_rows(extra, 3)', '!collector.verify_rows(reordered, 2)',
                         '{ASSET_TYPE_FX, rumble.name}', '{ASSET_TYPE_RUMBLE, "changed"}',
                         '{ASSET_TYPE_RUMBLE, ",fixture_rumble"}',
                         '{ASSET_TYPE_ATTACHMENT, nd::attachment_name}'):
            self.assertIn(required, rows)
        names = case('rumble_names_refuse')
        for required in ('nd::weapon_name', 'nd::attachment_name', '"default"', '"$default"',
                         '",fixture_rumble"', '!collector.asset(ASSET_TYPE_RUMBLE',
                         'collector.references().empty()'):
            self.assertIn(required, names)
        self.assertIn('static_cast<int>(ASSET_TYPE_MATERIAL)', case('unsupported_type'))

    def test_parity_fixture_has_storage_for_all_counted_model_arrays(self):
        walker = self.source('native_weapon_dependencies.inc')
        fields = set(re.findall(r'sink.required\(!\(asset->numComplexModels\) \|\| asset->(\w+) != nullptr\)', walker))
        self.assertEqual(len(fields), 6)
        fixture = self.source('test_neutral_dependencies.cpp')
        _, opening, end = production.body(fixture, 'void legacy_parity()')
        parity = fixture[opening:end]
        supplied = set(re.findall(r'pair.fields\.(\w+) = (?:models|empty_models);', parity))
        self.assertEqual(fields - supplied, set())
        # Before-control: the real failed layout supplied only one of six arrays.
        original_partial = 'pair.fields.complexWorldModel = models; pair.fields.numComplexModels = 2;'
        partial_fields = set(re.findall(r'pair.fields\.(\w+) = (?:models|empty_models);', original_partial))
        self.assertEqual(len(fields - partial_fields), 5)
        self.assertIn('legacy sparse NULL-array sequence differs', parity)


if __name__ == '__main__':
    unittest.main()
