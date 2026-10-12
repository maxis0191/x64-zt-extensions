"""Read-only check of generated MSBuild source/output routing before admission."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from prepare_full_build import q, digest

def verify(directory):
    directory = directory.resolve(strict=True)
    prep = json.loads((directory / 'preparation.local.json').read_text())
    source = Path(prep['source']).resolve(strict=True)
    project = directory / 'zonetool-community.vcxproj'
    assert digest(project) == prep['project_sha256'], 'Prepared project changed'
    root = ET.parse(project).getroot()
    assert not root.findall('.//' + q('ProjectReference'))
    for tag in ('PreBuildEvent', 'PostBuildEvent', 'CustomBuild'):
        assert not root.findall('.//' + q(tag)), tag
    compiles = root.findall('.//' + q('ClCompile') + '[@Include]')
    assert len(compiles) == 413
    patched = 0
    for node in root.iter():
        if 'Include' in node.attrib and node.tag in map(q, ('ClCompile','ClInclude','None','ResourceCompile')):
            path = Path(node.attrib['Include'])
            assert path.is_absolute() and path.is_file(), str(path)
            assert source in path.parents or directory in path.parents, str(path)
            if node.tag == q('ClCompile') and directory in path.parents:
                patched += 1
                includes = node.find(q('AdditionalIncludeDirectories')).text.split(';')
                assert Path(includes[0]).is_relative_to(source)
        if node.tag == q('ObjectFileName'):
            assert node.text.startswith('$(IntDir)') and '..' not in node.text, node.text
    assert patched == 4
    for group in root.findall(q('PropertyGroup')):
        if group.find(q('IntDir')) is not None:
            assert Path(group.find(q('IntDir')).text).resolve() == directory / 'obj'
            assert Path(group.find(q('OutDir')).text).resolve() == directory / 'bin'
            assert group.find(q('TLogLocation')).text == '$(IntDir)tlog\\'
    for group in root.findall(q('ItemDefinitionGroup')):
        compile_node = group.find(q('ClCompile'))
        assert 'EXPERIMENTAL_IW7' in compile_node.find(q('PreprocessorDefinitions')).text.split(';')
        assert compile_node.find(q('MultiProcessorCompilation')).text == 'false'
        assert compile_node.find(q('PrecompiledHeaderOutputFile')).text == '$(IntDir)community.pch'
        assert compile_node.find(q('ProgramDataBaseFileName')).text == '$(IntDir)community-compile.pdb'
        link = group.find(q('Link'))
        for tag in ('ProgramDatabaseFile','ImportLibrary','OutputFile'):
            assert link.find(q(tag)).text.startswith('$(OutDir)')
        libs = link.find(q('AdditionalDependencies')).text.split(';')[:-1]
        assert len(libs) == 18 and all(Path(p).is_file() and Path(p).is_relative_to(source) for p in libs)
    allowed = {'$(VCTargetsPath)\\Microsoft.Cpp.Default.props', '$(VCTargetsPath)\\Microsoft.Cpp.props',
               '$(VCTargetsPath)\\Microsoft.Cpp.targets'}
    assert {n.attrib['Project'] for n in root.findall('.//' + q('Import'))} == allowed
    result = {'compile_units':413, 'patched_units':patched, 'dependency_libraries':18,
              'private_output_routing':True, 'macro_enabled':True, 'build_events_removed':True}
    print(json.dumps(result))
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    verify(parser.parse_args().directory)
