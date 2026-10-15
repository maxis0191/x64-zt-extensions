"""Declaration-only tests: no compiler, SDK/header read or native process."""
import unittest
from unittest.mock import patch
import neutral_dependency_inputs as production


class InputRoleTests(unittest.TestCase):
    def roots(self):
        return production.role_roots([r'C:\native\src', r'C:\native\deps\gsl\include', r'C:\sdk\include'],
                                     [r'C:\compiler\bin', r'C:\sdk\bin'], [r'C:\sdk\lib'])

    def pin(self, path):
        return {'Path': path, 'Bytes': 123, 'SHA256': 'a' * 64}

    def classify(self, rows):
        return production.classify(rows, self.roots(), parent_plan_sha256='b' * 64)

    def test_extensionless_headers_and_other_names_are_role_based_without_io(self):
        rows = [self.pin(r'C:\native\deps\gsl\include\gsl\gsl'), self.pin(r'C:\sdk\include\standard_header'),
                self.pin(r'C:\native\src\asset.hpp')]
        with patch('builtins.open', side_effect=AssertionError('No filesystem IO')):
            result = self.classify(rows)
        self.assertEqual(len(result['Selected']), 3)
        self.assertTrue(all(p['InputRole'] == 'CompilerInclude' and p['AdmissionRequired'] and 'IsText' not in p for p in result['Selected']))
        self.assertFalse(result['FilesystemQueried'])

    def test_exact_tuple_preserved_and_runtime_library_roles_are_distinct(self):
        rows = [self.pin(r'C:\compiler\bin\cl.exe'), self.pin(r'C:\sdk\lib\runtime.lib')]
        result = self.classify(rows)
        self.assertEqual([x['InputRole'] for x in result['Selected']], ['CompilerRuntime', 'FixtureLinkInput'])
        for before, after in zip(rows, result['Selected']):
            self.assertEqual({k: after[k] for k in before}, before)

    def test_historical_outputs_and_near_prefix_paths_are_excluded(self):
        rows = [self.pin(r'C:\historical\obj\weapon.obj'), self.pin(r'C:\historical\symbols\tool.pdb'),
                self.pin(r'C:\native\deps\gsl\include-elsewhere\gsl')]
        self.assertEqual(self.classify(rows)['Selected'], [])

    def test_duplicate_drifted_or_nonabsolute_declarations_refuse(self):
        pin = self.pin(r'C:\native\src\a.hpp')
        for rows in ([pin, dict(pin)], [dict(pin, SHA256='wrong')], [dict(pin, Bytes=0)],
                     [dict(pin, Path=r'C:\native\src\..\a.hpp')], [dict(pin, Path='relative.hpp')],
                     [dict(pin, Path=r'C:\native\src\a.hpp:stream')]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.classify(rows)

    def test_response_and_environment_assign_roles_without_suffix_guess(self):
        roots = production.from_pinned_response_environment('/I"C:\\native\\deps\\gsl\\include" /c input.cpp',
            {'INCLUDE': r'C:\sdk\include', 'PATH': r'C:\compiler\bin', 'LIB': r'C:\sdk\lib'})
        result = production.classify([self.pin(r'C:\native\deps\gsl\include\gsl\gsl')], roots, parent_plan_sha256='b' * 64)
        self.assertEqual(result['Selected'][0]['DeclaredRoleRoot'], r'C:\native\deps\gsl\include')
        with self.assertRaisesRegex(ValueError, 'quoted'):
            production.from_pinned_response_environment('/IC:\\native /c a.cpp', {'INCLUDE': r'C:\sdk\include', 'PATH': r'C:\compiler\bin', 'LIB': r'C:\sdk\lib'})

    def test_missing_roles_or_implicit_search_roots_refuse(self):
        with self.assertRaises(ValueError):
            production.role_roots([], [r'C:\bin'], [r'C:\lib'])
        with self.assertRaises(ValueError):
            production.from_pinned_response_environment('/I"C:\\native"', {'INCLUDE': r'C:\sdk;', 'PATH': r'C:\bin', 'LIB': r'C:\lib'})
        roots = self.roots(); roots[0]['Identity'] = ('wrong',)
        with self.assertRaisesRegex(ValueError, 'identity drift'):
            production.classify([self.pin(r'C:\native\src\a.hpp')], roots, parent_plan_sha256='b' * 64)

    def test_attached_include_suffix_refuses_instead_of_truncating_root(self):
        environment = {'INCLUDE': r'C:\sdk\include', 'PATH': r'C:\compiler\bin', 'LIB': r'C:\sdk\lib'}
        for response in ('/I"C:\\native\\include"suffix /c input.cpp', '/I"C:\\native"/I"C:\\other"'):
            with self.subTest(response=response), self.assertRaisesRegex(ValueError, 'quoted'):
                production.from_pinned_response_environment(response, environment)

    def test_win32_alias_components_refuse_for_leaf_directory_and_root(self):
        for path in (r'C:\native\src\a.hpp.', 'C:\\native\\src\\a.hpp ',
                     r'C:\native.\src\a.hpp', 'C:\\native \\src\\a.hpp'):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'trailing dot/space'):
                self.classify([self.pin(r'C:\native\src\a.hpp'), self.pin(path)])
        for root in (r'C:\native\include.', 'C:\\native\\include '):
            with self.subTest(root=root), self.assertRaisesRegex(ValueError, 'trailing dot/space'):
                production.role_roots([root], [r'C:\compiler\bin'], [r'C:\sdk\lib'])


if __name__ == '__main__':
    unittest.main()
