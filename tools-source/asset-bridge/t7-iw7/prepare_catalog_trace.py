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
CALLERS_NAME = 't7-catalog-callers'
CALLERS_SCHEMA = 'iw7.t7-catalog-callers/1'
MESSAGE_NAME = 't7-catalog-message'
MESSAGE_SCHEMA = 'iw7.t7-catalog-message/1'
BASE_PLAN_SHA = 'daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa'
BASE_RECEIPT_SHA = 'c609bc56523654d8bca4b855024a463393185aab8e19ed4eae94c1ff8f6a09c2'
SURFACE_COUNT_HEADER = 'prepared/t7_iw7_resident_model.hpp'
SURFACE_COUNT_OLD_PIN = (13444, '6d2da3d4f7c3d0686909dc488f3d176ee2dd250e8d43d9a3cd9bcfa701482777')
SURFACE_COUNT_NEW_PIN = (13545, '701e3d1eccb0e98ecccfd2012215aaf7eff8db7bd974b184e86648a138b6e3c3')

# Source-only v2 originated at 927e5ebab6bf864e78ffbc6d68bac7d767066a17.
# Adapter pin below includes the post-build-C surface96/work384 correction.
# C/D2 -> rendered source before the unchanged message/publication overlays.
MULTISURFACE_TRANSITIONS = {
    'prepared/main.cpp': (
        (12854, '40de5fda829cec32a5d75359f58e69c84db7d8ee54f198cf6befa2a6ebe6f86e'),
        (12944, 'ce4fdd46c2da6e777f1142a8b9cb4a7b9fb78715a14e146fcb73e7577bc68615')),
    'prepared/zonetool.cpp': (
        (35974, '106ccdb4aec584184132c309c117f778d504ca9e64e8a821d23bfecc83bc8635'),
        (62674, 'c080e69319ccff31fd8a25747210baeddc95269d6b416d18321ea272935ffff8')),
    SURFACE_COUNT_HEADER: (
        SURFACE_COUNT_OLD_PIN,
        (21290, '857d57b5f3c1c970f45e513e357215f3506e9c48b2daea4b4f62cb33e0d9bce4')),
}
MULTISURFACE_WIRED_PINS = {
    'prepared/main.cpp': (43038, '3ff489d38adfa4da640c5acd6a78b1600f312fbaef47d41b118fabd7dcd3fb84'),
    'prepared/zonetool.cpp': (62728, 'd9e25c2cdd8a422fdf5312ad3dc4596fb60482ee165e77f59bff1a30d436fe7f'),
    SURFACE_COUNT_HEADER: MULTISURFACE_TRANSITIONS[SURFACE_COUNT_HEADER][1],
}

# A distinct source transition set. The sealed E2/v2 table above remains exact.
SELECTED_STREAMED_TRANSITIONS = {
    'prepared/main.cpp': (MULTISURFACE_TRANSITIONS['prepared/main.cpp'][0],
        (13052, 'ca8875cf36bdf9a8c8e6142969eab95194d214d09c90064e202d68ff9302fcb3')),
    'prepared/zonetool.cpp': (MULTISURFACE_TRANSITIONS['prepared/zonetool.cpp'][0],
        (105327, '7b76fc52769de8648a3449fd94007ed6047f0963d97d06fdc88f90753442fd48')),
    SURFACE_COUNT_HEADER: MULTISURFACE_TRANSITIONS[SURFACE_COUNT_HEADER],
}
SELECTED_STREAMED_WIRED_PINS = {
    'prepared/main.cpp': (43146, 'e599c3e6945e2192443b8a3a3e274d5d36b133b41beb38d6d9234c669defca01'),
    'prepared/zonetool.cpp': (105381, '501570c6b69971052f32b8ebdf1dfc1318a73b55d251c1f2ab8655625d412afe'),
    SURFACE_COUNT_HEADER: SELECTED_STREAMED_TRANSITIONS[SURFACE_COUNT_HEADER][1],
}


