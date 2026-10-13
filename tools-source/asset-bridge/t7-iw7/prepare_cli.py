"""Prepare/check a pinned T7 CLI patch. Never modifies native source or builds."""
import argparse
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
helper_spec = importlib.util.spec_from_file_location('recipient_source_snapshot',
    HERE.parent/'recipient/script-names/prepare_observer.py')
helper = importlib.util.module_from_spec(helper_spec)
helper_spec.loader.exec_module(helper)
PATHS = ('src/zonetool/main.cpp', 'src/zonetool/zonetool/t7/zonetool.cpp',
         'src/zonetool/zonetool/t7/common/xpak.cpp', 'src/zonetool/zonetool/t7/common/xpak.hpp')
PATCH = HERE/'zonetool-fab9358-t7-resident-cli.patch'


def render(native):
    pins = json.loads((HERE/'source-inventory.json').read_text(encoding='utf-8'))['files']
    originals = {}
    for name in PATHS:
        data = helper.source_snapshot(Path(native)/name)
        if len(data) != pins[name]['bytes'] or hashlib.sha256(data).hexdigest() != pins[name]['sha256']:
            raise ValueError('Pinned T7 source differs: '+name)
        originals[name] = data.decode('utf-8').replace('\r\n', '\n')
    patched = dict(originals)
    main, target, xpak, header = PATHS
    patched[main] = helper.once(patched[main], 'int main()\n{', '''int main()
{
	if ((utils::flags::has_flag("t7-iw7-model") || utils::flags::has_flag("t7-iw7-model-v2") || utils::flags::has_flag("t7-iw7-catalog")) && !utils::io::file_exists(T7_BINARY))
	{
		std::fputs("T7 resident export requires the pinned unranked dedicated engine.\\n", stderr);
		return EXIT_FAILURE;
	}''')
    patched[main] = helper.once(patched[main], '\treturn main_internal();', '''	if ((utils::flags::has_flag("t7-iw7-model") || utils::flags::has_flag("t7-iw7-model-v2") || utils::flags::has_flag("t7-iw7-catalog")) && game::get_mode() != game::t7)
	{
		std::fputs("T7 resident export refuses competing engine mode.\\n", stderr);
		return EXIT_FAILURE;
	}
	return main_internal();''')
    includes = '''#include "common/xpak.hpp"
#include <utils/cryptography.hpp>
#include <utils/flags.hpp>
#include "t7_iw7_resident_model.hpp"
#include <atomic>
#include <mutex>

namespace zonetool::iw7
{
	void write_enemy_reference_output(const std::filesystem::path&, const std::string&);
}'''
    patched[target] = helper.once(patched[target], '#include "common/xpak.hpp"', includes)
    capture = (HERE/'native_catalog_capture.inc').read_text(encoding='utf-8')
    patched[target] = helper.once(patched[target], '\tutils::hook::detour db_add_xasset_hook;',
        '\n'.join('\t'+line if line else '' for line in capture.splitlines())+'\n\n\tutils::hook::detour db_add_xasset_hook;')
    patched[target] = helper.once(patched[target], '\t\tdump_asset(&xasset);',
        '\t\tresident_catalog_capture(type, header);\n\t\tdump_asset(&xasset);')
    export = (HERE/'native_export.inc').read_text(encoding='utf-8')
    export += '\n'+(HERE/'native_catalog.inc').read_text(encoding='utf-8')
    patched[target] = helper.once(patched[target], '\tvoid handle_params()\n',
        '\n'.join('\t'+line if line else '' for line in export.splitlines())+'\n\n\tvoid handle_params()\n')
    cli = (HERE/'native_cli.inc').read_text(encoding='utf-8')
    patched[target] = helper.once(patched[target], '\t\tauto args = get_command_line_arguments();',
        '\t\tauto args = get_command_line_arguments();\n'+cli)
    patched[header] = helper.once(patched[header], '\t\tvoid clear_cache();',
        '\t\tvoid deny_reads_for_resident_export();\n\t\tvoid clear_cache();')
    patched[xpak] = helper.once(patched[xpak], '#include "lz4.h"', '#include "lz4.h"\n#include <atomic>')
    patched[xpak] = helper.once(patched[xpak], '\tnamespace xpak\n\t{', '''	namespace xpak
	{
		static std::atomic_bool resident_export_reads_denied{false};
		void deny_reads_for_resident_export()
		{
			resident_export_reads_denied.store(true);
		}''')
    key_function = '\t\tstd::vector<std::uint8_t> get_data_for_xpak_key(uint64_t key, const unsigned int expected_size)\n\t\t{'
    patched[xpak] = helper.once(patched[xpak], key_function, key_function+'''
			if (resident_export_reads_denied.load())
				throw std::runtime_error("XPAK payload/index access forbidden by resident export profile");''')
    return originals, patched


def patch_for(native):
    originals, patched = render(native)
    result = []
    for name in PATHS:
        for line in difflib.unified_diff(originals[name].splitlines(keepends=True),
                patched[name].splitlines(keepends=True), fromfile='a/'+name, tofile='b/'+name):
            result.append(line if line.endswith('\n') else line+'\n\\ No newline at end of file\n')
    return ''.join(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    patch = patch_for(args.source)
    if args.check:
        if PATCH.read_text(encoding='utf-8') != patch: raise SystemExit('Prepared patch differs')
    else:
        PATCH.write_text(patch,encoding='utf-8',newline='\n')
    print(json.dumps({'patch_bytes':len(patch.encode()),'patched_source_files':len(PATHS),
                     'translation_units':3,'shared_source_modified':False,'native_compiled':False}))
