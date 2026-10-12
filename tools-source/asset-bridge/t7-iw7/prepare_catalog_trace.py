"""Add bounded startup/exit observations to the existing catalogue command."""
import hashlib
import json
from pathlib import PureWindowsPath
import prepare_cli

NAME = 't7-catalog-trace'
OPTION = '-t7-iw7-catalog'
SCHEMA = 'iw7.t7-catalog-trace/1'
BASE_PLAN_SHA = 'daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa'
BASE_RECEIPT_SHA = 'c609bc56523654d8bca4b855024a463393185aab8e19ed4eae94c1ff8f6a09c2'

SUPPORT = r'''
namespace
{
	bool catalog_trace_enabled = false;
	volatile LONG catalog_trace_seen = 0;

	void catalog_trace_once(const LONG bit, const char* phase, const int code = 0, void* address = nullptr)
	{
		if (!catalog_trace_enabled || (InterlockedOr(&catalog_trace_seen, bit) & bit)) return;
		std::fprintf(stderr, "[T7_CATALOG_TRACE] schema=iw7.t7-catalog-trace/1 phase=%s code=%d tid=%lu return_address=%p\n",
			phase, code, GetCurrentThreadId(), address);
		std::fflush(stderr);
	}

	void catalog_trace_initialize()
	{
		int count = 0;
		auto* args = CommandLineToArgvW(GetCommandLineW(), &count);
		if (!args) return;
		catalog_trace_enabled = count == 3 && std::wcscmp(args[1], L"-t7-iw7-catalog") == 0 && args[2][0] != L'\0';
		LocalFree(args);
		if (!catalog_trace_enabled || (InterlockedOr(&catalog_trace_seen, 1) & 1)) return;
		const int out_result = std::setvbuf(stdout, nullptr, _IONBF, 0);
		const int err_result = std::setvbuf(stderr, nullptr, _IONBF, 0);
		std::fprintf(stderr, "[T7_CATALOG_TRACE] schema=iw7.t7-catalog-trace/1 phase=enabled stdout_unbuffered=%d stderr_unbuffered=%d tid=%lu\n",
			out_result == 0, err_result == 0, GetCurrentThreadId());
		std::fflush(stderr);
	}
}
'''


def wire_main(source):
    once = prepare_cli.helper.once
    source = once(source, '#include <std_include.hpp>', '#include <std_include.hpp>\n#include <intrin.h>\n#include <cwchar>\n#include <cstdio>')
    anchor = '#define T7_BINARY "BlackOps3_UnrankedDedicatedServer.exe"'
    source = once(source, anchor, anchor+'\n'+SUPPORT)
    source = once(source, '\tDECLSPEC_NORETURN void WINAPI exit_hook(const int code)\n\t{',
        '\tDECLSPEC_NORETURN void WINAPI exit_hook(const int code)\n\t{\n'
        '\t\tcatalog_trace_once(32, "exit_hook", code, _ReturnAddress());')
    anchor = '\t\tBOOL set_process_dpi_aware_stub()\n\t\t{\n\t\t\tcomponent_loader::post_unpack();'
    source = once(source, anchor, '\t\tBOOL set_process_dpi_aware_stub()\n\t\t{\n'
        '\t\t\tcatalog_trace_once(2, "before_post_unpack");\n'
        '\t\t\tcomponent_loader::post_unpack();\n'
        '\t\t\tcatalog_trace_once(4, "after_post_unpack");')
    source = once(source, '\t\treturn static_cast<int>(entry_point());',
        '\t\tcatalog_trace_once(8, "before_entry_point");\n'
        '\t\tconst auto result = static_cast<int>(entry_point());\n'
        '\t\tcatalog_trace_once(16, "entry_point_return", result);\n'
        '\t\treturn result;')
    return once(source, 'int main()\n{', 'int main()\n{\n\tcatalog_trace_initialize();')


def verify_base(plan_raw, receipt_raw, prior_raw, prior_receipt_raw, payloads):
    """Compare small text manifests only; never open retained binary inputs."""
    def require(ok, message):
        if not ok: raise ValueError(message)
    def key(path): return str(PureWindowsPath(path)).casefold()
    require(hashlib.sha256(plan_raw).hexdigest() == BASE_PLAN_SHA and
            hashlib.sha256(receipt_raw).hexdigest() == BASE_RECEIPT_SHA, 'Exact ordinary D2 proof required')
    base, receipt, prior, old_receipt = map(json.loads, (plan_raw, receipt_raw, prior_raw, prior_receipt_raw))
    require(base['Schema'] == 'iw7.t7-minimal-build-plan/1' and not base.get('BuildProfile') and
            receipt['Schema'] == 'iw7.t7-minimal-build/1' and not receipt.get('BuildProfile') and
            receipt['PlanSHA256'] == BASE_PLAN_SHA and receipt['Status'] == 'Passed' and
            all(receipt[n] is True for n in ('InputsReverified','TreeClosureConfirmed','LeaseReleased')) and
            receipt['Quarantined'] is False, 'Passed ordinary D2 identity differs')
    require(base['ReuseCompile']['SourcePlanSHA256'] == hashlib.sha256(prior_raw).hexdigest() and
            base['ReuseCompile']['ReceiptSHA256'] == hashlib.sha256(prior_receipt_raw).hexdigest() and
            not base['ReuseCompile'].get('RecompiledMain', False), 'D2 retained compilation chain differs')
    require([s['Name'] for s in base['Stages']] == ['link'] and
            [s['Name'] for s in receipt['Stages']] == ['link'] and
            receipt['Stages'][0]['ExitCode'] == 0 and receipt['Stages'][0]['TreeClosureConfirmed'] is True,
            'Successful single Link required for D2')
    for plan in (base, prior):
        bindings = {key(p['Path']):p for p in plan['Bindings']}
        root = PureWindowsPath(plan['PreparedRoot'])
        for name, raw in payloads.items():
            if not name.startswith('prepared/'): continue
            pin = bindings.get(key(root/name.removeprefix('prepared/')))
            require(pin and pin['Bytes'] == len(raw) and pin['SHA256'] == hashlib.sha256(raw).hexdigest(),
                    'Ordinary D2/C native source differs: '+name)
    inputs = {key(p['Path']):p for p in base['Inputs']}
    for stage in old_receipt['Stages'][:5]:
        for pin in stage.get('Artifacts', []):
            actual = inputs.get(key(pin['Path']))
            require(actual and actual['Bytes'] == pin['Bytes'] and actual['SHA256'] == pin['SHA256'],
                    'D2 retained object/helper proof differs')
