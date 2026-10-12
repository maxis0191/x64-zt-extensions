"""Wire the bounded pre-patch helper into an already pinned T7 main overlay."""
import prepare_cli

NAME = 't7-prepatch-probe'
OPTION = '-'+NAME
REPORT = NAME+'.local.json'
HELPER = 'native_prepatch_probe.inc'
API = 'zonetool::t7_prepatch_probe'


def wire_main(source):
    """No engine files are opened, patched or executed by this transformation."""
    once = prepare_cli.helper.once
    source = once(source, '#define T7_BINARY "BlackOps3_UnrankedDedicatedServer.exe"',
        '#define T7_BINARY "BlackOps3_UnrankedDedicatedServer.exe"\n\n#include "'+HELPER+'"')
    source = once(source, '\tnamespace t7\n\t{', '''\tnamespace t7
\t{
\t\tDECLSPEC_NORETURN void WINAPI prepatch_early_exit(const int)
\t\t{
\t\t\tstd::fputs("T7 pre-patch probe: engine exited before capture.\\n", stderr);
\t\t\texit_hook(2);
\t\t}''')
    source = once(source, '\t\tBOOL set_process_dpi_aware_stub()\n\t\t{', '''\t\tBOOL set_process_dpi_aware_stub()
\t\t{
\t\t\tif (zonetool::t7_prepatch_probe::requested())
\t\t\t{
\t\t\t\texit_hook(zonetool::t7_prepatch_probe::capture());
\t\t\t}''')
    # Only the T7 resolver receives this exit-before-rendezvous refusal.
    begin = source.index('\tnamespace t7\n')
    end = source.index('\tnamespace iw7\n', begin)
    t7 = once(source[begin:end], '\t\t\t\t\treturn exit_hook;', '''\t\t\t\t\tif (zonetool::t7_prepatch_probe::requested()) return prepatch_early_exit;
\t\t\t\t\treturn exit_hook;''')
    source = source[:begin]+t7+source[end:]
    source = once(source, 'int main()\n{', '''int main()
{
\tif (zonetool::t7_prepatch_probe::requested())
\t{
\t\tif (!zonetool::t7_prepatch_probe::validate_invocation())
\t\t{
\t\t\treturn 2;
\t\t}
\t\tif (!utils::io::file_exists(T7_BINARY))
\t\t{
\t\t\tstd::fputs("T7 pre-patch probe requires the pinned dedicated engine.\\n", stderr);
\t\t\treturn 2;
\t\t}
\t}''')
    source = once(source, '\treturn main_internal();', '''\tif (zonetool::t7_prepatch_probe::requested() && game::get_mode() != game::t7)
\t{
\t\tstd::fputs("T7 pre-patch probe refuses competing engine mode.\\n", stderr);
\t\treturn 2;
\t}
\treturn main_internal();''')
    for phase in ('post_start', 'post_load'):
        anchor = '\t\t\t\tif (!component_loader::'+phase+'())\n\t\t\t\t{\n\t\t\t\t\treturn 0;'
        source = once(source, anchor, anchor.removesuffix('return 0;')+
            'return zonetool::t7_prepatch_probe::requested() ? 2 : 0;')
    source = once(source, '\t\t\t\tMessageBoxA(nullptr, e.what(), "ERROR", MB_ICONERROR);', '''\t\t\t\tif (zonetool::t7_prepatch_probe::requested())
\t\t\t\t{
\t\t\t\t\tstd::fprintf(stderr, "T7 pre-patch probe loading failed: %s\\n", e.what());
\t\t\t\t\treturn 2;
\t\t\t\t}
\t\t\t\tMessageBoxA(nullptr, e.what(), "ERROR", MB_ICONERROR);''')
    source = once(source, '\t\treturn static_cast<int>(entry_point());', '''\t\tconst auto result = static_cast<int>(entry_point());
\t\tif (zonetool::t7_prepatch_probe::requested())
\t\t{
\t\t\tstd::fputs("T7 pre-patch probe: entrypoint returned without capture.\\n", stderr);
\t\t\treturn 2;
\t\t}
\t\treturn result;''')
    return source