def multisurface_payload_delta(name, raw, pin, *, wired=False, selected_streamed=False):
    """Only the three sealed transitions; no name-only or arbitrary TU bypass."""
    if type(wired) is not bool or type(selected_streamed) is not bool: return False
    transitions = SELECTED_STREAMED_TRANSITIONS if selected_streamed else MULTISURFACE_TRANSITIONS
    wired_pins = SELECTED_STREAMED_WIRED_PINS if selected_streamed else MULTISURFACE_WIRED_PINS
    if name not in transitions: return False
    old, new = transitions[name]
    if wired: new = wired_pins[name]
    return (isinstance(raw, bytes) and isinstance(pin, dict) and
            (pin.get('Bytes'), pin.get('SHA256')) == old and
            (len(raw), hashlib.sha256(raw).hexdigest()) == new)


def surface_count_header_delta(name, raw, pin):
    """Only the reviewed diagnostic; never a general changed-header allowance."""
    return (name == SURFACE_COUNT_HEADER and isinstance(raw, bytes) and isinstance(pin, dict) and
            (pin.get('Bytes'), pin.get('SHA256')) == SURFACE_COUNT_OLD_PIN and
            (len(raw), hashlib.sha256(raw).hexdigest()) == SURFACE_COUNT_NEW_PIN)

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


