"""Prepare a fresh, small MSBuild overlay. Never writes to the retained fork."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
NS = 'http://schemas.microsoft.com/developer/msbuild/2003'
ET.register_namespace('', NS)
def q(name): return '{' + NS + '}' + name
def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
def lf_digest(path): return hashlib.sha256(path.read_text(encoding='utf-8').encode()).hexdigest()
def run(*args, cwd):
    return subprocess.check_output(args, cwd=cwd, text=True, stderr=subprocess.STDOUT).strip()
def put(parent, name, value):
    node = parent.find(q(name))
    if node is None: node = ET.SubElement(parent, q(name))
    node.text = str(value)
    return node

def prepare(source, output):
    source, output = source.resolve(strict=True), output.resolve()
    plan = json.loads((HERE / 'full-build-plan-2026-10-12.json').read_text())
    repair = json.loads((HERE / 'map-layout-source.json').read_text())
    if repair['source_pin'] != plan['reference_pin']: raise ValueError('Repair source pin differs')
    plan['patched_files'].update(repair['files'])
    plan['patches'][repair['patch']] = repair['sha256']
    if output.exists(): raise ValueError('Fresh absent output directory required')
    if source in output.parents or output in source.parents: raise ValueError('Separate overlay required')
    if run('git', 'rev-parse', 'HEAD', cwd=source) != plan['reference_pin']:
        raise ValueError('Retained fork pin differs')
    if run('git', 'status', '--porcelain', '--untracked-files=no', cwd=source):
        raise ValueError('Retained tracked source is dirty')
    submodules = run('git', 'submodule', 'status', cwd=source)
    if any(line[0] in '-+U' for line in submodules.splitlines()):
        raise ValueError('Submodule pin or availability differs')
    output.mkdir(parents=True)
    patched = output / 'patch-inputs'
    patched.mkdir()
    for relative, pins in plan['patched_files'].items():
        original = source / relative
        if lf_digest(original) != pins['base_lf_sha256']: raise ValueError(relative)
        target = patched / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(original.read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
    patches = [HERE / 'zonetool-fab9358-h1-xsurface.patch', HERE.parent / 'surfaces/strict-content-sources.patch',
               HERE / repair['patch']]
    # A tiny standalone temporary repository avoids git discovering our parent worktree.
    run('git', 'init', '--quiet', cwd=patched)
    for patch in patches:
        if digest(patch) != plan['patches'][patch.name]: raise ValueError('Patch pin differs')
        run('git', 'apply', '--check', str(patch), cwd=patched)
        run('git', 'apply', str(patch), cwd=patched)
    redirects = {}
    for index, (relative, pins) in enumerate(plan['patched_files'].items()):
        target = patched / relative
        if lf_digest(target) != pins['patched_lf_sha256']: raise ValueError('Patched digest differs')
        # Short paths also keep MSVC debug record names below Windows path limits.
        short = output / f'{index}-{target.name}'
        short.write_bytes(target.read_bytes())
        redirects[str((source / relative).resolve())] = short
    generated = output / 'generated'
    generated.mkdir()
    version = (source / 'build/src/version.h').read_text()
    version = version.replace('#define GIT_DIRTY 0', '#define GIT_DIRTY 1')
    version = version.replace('latest-8-gfab9358', 'fab9358-community-h1-strict-source')
    (generated / 'version.h').write_text(version, encoding='utf-8')
    (generated / 'version.hpp').write_text('#pragma once\n#include "version.h"\n')
    rc = (source / 'src/zonetool/resource.rc').read_text()
    resources = {
        'resources/icon.ico': source / 'src/zonetool/resources/icon.ico',
        'resources/h1_mp64_zt': source / 'src/zonetool/resources/h1_mp64_zt',
        '../../build/bin/x64/Debug/tlsdll.dll': source / 'build/bin/x64/Release/tlsdll.dll',
        '../../build/bin/x64/Release/tlsdll.dll': source / 'build/bin/x64/Release/tlsdll.dll',
    }
    for old, path in resources.items():
        if not path.is_file(): raise ValueError(str(path))
        rc = rc.replace('"' + old + '"', '"' + path.as_posix() + '"')
    (output / 'resource.rc').write_text(rc, encoding='utf-8')
    tree = ET.parse(source / 'build/zonetool.vcxproj')
    root = tree.getroot()
    refs = root.findall('.//' + q('ProjectReference') + '[@Include]')
    libs = [source / 'build/bin/x64/Release' / (Path(n.attrib['Include']).stem + '.lib') for n in refs]
    if len(libs) != 18 or not all(p.is_file() for p in libs): raise ValueError('Dependencies differ')
    for parent in root.iter():
        for node in list(parent):
            tag = node.tag.split('}')[-1]
            if tag in ('ProjectReference', 'PreBuildEvent', 'PostBuildEvent', 'CustomBuild') or (
                tag == 'ImportGroup' and node.get('Label') == 'PropertySheets'):
                parent.remove(node)
    globals_node = root.find(q('PropertyGroup'))
    for name, value in {'ImportDirectoryBuildProps':'false', 'ImportDirectoryBuildTargets':'false',
                        'WindowsTargetPlatformVersion':'10.0.26100.0', 'VCToolsVersion':'14.44.35207'}.items():
        put(globals_node, name, value)
    for node in root.iter():
        tag = node.tag.split('}')[-1]
        if tag in ('ClCompile', 'ClInclude', 'None', 'ResourceCompile') and 'Include' in node.attrib:
            original = (source / 'build' / node.attrib['Include']).resolve(strict=True)
            replacement = redirects.get(str(original), original)
            if tag == 'ResourceCompile': replacement = output / 'resource.rc'
            node.set('Include', str(replacement))
            if str(original) in redirects:
                put(node, 'AdditionalIncludeDirectories', str(original.parent) + ';%(AdditionalIncludeDirectories)')
        if tag == 'AdditionalIncludeDirectories' and node.text:
            paths = []
            for item in node.text.split(';'):
                if item == 'src' or item == '$(ProjectDir)src': paths.append(str(generated))
                elif item.startswith('%('): paths.append(item)
                elif '$(' in item: raise ValueError('Unknown input macro: ' + item)
                else: paths.append(str((source / 'build' / item).resolve(strict=True)))
            node.text = ';'.join(paths)
        if tag in ('OutDir', 'IntDir'): node.text = str(output / ('bin' if tag == 'OutDir' else 'obj')) + '\\'
        if tag == 'TargetName': node.text = 'zonetool-community'
        if tag == 'PreprocessorDefinitions': node.text = 'EXPERIMENTAL_IW7;' + node.text
    for group in root.findall(q('ItemDefinitionGroup')):
        compile_node = group.find(q('ClCompile'))
        put(compile_node, 'PrecompiledHeaderOutputFile', '$(IntDir)community.pch')
        put(compile_node, 'ProgramDataBaseFileName', '$(IntDir)community-compile.pdb')
        put(compile_node, 'ObjectFileName', '$(IntDir)')
        link = group.find(q('Link'))
        put(link, 'AdditionalDependencies', ';'.join(map(str, libs)) + ';%(AdditionalDependencies)')
        put(link, 'ProgramDatabaseFile', '$(OutDir)zonetool-community.pdb')
        put(link, 'ImportLibrary', '$(OutDir)zonetool-community.lib')
        put(link, 'OutputFile', '$(OutDir)zonetool-community.exe')
        put(group.find(q('ResourceCompile')), 'ResourceOutputFileName', '$(IntDir)resource.res')
    for group in root.findall(q('PropertyGroup')):
        if group.find(q('IntDir')) is not None:
            put(group, 'TLogLocation', '$(IntDir)tlog\\')
            put(group, 'BuildProjectReferences', 'false')
    project = output / 'zonetool-community.vcxproj'
    ET.indent(tree, space='  ')
    tree.write(project, encoding='utf-8', xml_declaration=True)
    inputs = libs + list(set(resources.values())) + [source / 'build/zonetool.vcxproj',
              source / 'build/bin/x64/Release/zonetool.exe', source / 'build/bin/x64/Release/zonetool.pdb']
    inputs += [source / p for p in plan['patched_files']]
    evidence = {'schema':'iw7.zonetool-isolated-overlay/1', 'source':str(source), 'output':str(output),
        'source_pin':plan['reference_pin'], 'submodules':submodules.splitlines(), 'patches':plan['patches'],
        'compile_units':len(root.findall('.//' + q('ClCompile') + '[@Include]')), 'patched_units':len(redirects),
        'experimental_unvalidated_capabilities':[repair['capability']],
        'dependency_libraries':len(libs), 'feature_macro':'EXPERIMENTAL_IW7', 'project_sha256':digest(project),
        'readonly_inputs':[{ 'path':str(p), 'bytes':p.stat().st_size, 'sha256':digest(p)} for p in inputs],
        'new_artifact_hard_ceiling':2*1024**3, 'stop_at_bytes':1600*1024**2}
    if evidence['compile_units'] != 413: raise ValueError('Compile unit count changed')
    (output / 'preparation.local.json').write_text(json.dumps(evidence, indent=2) + '\n')
    size = sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
    if size > 2*1024**2: raise ValueError('Preparation exceeded 2 MiB')
    print(json.dumps({'project':str(project), 'preparation_bytes':size, 'compile_units':413, 'libraries':18}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    prepare(args.source, args.output)
