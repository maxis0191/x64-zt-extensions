"""Source renderer/contracts only. Authored native fixture is NOT executed here."""
import hashlib
import os
import re
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import prepare_build as build
import prepare_image_metadata as metadata
import prepare_image_provenance as provenance
import prepare_image_registration_metadata as registration
from test_image_metadata import MetadataSourceTests
from test_image_provenance import ProvenanceTransitionTests


class RegistrationSourceTests(unittest.TestCase):
    def test_prepare_refuses_incomplete_selection_before_any_io(self):
        with patch.object(build, 'path_checked', side_effect=AssertionError('Preparation IO reached')) as read:
            with self.assertRaises(ValueError):
                build.prepare(SimpleNamespace(image_registration_metadata_v1=True))
            read.assert_not_called()

    def test_registration_payload_cap_does_not_expand_old_profile(self):
        options = dict(provenance_profile=True, metadata_profile=True)
        payload = {'source': b'x'*(320*1024+1)}
        with self.assertRaises(ValueError):
            build.require_preparation_bounds(b'{}', payload, **options)
        build.require_preparation_bounds(b'{}', payload, registration_profile=True, **options)
        for invalid in ({'registration_profile': True}, {'registration_profile': 1, **options}):
            with self.assertRaises(ValueError):
                build.require_preparation_bounds(b'{}', payload, **invalid)
        with self.assertRaises(ValueError):
            build.require_preparation_bounds(b'{}', {'source': b'x'*(384*1024+1)},
                                             registration_profile=True, **options)

    def test_selection_is_explicit_and_does_not_admit_the_legacy_pair_alone(self):
        self.assertFalse(registration.selected(SimpleNamespace()))
        self.assertTrue(registration.selected(SimpleNamespace(image_registration_metadata_v1=True,
                                                             image_metadata_v1=True, image_provenance_v1=True)))
        for values in ({'image_registration_metadata_v1': 1}, {'image_registration_metadata_v1': 'true'},
                       {'image_registration_metadata_v1': True},
                       {'image_registration_metadata_v1': True, 'image_metadata_v1': True}):
            with self.assertRaises(ValueError):
                registration.selected(SimpleNamespace(**values))

    def test_same_copy_source_has_fixed_fault_leaf_and_validates_raw_before_typed(self):
        source = (registration.HERE/registration.CAPTURE).read_text()
        self.assertEqual(source.count('__declspec(noinline)'), 2)
        header = source.split('bool copy_header_leaf', 1)[1].split('#else', 1)[0]
        self.assertIn('std::memcpy(target, source, span)', header)
        self.assertIn('__try { *target = *source;', header)
        self.assertEqual(header.count('EXCEPTION_CONTINUE_SEARCH'), 2)
        self.assertEqual(header.count('EXCEPTION_ACCESS_VIOLATION'), 2)
        self.assertEqual(header.count('EXCEPTION_IN_PAGE_ERROR'), 2)
        for forbidden in ('std::string', 'std::lock_guard', 'throw ', 'ReadProcessMemory', 'ZONETOOL_'):
            self.assertNotIn(forbidden, header)
        record = source.split('void record(', 1)[1].split('nlohmann::ordered_json finish(', 1)[0]
        self.assertLess(record.index('target[offsetof(GfxImage, delayLoadPixels)] <= 1'), record.index('GfxImage copied{}'))
        self.assertLess(record.index('first == second && first_name == second_name'), record.index('scalar::build('))
        self.assertLess(record.index('read.unchanged(pointer, model)'), record.index('scalar::build('))
        finish = re.sub(r'//[^\n]*', '', source.split('nlohmann::ordered_json finish(', 1)[1])
        for forbidden in ('read.one(', 'read.range(', 'read.name(', 'copied.name', 'binding.image', 'copy_leaf('):
            self.assertNotIn(forbidden, finish)
        self.assertIn('result["image"] = image_', finish)

    def test_closed_shape_is_the_consumer_contract_and_copies_have_no_lifetime_claim(self):
        from registration_image_request import OUTER
        source = (registration.HERE/registration.CAPTURE).read_text()
        envelope = source.split('inline nlohmann::ordered_json envelope(', 1)[1].split('    class cache', 1)[0]
        keys = set(re.findall(r'\{"([a-z0-9_]+)",', envelope))
        self.assertEqual(keys, OUTER)
        self.assertEqual(len(keys), 33)
        for key in ('same_object_proven', 'allocation_retained', 'atomic_snapshot_proven',
                    'runtime_abi_proven', 'lifetime_proven', 'pixels_copied', 'ready'):
            self.assertIn('{"'+key+'", false}', envelope)
        fixture = (registration.HERE/registration.FIXTURE).read_text()
        self.assertEqual(fixture.count('check('), 33)
        self.assertIn('if (checks != 39)', fixture)  # One seven-key loop adds six.
        self.assertIn('VirtualProtect(page,4096,PAGE_NOACCESS', fixture)
        self.assertIn('VirtualProtect(name_page,4096,PAGE_NOACCESS', fixture)
        self.assertIn('capture::copy_name_byte_leaf', fixture)
        self.assertIn('original_calls == 1', fixture)
        self.assertIn('reset_cache.reset()', fixture)
        self.assertNotIn('IN_PAGE_ERROR', fixture)  # No invented measured in-page fault.

    @unittest.skipUnless(os.environ.get('IW7_T7_SOURCE'), 'Exact pinned native SOURCE not supplied')
    def test_actual_renderer_keeps_base_api_frozen_and_new_guards_parse(self):
        base = ProvenanceTransitionTests()
        main, cli = base.base()
        f2main, f2cli, _ = provenance.overlay(main, cli, base.read)
        old_main, old_cli, _ = metadata.overlay(f2main, f2cli, base.read)
        observer = base.read(registration.HERE/provenance.HELPER, 32*1024)
        derived = registration.observer_source(observer)
        output_main, output_cli = registration.wire(old_main, old_cli, observer,
            base.read(registration.HERE/registration.CAPTURE, 32*1024),
            base.read(registration.HERE/registration.ENTRY, 16*1024))
        sealed_main, sealed_cli, marker = registration.overlay(old_main, old_cli, base.read)
        self.assertEqual((sealed_main, sealed_cli), (output_main, output_cli))
        self.assertTrue(marker['SourceOnlyPending'])
        self.assertFalse(marker['CPPQualified'])
        self.assertFalse(marker['Ready'])
        self.assertEqual((len(observer), hashlib.sha256(observer).hexdigest()), registration.BASE_OBSERVER)
        record_call = derived.index('registration_copy_.record(')
        self.assertLess(derived.index('registration_ = capture('), record_call)
        self.assertLess(record_call, derived.index('template <typename OriginalAdd>'))
        self.assertIn('const auto returned = original(type, incoming);', derived)
        self.assertIn('return returned; // Already a HEADER.', derived)
        self.assertIn('registration_copy_.reset()', derived)
        self.assertEqual(output_main.count(registration.FLAG), 2)
        self.assertEqual(output_cli.count('class cache\n'), 1)
        self.assertLess(len(output_cli.encode()), 192*1024)
        for selector, option in (('registration_metadata', 't7-iw7-image-registration-metadata-v1'),
                                 ('image_metadata', 't7-iw7-image-metadata-v1'),
                                 ('provenance', 't7-iw7-image-provenance-v1')):
            statement = MetadataSourceTests.cli_guard(output_cli, selector)
            expression = compile(MetadataSourceTests.python_predicate(statement), '<registration guard>', 'eval')
            self.assertFalse(eval(expression, {'__builtins__': {}}, {selector: True, 'flags': {option}}))
            self.assertTrue(eval(expression, {'__builtins__': {}}, {selector: False, 'flags': {option}}))
            other = 't7-iw7-image-registration-metadata-v1' if selector != 'registration_metadata' else 't7-iw7-image-metadata-v1'
            self.assertTrue(eval(expression, {'__builtins__': {}}, {selector: True, 'flags': {option, other}}))
        with self.assertRaises(ValueError):
            registration.wire(output_main, output_cli, observer, b'', b'')


if __name__ == '__main__':
    unittest.main()