CALLERS_SUPPORT = r'''
	struct catalog_caller_context
	{
		const char* status;
		int frame;
		HMODULE module;
		DWORD64 image;
		PRUNTIME_FUNCTION address;
		RUNTIME_FUNCTION record;
		SIZE_T record_copied;
		uintptr_t start;
		SIZE_T requested;
		SIZE_T copied;
		const char* scope;
		MEMORY_BASIC_INFORMATION region;
		DWORD error;
		unsigned char bytes[512];
	};

	void catalog_caller_read(const uintptr_t target, const catalog_exit_stack& stack, catalog_caller_context& out)
	{
		out.status = "exception";
		out.frame = -1;
		out.scope = "none";
		__try
		{
			if (std::strcmp(stack.status, "ok") != 0 || stack.count == 0 || stack.count > 8)
			{ out.status = "stack_unavailable"; return; }
			for (USHORT i = 0; i < stack.count; ++i)
			{
				if (reinterpret_cast<uintptr_t>(stack.frames[i]) == target) { out.frame = i; break; }
			}
			if (out.frame < 0) { out.status = "absent"; return; }
			out.module = GetModuleHandleW(L"BlackOps3_UnrankedDedicatedServer.exe");
			if (!out.module) { out.error = GetLastError(); out.status = "module_missing"; return; }
			if (reinterpret_cast<uintptr_t>(out.module) != 0x140000000ULL || target <= 0x140000000ULL)
			{ out.status = "module_mismatch"; return; }
			if (VirtualQuery(reinterpret_cast<void*>(target - 1), &out.region, sizeof(out.region)) != sizeof(out.region))
			{ out.error = GetLastError(); out.status = "query_failed"; return; }
			if (out.region.AllocationBase != out.module) { out.status = "module_mismatch"; return; }
			if (!catalog_exit_readable(out.region, target - 1, 1)) { out.status = "region_invalid"; return; }
			out.address = RtlLookupFunctionEntry(target - 1, &out.image, nullptr);
			if (!out.address) { out.status = "not_found"; return; }
			if (out.image != reinterpret_cast<uintptr_t>(out.module)) { out.status = "module_mismatch"; return; }
			MEMORY_BASIC_INFORMATION record_region{};
			if (VirtualQuery(out.address, &record_region, sizeof(record_region)) != sizeof(record_region))
			{ out.error = GetLastError(); out.status = "query_failed"; return; }
			if (record_region.AllocationBase != out.module) { out.status = "module_mismatch"; return; }
			if (!catalog_exit_readable(record_region, reinterpret_cast<uintptr_t>(out.address), sizeof(out.record)))
			{ out.status = "region_invalid"; return; }
			const auto record_ok = ReadProcessMemory(GetCurrentProcess(), out.address, &out.record, sizeof(out.record), &out.record_copied);
			if (!record_ok) out.error = GetLastError();
			if (out.record_copied > sizeof(out.record)) { out.record_copied = 0; out.error = ERROR_INVALID_DATA; }
			if (!record_ok || out.record_copied != sizeof(out.record))
			{
				out.record = {};
				out.status = out.record_copied && out.record_copied < sizeof(out.record) ? "record_partial" : "record_read_failed";
				return;
			}
			const auto rva = target - 1 - out.image;
			if (!(out.record.BeginAddress <= rva && rva < out.record.EndAddress))
			{ out.status = "record_invalid"; return; }
			const auto begin = static_cast<uintptr_t>(out.image + out.record.BeginAddress);
			const auto end = static_cast<uintptr_t>(out.image + out.record.EndAddress);
			const auto region_begin = reinterpret_cast<uintptr_t>(out.region.BaseAddress);
			if (out.region.RegionSize > ~uintptr_t(0) - region_begin || target > ~uintptr_t(0) - 64)
			{ out.status = "region_invalid"; return; }
			const auto region_end = region_begin + out.region.RegionSize;
			uintptr_t start = begin;
			uintptr_t stop = end;
			if (end - begin > sizeof(out.bytes) || !catalog_exit_readable(out.region, begin, end - begin))
			{
				start = target - 448;
				stop = target + 64;
				if (start < begin) start = begin;
				if (start < region_begin) start = region_begin;
				if (stop > end) stop = end;
				if (stop > region_end) stop = region_end;
			}
			if (!(start <= target - 1 && target - 1 < stop) || stop - start > sizeof(out.bytes) ||
				!catalog_exit_readable(out.region, start, stop - start))
			{ out.status = "region_invalid"; return; }
			out.start = start;
			out.requested = stop - start;
			out.scope = start == begin && stop == end ? "full" : "window";
			const auto ok = ReadProcessMemory(GetCurrentProcess(), reinterpret_cast<void*>(out.start), out.bytes, out.requested, &out.copied);
			if (!ok) out.error = GetLastError();
			if (out.copied > out.requested) { out.copied = 0; out.error = ERROR_INVALID_DATA; out.status = "read_failed"; return; }
			out.status = ok && out.copied == out.requested ? "ok" :
				(out.copied && out.copied < out.requested ? "partial" : "read_failed");
		}
		__except (EXCEPTION_EXECUTE_HANDLER) { out.record = {}; out.error = GetExceptionCode(); out.status = "exception"; }
	}

	void catalog_callers_capture(const int code, const DWORD tid, void* exit_caller, const catalog_exit_stack& stack)
	{
		constexpr uintptr_t targets[3] = {0x140584FD8ULL, 0x1401DA015ULL, 0x140526D02ULL};
		constexpr char hex[] = "0123456789ABCDEF";
		for (unsigned index = 0; index < 3; ++index)
		{
			catalog_caller_context out{};
			catalog_caller_read(targets[index], stack, out);
			// Guard serialization independently of a partially completed API/SEH path.
			if (out.record_copied > 12) { out.record_copied = 0; out.record = {}; out.status = "record_invalid"; }
			if (out.requested > 512 || out.copied > out.requested)
			{ out.requested = 0; out.copied = 0; out.start = 0; out.scope = "none"; out.status = "read_failed"; out.error = ERROR_INVALID_DATA; }
			char data[1025] = "-";
			if (out.copied)
			{
				for (SIZE_T i = 0; i < out.copied; ++i)
				{ data[2 * i] = hex[out.bytes[i] >> 4]; data[2 * i + 1] = hex[out.bytes[i] & 15]; }
				data[2 * out.copied] = '\0';
			}
			std::fprintf(stderr, "[T7_CATALOG_CALLER] schema=iw7.t7-catalog-callers/1 code=%d tid=%lu exit_ra=%p index=%u ra=%p status=%s frame=%d module=%p image=%p record=%p record_read=%zu begin=%08lX end=%08lX unwind=%08lX start=%p requested=%zu read=%zu scope=%s allocation=%p region=%p region_size=%llu state=%lu protect=%lu type=%lu error=%lu data=%s\n",
				code, tid, exit_caller, index, reinterpret_cast<void*>(targets[index]), out.status, out.frame, static_cast<void*>(out.module),
				reinterpret_cast<void*>(out.image), static_cast<void*>(out.address), out.record_copied,
				out.record.BeginAddress, out.record.EndAddress, out.record.UnwindData, reinterpret_cast<void*>(out.start),
				out.requested, out.copied, out.scope, out.region.AllocationBase, out.region.BaseAddress,
				static_cast<unsigned long long>(out.region.RegionSize), out.region.State, out.region.Protect, out.region.Type, out.error, data);
			std::fflush(stderr);
		}
	}
'''


