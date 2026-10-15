"""Finite declaration-only compiler input roles; never queries any filesystem.

The caller pins the historical plan/response/environment before passing them.
Roots describe compiler roles, not file suffixes. Only exact existing declared
path/length/SHA tuples are imported. Actual byte verification remains admitted
H1 Open-T7Pin work; this module never classifies inherited inputs as IsText.
"""
import re
from pathlib import PureWindowsPath

ROLES = ('CompilerInclude', 'CompilerRuntime', 'FixtureLinkInput')


def require(value, message):
    if not value:
        raise ValueError(message)


def identity(text):
    require(isinstance(text, str) and text and not any(ord(c) < 32 or c == '"' for c in text),
            'Ordinary lexical Windows path required')
    parts = re.split(r'[\\/]', text)
    require(not any(part in ('.', '..') for part in parts), 'Relative path segments refused')
    require(not any(part.endswith(('.', ' ')) for part in parts if part), 'Win32 trailing dot/space aliases refused')
    path = PureWindowsPath(text)
    require(path.is_absolute() and re.fullmatch(r'[a-zA-Z]:', path.drive) and ':' not in text[2:],
            'Absolute drive path without alternate stream required')
    require(not path.is_reserved(), 'Reserved path refused')
    return tuple(part.casefold() for part in path.parts)


def role_roots(include_roots, runtime_roots, library_roots):
    result = []
    for role, roots in zip(ROLES, (include_roots, runtime_roots, library_roots)):
        require(isinstance(roots, (list, tuple)) and roots, 'Explicit roots for each compiler role required')
        seen = set()
        for root in roots:
            key = identity(root)
            if key not in seen:
                result.append({'Role': role, 'Root': root, 'Identity': key}); seen.add(key)
    # Attribute overlaps to the most specific declared root, deterministically.
    return sorted(result, key=lambda row: (-len(row['Identity']), ROLES.index(row['Role']), row['Identity']))


def from_pinned_response_environment(response, environment):
    """Parse only the reviewed quoted /I roots and sealed INCLUDE/PATH/LIB strings."""
    require(isinstance(response, str) and len(response.encode()) <= 1048576, 'Bounded response Source required')
    require(isinstance(environment, dict), 'Pinned sealed environment object required')
    includes = re.findall(r'(?:^|\s)/I"([^"\r\n]+)"(?=\s|$)', response, re.I)
    # No bare /I form is silently omitted from this closed source profile.
    require(len(re.findall(r'(?:^|\s)/I', response, re.I)) == len(includes), 'Every /I root must be explicitly quoted')
    values = []
    for name in ('INCLUDE', 'PATH', 'LIB'):
        value = environment.get(name)
        require(isinstance(value, str) and value and len(value) <= 32768, 'Finite pinned environment roots required')
        roots = value.split(';')
        require(all(roots), 'Empty implicit environment search root refused')
        for root in roots:
            identity(root)
        values.append(roots)
    return role_roots(includes + values[0], values[1], values[2])


def classify(declarations, roots, *, parent_plan_sha256):
    require(isinstance(declarations, list) and 0 < len(declarations) <= 4096, 'Finite inherited declarations required')
    require(re.fullmatch('[0-9a-f]{64}', parent_plan_sha256 or ''), 'Pinned parent plan required')
    require(isinstance(roots, list) and 0 < len(roots) <= 128 and
            all(isinstance(row, dict) and row.get('Role') in ROLES for row in roots), 'Closed compiler roles required')
    checked_roots = []
    for row in roots:
        root_identity = identity(row.get('Root'))
        require(tuple(row.get('Identity', root_identity)) == root_identity, 'Role root identity drift')
        checked_roots.append(dict(row, Identity=root_identity))
    roots = sorted(checked_roots, key=lambda row: (-len(row['Identity']), ROLES.index(row['Role']), row['Identity']))
    selected, excluded, seen = [], [], set()
    for original in declarations:
        require(isinstance(original, dict), 'Input declaration required')
        path, length, digest = original.get('Path'), original.get('Bytes'), original.get('SHA256')
        key = identity(path)
        require(key not in seen, 'Duplicate declared input identity')
        seen.add(key)
        require(type(length) is int and 0 < length <= 268435456 and
                isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest), 'Exact inherited length/hash tuple required')
        matched = next((row for row in roots if len(key) > len(row['Identity']) and
                        key[:len(row['Identity'])] == row['Identity']), None)
        item = {'Path': path, 'Bytes': length, 'SHA256': digest}
        if matched:
            item.update(InputRole=matched['Role'], DeclaredRoleRoot=matched['Root'],
                        ParentPlanSHA256=parent_plan_sha256, AdmissionRequired=True)
            selected.append(item)
        else:
            item['ExclusionReason'] = 'Outside explicit compiler include/runtime/fixture-library roots'
            excluded.append(item)
    return {'Schema': 'iw7.neutral-compiler-input-roles/1', 'ParentPlanSHA256': parent_plan_sha256,
            'Roots': [{'Role': row['Role'], 'Root': row['Root']} for row in roots],
            'Selected': selected, 'Excluded': excluded, 'InheritedInputsRead': False,
            'FilesystemQueried': False, 'IsTextClassificationInherited': False}
