"""Add bounded startup/exit observations to the existing catalogue command."""
import hashlib
import json
from pathlib import PureWindowsPath
import prepare_cli

NAME = 't7-catalog-trace'
OPTION = '-t7-iw7-catalog'
SCHEMA = 'iw7.t7-catalog-trace/1'
EXIT_NAME = 't7-catalog-exit-context'
EXIT_SCHEMA = 'iw7.t7-catalog-exit-context/1'
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

EXIT_SUPPORT = r'''
namespace
{
	struct catalog_exit_memory
	{
		const char* status;
		HMODULE module;
		uintptr_t start;
		MEMORY_BASIC_INFORMATION region;
		SIZE_T copied;
		DWORD error;
		unsigned char bytes[256];
	};
	struct catalog_exit_stack
	{
		const char* status;
		void* frames[8];
		USHORT count;
		DWORD error;
	};
	struct catalog_exit_function
	{
		const char* status;
		DWORD64 image;
		PRUNTIME_FUNCTION address;
		RUNTIME_FUNCTION record;
		SIZE_T copied;
		DWORD error;
	};
	static_assert(sizeof(RUNTIME_FUNCTION) == 12);

	bool catalog_exit_readable(const MEMORY_BASIC_INFORMATION& region, const uintptr_t address, const SIZE_T length)
	{
		const auto begin = reinterpret_cast<uintptr_t>(region.BaseAddress);
		return region.State == MEM_COMMIT && (region.Protect & PAGE_GUARD) == 0 &&
			(region.Protect & 0xFF) != PAGE_NOACCESS && (region.Protect & 0xFF) != 0 &&
			address >= begin && address - begin < region.RegionSize &&
			length <= region.RegionSize - (address - begin);
	}

	void catalog_exit_read_memory(void* caller, catalog_exit_memory& out)
	{
		out.status = "exception";
		__try
		{
			out.module = GetModuleHandleW(L"BlackOps3_UnrankedDedicatedServer.exe");
			if (!out.module) { out.error = GetLastError(); out.status = "module_missing"; return; }
			if (reinterpret_cast<uintptr_t>(out.module) != 0x140000000ULL) { out.status = "module_mismatch"; return; }
			const auto address = reinterpret_cast<uintptr_t>(caller);
			if (address < 0x140000040ULL) { out.status = "address_invalid"; return; }
			out.start = address - 0x40;
			if (VirtualQuery(reinterpret_cast<void*>(out.start), &out.region, sizeof(out.region)) != sizeof(out.region))
			{ out.error = GetLastError(); out.status = "query_failed"; return; }
			if (out.region.AllocationBase != out.module) { out.status = "module_mismatch"; return; }
			if (!catalog_exit_readable(out.region, out.start, sizeof(out.bytes))) { out.status = "region_invalid"; return; }
			const auto ok = ReadProcessMemory(GetCurrentProcess(), reinterpret_cast<void*>(out.start), out.bytes, sizeof(out.bytes), &out.copied);
			if (!ok) out.error = GetLastError();
			if (out.copied > sizeof(out.bytes)) { out.copied = 0; out.error = ERROR_INVALID_DATA; out.status = "read_failed"; return; }
			out.status = ok && out.copied == sizeof(out.bytes) ? "ok" :
				(out.copied && out.copied < sizeof(out.bytes) ? "partial" : "read_failed");
		}
		__except (EXCEPTION_EXECUTE_HANDLER) { out.error = GetExceptionCode(); out.status = "exception"; }
	}

	__declspec(noinline) void catalog_exit_read_stack(catalog_exit_stack& out)
	{
		out.status = "exception";
		__try
		{
			out.count = RtlCaptureStackBackTrace(0, 8, out.frames, nullptr);
			if (out.count > 8) { out.count = 0; out.status = "invalid_count"; return; }
			out.status = out.count ? "ok" : "empty";
		}
		__except (EXCEPTION_EXECUTE_HANDLER) { out.count = 0; out.error = GetExceptionCode(); out.status = "exception"; }
	}

	void catalog_exit_read_function(void* caller, HMODULE module, catalog_exit_function& out)
	{
		out.status = "exception";
		__try
		{
			const auto address = reinterpret_cast<uintptr_t>(caller);
			if (reinterpret_cast<uintptr_t>(module) != 0x140000000ULL || address <= 0x140000000ULL)
			{ out.status = "module_mismatch"; return; }
			MEMORY_BASIC_INFORMATION region{};
			if (VirtualQuery(reinterpret_cast<void*>(address - 1), &region, sizeof(region)) != sizeof(region))
			{ out.error = GetLastError(); out.status = "query_failed"; return; }
			if (region.AllocationBase != module) { out.status = "module_mismatch"; return; }
			if (!catalog_exit_readable(region, address - 1, 1)) { out.status = "region_invalid"; return; }
			out.address = RtlLookupFunctionEntry(address - 1, &out.image, nullptr);
			if (!out.address) { out.status = "not_found"; return; }
			if (out.image != reinterpret_cast<uintptr_t>(module)) { out.status = "module_mismatch"; return; }
			if (VirtualQuery(out.address, &region, sizeof(region)) != sizeof(region))
			{ out.error = GetLastError(); out.status = "query_failed"; return; }
			if (!catalog_exit_readable(region, reinterpret_cast<uintptr_t>(out.address), sizeof(out.record)))
			{ out.status = "region_invalid"; return; }
			const auto ok = ReadProcessMemory(GetCurrentProcess(), out.address, &out.record, sizeof(out.record), &out.copied);
			if (!ok) out.error = GetLastError();
			if (out.copied > sizeof(out.record)) { out.copied = 0; out.error = ERROR_INVALID_DATA; }
			if (!ok || out.copied != sizeof(out.record))
			{ out.record = {}; out.status = out.copied && out.copied < sizeof(out.record) ? "partial" : "read_failed"; return; }
			const auto rva = address - 1 - out.image;
			out.status = out.record.BeginAddress <= rva && rva < out.record.EndAddress ? "ok" : "record_invalid";
		}
		__except (EXCEPTION_EXECUTE_HANDLER) { out.record = {}; out.error = GetExceptionCode(); out.status = "exception"; }
	}

	void catalog_exit_once(const int code, void* caller)
	{
		if (!catalog_trace_enabled || (InterlockedOr(&catalog_trace_seen, 64) & 64)) return;
		const DWORD saved_error = GetLastError();
		const DWORD tid = GetCurrentThreadId();
		catalog_trace_once(32, "exit_hook", code, caller);
		catalog_exit_memory memory{};
		catalog_exit_stack stack{};
		catalog_exit_function function{};
		catalog_exit_read_memory(caller, memory);
		// Keep serialization bounded even after a partially completed guarded API.
		if (memory.copied > 256) { memory.copied = 0; memory.status = "read_failed"; memory.error = ERROR_INVALID_DATA; }
		constexpr char hex[] = "0123456789ABCDEF";
		char data[513] = "-";
		if (memory.copied)
		{
			for (SIZE_T i = 0; i < memory.copied; ++i)
			{ data[2 * i] = hex[memory.bytes[i] >> 4]; data[2 * i + 1] = hex[memory.bytes[i] & 15]; }
			data[2 * memory.copied] = '\0';
		}
		std::fprintf(stderr, "[T7_CATALOG_EXIT] schema=iw7.t7-catalog-exit-context/1 kind=memory code=%d tid=%lu ra=%p status=%s start=%p requested=256 read=%zu module=%p allocation=%p region=%p region_size=%llu state=%lu protect=%lu type=%lu error=%lu data=%s\n",
			code, tid, caller, memory.status, reinterpret_cast<void*>(memory.start), memory.copied, static_cast<void*>(memory.module),
			memory.region.AllocationBase, memory.region.BaseAddress, static_cast<unsigned long long>(memory.region.RegionSize),
			memory.region.State, memory.region.Protect, memory.region.Type, memory.error, data);
		std::fflush(stderr);
		catalog_exit_read_stack(stack);
		if (stack.count > 8) { stack.count = 0; stack.status = "invalid_count"; }
		char frames[137] = "-";
		if (stack.count)
		{
			for (USHORT i = 0; i < stack.count; ++i)
			{
				const auto value = reinterpret_cast<uintptr_t>(stack.frames[i]);
				for (unsigned j = 0; j < 16; ++j) frames[i * 17 + j] = hex[(value >> ((15 - j) * 4)) & 15];
				frames[i * 17 + 16] = ',';
			}
			frames[stack.count * 17 - 1] = '\0';
		}
		std::fprintf(stderr, "[T7_CATALOG_EXIT] schema=iw7.t7-catalog-exit-context/1 kind=stack code=%d tid=%lu ra=%p status=%s count=%u error=%lu addresses=%s\n",
			code, tid, caller, stack.status, static_cast<unsigned>(stack.count), stack.error, frames);
		std::fflush(stderr);
		catalog_exit_read_function(caller, memory.module, function);
		if (function.copied > 12) { function.copied = 0; function.record = {}; function.status = "record_invalid"; }
		std::fprintf(stderr, "[T7_CATALOG_EXIT] schema=iw7.t7-catalog-exit-context/1 kind=function code=%d tid=%lu ra=%p status=%s image=%p record=%p read=%zu begin=%08lX end=%08lX unwind=%08lX error=%lu\n",
			code, tid, caller, function.status, reinterpret_cast<void*>(function.image), static_cast<void*>(function.address),
			function.copied, function.record.BeginAddress, function.record.EndAddress, function.record.UnwindData, function.error);
		std::fflush(stderr);
		SetLastError(saved_error);
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


def wire_exit_main(source):
    """Keep /1 markers and add a separate, once-only context before cleanup."""
    source = wire_main(source)
    source = prepare_cli.helper.once(source, SUPPORT, SUPPORT+'\n'+EXIT_SUPPORT)
    return prepare_cli.helper.once(source, '\t\tcatalog_trace_once(32, "exit_hook", code, _ReturnAddress());',
                                   '\t\tcatalog_exit_once(code, _ReturnAddress());')


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