MESSAGE_SUPPORT = r'''
	// The forwarding target is immutable and exists before the CALL can be patched.
	constexpr uintptr_t catalog_message_site = 0x140584F98ULL;
	constexpr uintptr_t catalog_message_target = 0x140AB6460ULL;
	volatile LONG catalog_message_install_seen = 0;
	volatile LONG catalog_message_ready = 0;
	volatile LONG catalog_message_seen = 0;
	static_assert(catalog_message_site % 8 == 0);

	struct catalog_message_buffer
	{
		const char* status;
		SIZE_T requested;
		SIZE_T copied;
		DWORD error;
		unsigned char bytes[384];
	};

	__declspec(noinline) void catalog_message_read(const uintptr_t buffer, const uintptr_t capacity, void* caller, catalog_message_buffer& out)
	{
		out.status = "exception";
		__try
		{
			if (!buffer || capacity != 0x1000 || reinterpret_cast<uintptr_t>(caller) != catalog_message_site + 5)
			{ out.status = "argument_invalid"; return; }
			ULONG_PTR low = 0, high = 0;
			GetCurrentThreadStackLimits(&low, &high);
			if (low >= high || buffer < low || buffer >= high || capacity > high - buffer)
			{ out.status = "stack_invalid"; return; }
			MEMORY_BASIC_INFORMATION region{};
			if (VirtualQuery(reinterpret_cast<void*>(buffer), &region, sizeof(region)) != sizeof(region))
			{ out.error = GetLastError(); out.status = "query_failed"; return; }
			if (!catalog_exit_readable(region, buffer, 1)) { out.status = "region_invalid"; return; }
			const auto remaining = region.RegionSize - (buffer - reinterpret_cast<uintptr_t>(region.BaseAddress));
			out.requested = remaining < sizeof(out.bytes) ? remaining : sizeof(out.bytes);
			const auto ok = ReadProcessMemory(GetCurrentProcess(), reinterpret_cast<void*>(buffer), out.bytes, out.requested, &out.copied);
			if (!ok) out.error = GetLastError();
			out.status = ok && out.copied == out.requested ? "complete" :
				(out.copied && out.copied < out.requested ? "partial" : "read_failed");
		}
		__except (EXCEPTION_EXECUTE_HANDLER) { out.error = GetExceptionCode(); out.status = "exception"; }
	}

	__declspec(noinline) void catalog_message_observe(const uintptr_t buffer, const uintptr_t capacity, void* caller)
	{
		if (InterlockedCompareExchange(&catalog_message_ready, 0, 0) != 1 ||
			(InterlockedOr(&catalog_message_seen, 1) & 1)) return;
		catalog_message_buffer out{};
		catalog_message_read(buffer, capacity, caller, out);
		if (out.requested > 384 || out.copied > out.requested)
		{ out.requested = 0; out.copied = 0; out.status = "read_failed"; out.error = ERROR_INVALID_DATA; }
		SIZE_T length = out.copied;
		unsigned nul = 0;
		for (SIZE_T i = 0; i < out.copied; ++i)
		{
			if (out.bytes[i] == 0) { length = i; nul = 1; break; }
		}
		if (std::strcmp(out.status, "complete") == 0) out.status = nul ? "ok" : "prefix";
		constexpr char hex[] = "0123456789ABCDEF";
		char data[769] = "-";
		if (length)
		{
			for (SIZE_T i = 0; i < length; ++i)
			{ data[2 * i] = hex[out.bytes[i] >> 4]; data[2 * i + 1] = hex[out.bytes[i] & 15]; }
			data[2 * length] = '\0';
		}
		std::fprintf(stderr, "[T7_CATALOG_MSG] schema=iw7.t7-catalog-message/1 kind=buffer tid=%lu status=%s requested=%zu read=%zu length=%zu nul=%u error=%lu data=%s\n",
			GetCurrentThreadId(), out.status, out.requested, out.copied, length, nul, out.error, data);
		std::fflush(stderr);
	}

	__declspec(noinline) uintptr_t catalog_message_forward(const uintptr_t buffer, const uintptr_t capacity,
		const uintptr_t format, const uintptr_t arguments)
	{
		// No diagnostic API or exception boundary may precede/wrap the original call.
		const auto result = reinterpret_cast<uintptr_t(*)(uintptr_t, uintptr_t, uintptr_t, uintptr_t)>(catalog_message_target)(
			buffer, capacity, format, arguments);
		const DWORD saved_error = GetLastError();
		catalog_message_observe(buffer, capacity, _ReturnAddress());
		SetLastError(saved_error);
		return result;
	}

	struct catalog_message_install
	{
		const char* status;
		DWORD error;
		unsigned char bytes[399];
		LONG64 original;
		LONG64 replacement;
		bool attempted;
	};

	__declspec(noinline) void catalog_message_prepare(catalog_message_install& out)
	{
		out.status = "exception";
		__try
		{
			const auto module = GetModuleHandleW(L"BlackOps3_UnrankedDedicatedServer.exe");
			if (!module) { out.error = GetLastError(); out.status = "module_missing"; return; }
			if (reinterpret_cast<uintptr_t>(module) != 0x140000000ULL) { out.status = "module_mismatch"; return; }
			MEMORY_BASIC_INFORMATION region{};
			if (VirtualQuery(reinterpret_cast<void*>(0x140584F50ULL), &region, sizeof(region)) != sizeof(region))
			{ out.error = GetLastError(); out.status = "query_failed"; return; }
			if (region.AllocationBase != module) { out.status = "module_mismatch"; return; }
			if (region.Protect != PAGE_EXECUTE_READWRITE || region.Type != MEM_IMAGE ||
				!catalog_exit_readable(region, 0x140584F50ULL, sizeof(out.bytes)))
			{ out.status = "region_invalid"; return; }
			SIZE_T copied = 0;
			const auto ok = ReadProcessMemory(GetCurrentProcess(), reinterpret_cast<void*>(0x140584F50ULL), out.bytes, sizeof(out.bytes), &copied);
			if (!ok || copied != sizeof(out.bytes))
			{ out.error = ok ? ERROR_INVALID_DATA : GetLastError(); out.status = "read_failed"; return; }
			int32_t displacement = 0;
			std::memcpy(&displacement, out.bytes + 73, sizeof(displacement));
			if (out.bytes[72] != 0xE8 || static_cast<int64_t>(catalog_message_site + 5) + displacement != static_cast<int64_t>(catalog_message_target))
			{ out.status = "call_mismatch"; return; }
			const auto relative = static_cast<int64_t>(reinterpret_cast<uintptr_t>(&catalog_message_forward)) -
				static_cast<int64_t>(catalog_message_site + 5);
			const auto relative32 = static_cast<int32_t>(relative);
			if (static_cast<int64_t>(relative32) != relative) { out.status = "wrapper_far"; return; }
			std::memcpy(&out.original, out.bytes + 72, sizeof(out.original));
			unsigned char patch[8]{};
			std::memcpy(patch, &out.original, sizeof(patch));
			std::memcpy(patch + 1, &relative32, sizeof(relative32));
			std::memcpy(&out.replacement, patch, sizeof(out.replacement));
			out.status = "prepared";
		}
		__except (EXCEPTION_EXECUTE_HANDLER) { out.error = GetExceptionCode(); out.status = "exception"; }
	}

	__declspec(noinline) void catalog_message_rollback(catalog_message_install& out)
	{
		__try
		{
			const auto previous = InterlockedCompareExchange64(reinterpret_cast<volatile LONG64*>(catalog_message_site), out.original, out.replacement);
			if (previous != out.replacement && previous != out.original)
			{ out.error = ERROR_INVALID_DATA; out.status = "rollback_failed"; return; }
			const auto flushed = FlushInstructionCache(GetCurrentProcess(), reinterpret_cast<void*>(catalog_message_site), sizeof(out.original));
			const DWORD flush_error = flushed ? 0 : GetLastError();
			LONG64 observed = 0;
			SIZE_T copied = 0;
			const auto read = ReadProcessMemory(GetCurrentProcess(), reinterpret_cast<void*>(catalog_message_site), &observed, sizeof(observed), &copied);
			if (!flushed || !read || copied != sizeof(observed) || observed != out.original)
			{
				out.error = !flushed ? flush_error : (!read ? GetLastError() : ERROR_INVALID_DATA);
				out.status = "rollback_failed"; return;
			}
			out.status = "rolled_back";
		}
		__except (EXCEPTION_EXECUTE_HANDLER) { out.error = GetExceptionCode(); out.status = "rollback_failed"; }
	}

	__declspec(noinline) void catalog_message_patch(catalog_message_install& out)
	{
		__try
		{
			out.attempted = true;
			const auto previous = InterlockedCompareExchange64(reinterpret_cast<volatile LONG64*>(catalog_message_site), out.replacement, out.original);
			if (previous != out.original) { out.attempted = false; out.status = "compare_mismatch"; return; }
			const auto flushed = FlushInstructionCache(GetCurrentProcess(), reinterpret_cast<void*>(catalog_message_site), sizeof(out.replacement));
			const DWORD flush_error = flushed ? 0 : GetLastError();
			LONG64 observed = 0;
			SIZE_T copied = 0;
			const auto read = ReadProcessMemory(GetCurrentProcess(), reinterpret_cast<void*>(catalog_message_site), &observed, sizeof(observed), &copied);
			if (!flushed || !read || copied != sizeof(observed) || observed != out.replacement)
			{
				out.error = !flushed ? flush_error : (!read ? GetLastError() : ERROR_INVALID_DATA);
				catalog_message_rollback(out); return;
			}
			out.status = "installed";
		}
		__except (EXCEPTION_EXECUTE_HANDLER)
		{
			out.error = GetExceptionCode(); out.status = "exception";
			if (out.attempted) catalog_message_rollback(out);
		}
	}

	void catalog_message_initialize()
	{
		if (!catalog_trace_enabled || (InterlockedOr(&catalog_message_install_seen, 1) & 1)) return;
		const DWORD saved_error = GetLastError();
		catalog_message_install out{};
		catalog_message_prepare(out);
		if (std::strcmp(out.status, "prepared") == 0)
		{
			try
			{
				if (utils::cryptography::sha256::compute(out.bytes, sizeof(out.bytes), true) !=
					"6E07CFFEB7E5F2DD6466DD4713537EDC5C93050CBEBC8A07892DB032931F038B")
					out.status = "signature_mismatch";
				else catalog_message_patch(out);
			}
			catch (...) { out.error = ERROR_UNHANDLED_EXCEPTION; out.status = "exception"; }
		}
		const auto printed = std::fprintf(stderr, "[T7_CATALOG_MSG] schema=iw7.t7-catalog-message/1 kind=install tid=%lu status=%s error=%lu\n",
			GetCurrentThreadId(), out.status, out.error);
		const auto flushed = std::fflush(stderr);
		// A concurrent call before publication only forwards; it never waits.
		if (printed >= 0 && flushed == 0 && std::strcmp(out.status, "installed") == 0)
			InterlockedExchange(&catalog_message_ready, 1);
		SetLastError(saved_error);
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


def wire_callers_main(source):
    """Add only the three E caller observations to the existing first winner."""
    source = wire_exit_main(source)
    source = prepare_cli.helper.once(source, '#include <cstdio>', '#include <cstdio>\n#include <cstring>')
    source = prepare_cli.helper.once(source, '\tvoid catalog_exit_once(', CALLERS_SUPPORT+'\n\tvoid catalog_exit_once(')
    return prepare_cli.helper.once(source, '\t\tSetLastError(saved_error);',
        '\t\tcatalog_callers_capture(code, tid, caller, stack);\n\t\tSetLastError(saved_error);')


def wire_message_main(source):
    """Observe one formatted buffer while preserving the original helper and exit."""
    source = wire_callers_main(source)
    source = prepare_cli.helper.once(source, '#include <cstring>',
        '#include <cstring>\n#include <utils/cryptography.hpp>')
    source = prepare_cli.helper.once(source, '\tvoid catalog_exit_once(', MESSAGE_SUPPORT+'\n\tvoid catalog_exit_once(')
    return prepare_cli.helper.once(source, '\t\t\tcatalog_trace_once(2, "before_post_unpack");',
        '\t\t\tcatalog_trace_once(2, "before_post_unpack");\n\t\t\tcatalog_message_initialize();')


def verify_base(plan_raw, receipt_raw, prior_raw, prior_receipt_raw, payloads, *, surface_count_diagnostic=False,
                resident_multisurface_v2=False, selected_streamed_static_v1=False):
    """Compare small text manifests only; never open retained binary inputs."""
    def require(ok, message):
        if not ok: raise ValueError(message)
    def key(path): return str(PureWindowsPath(path)).casefold()
    require(type(surface_count_diagnostic) is bool, 'Surface-count diagnostic flag must be boolean')
    require(type(resident_multisurface_v2) is bool and not (resident_multisurface_v2 and surface_count_diagnostic),
            'Multisurface v2 and diagnostic transitions are exclusive boolean choices')
    require(type(selected_streamed_static_v1) is bool and
            (not selected_streamed_static_v1 or resident_multisurface_v2), 'Explicit streamed base transition required')
    transitions = SELECTED_STREAMED_TRANSITIONS if selected_streamed_static_v1 else MULTISURFACE_TRANSITIONS
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
        if resident_multisurface_v2:
            require(all(multisurface_payload_delta(name, payloads.get(name),
                        bindings.get(key(root/name.removeprefix('prepared/'))), selected_streamed=selected_streamed_static_v1)
                        for name in transitions), 'Exact versioned multisurface transitions required')
        if surface_count_diagnostic:
            require(surface_count_header_delta(SURFACE_COUNT_HEADER, payloads.get(SURFACE_COUNT_HEADER),
                    bindings.get(key(root/SURFACE_COUNT_HEADER.removeprefix('prepared/')))),
                    'Exact surface-count diagnostic transition required')
        for name, raw in payloads.items():
            if not name.startswith('prepared/'): continue
            pin = bindings.get(key(root/name.removeprefix('prepared/')))
            if resident_multisurface_v2 and multisurface_payload_delta(name, raw, pin,
                    selected_streamed=selected_streamed_static_v1): continue
            if surface_count_diagnostic and surface_count_header_delta(name, raw, pin): continue
            require(pin and pin['Bytes'] == len(raw) and pin['SHA256'] == hashlib.sha256(raw).hexdigest(),
                    'Ordinary D2/C native source differs: '+name)
    inputs = {key(p['Path']):p for p in base['Inputs']}
    for stage in old_receipt['Stages'][:5]:
        for pin in stage.get('Artifacts', []):
            actual = inputs.get(key(pin['Path']))
            require(actual and actual['Bytes'] == pin['Bytes'] and actual['SHA256'] == pin['SHA256'],
                    'D2 retained object/helper proof differs')
