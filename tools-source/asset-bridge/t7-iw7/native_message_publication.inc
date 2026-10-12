	// One admitted capture; closing is terminal even if its writer finishes later.
	enum catalog_message_phase : LONG { message_idle, message_capturing, message_published, message_closing };
	enum catalog_message_publication : LONG
	{
		message_pending, message_written, message_format_failed, message_write_failed, message_short_write
	};
	enum catalog_message_closure : LONG
	{
		message_not_closed, message_close_pending, message_close_no_capture,
		message_close_published, message_close_publish_failed, message_close_incomplete
	};
	volatile LONG catalog_message_state = message_idle;
	volatile LONG catalog_message_publication_result = message_pending;
	volatile LONG catalog_message_close_result = message_not_closed;
	DWORD catalog_message_requested_bytes = 0;
	DWORD catalog_message_written_bytes = 0;
	DWORD catalog_message_publication_error = 0;
	constexpr DWORD catalog_message_close_budget_ms = 100;
	constexpr unsigned catalog_message_close_max_polls = 100;

	void catalog_message_complete(const LONG result)
	{
		// Full interlocked barrier publishes the write counts/error before result.
		InterlockedExchange(&catalog_message_publication_result, result);
		if (result == message_written)
			InterlockedCompareExchange(&catalog_message_state, message_published, message_capturing);
		// A failed capture retains its consumed claim. Never retry or reopen.
	}

	__declspec(noinline) void catalog_message_publish(const char* record, const int length)
	{
		if (length <= 0 || length >= 1024)
		{ catalog_message_complete(message_format_failed); return; }
		catalog_message_requested_bytes = static_cast<DWORD>(length);
		const auto sink = GetStdHandle(STD_ERROR_HANDLE);
		if (!sink || sink == INVALID_HANDLE_VALUE)
		{
			catalog_message_publication_error = ERROR_INVALID_HANDLE;
			catalog_message_complete(message_write_failed); return;
		}
		// One bounded record, no streaming printf or CRT FILE lock. This OS write
		// can still stall on a blocked sink; the CLI closer never joins this writer.
		const auto ok = WriteFile(sink, record, catalog_message_requested_bytes,
			&catalog_message_written_bytes, nullptr);
		if (!ok) catalog_message_publication_error = GetLastError();
		catalog_message_complete(!ok ? message_write_failed :
			(catalog_message_written_bytes == catalog_message_requested_bytes ? message_written : message_short_write));
	}

	__declspec(noinline) LONG catalog_message_close()
	{
		// Internal result only: no output, flush, stream lock, thread join or IO.
		// CLI invokes this once before its noreturn exit. Repeated callers remain
		// bounded too; they cannot reopen capture or overwrite a terminal result.
		const DWORD saved_error = GetLastError();
		const auto previous = InterlockedExchange(&catalog_message_state, message_closing);
		InterlockedCompareExchange(&catalog_message_close_result, message_close_pending, message_not_closed);
		LONG result = message_close_incomplete;
		if (previous == message_idle) result = message_close_no_capture;
		else
		{
			const auto start = GetTickCount64();
			for (unsigned poll = 0; poll < catalog_message_close_max_polls; ++poll)
			{
				const auto terminal = InterlockedCompareExchange(&catalog_message_close_result, 0, 0);
				if (terminal != message_close_pending) { result = terminal; break; }
				const auto publication = InterlockedCompareExchange(&catalog_message_publication_result, 0, 0);
				if (publication != message_pending)
				{
					result = publication == message_written ? message_close_published : message_close_publish_failed;
					break;
				}
				if (GetTickCount64() - start >= catalog_message_close_budget_ms) break;
				Sleep(1);
			}
		}
		InterlockedCompareExchange(&catalog_message_close_result, result, message_close_pending);
		result = InterlockedCompareExchange(&catalog_message_close_result, 0, 0);
		SetLastError(saved_error);
		return result;
	}

	__declspec(noinline) void catalog_message_observe(const uintptr_t buffer, const uintptr_t capacity, void* caller)
	{
		if (InterlockedCompareExchange(&catalog_message_ready, 0, 0) != 1 ||
			InterlockedCompareExchange(&catalog_message_state, message_capturing, message_idle) != message_idle) return;
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
		char record[1024]{};
		const auto formatted = std::snprintf(record, sizeof(record), "[T7_CATALOG_MSG] schema=iw7.t7-catalog-message/1 kind=buffer tid=%lu status=%s requested=%zu read=%zu length=%zu nul=%u error=%lu data=%s\n",
			GetCurrentThreadId(), out.status, out.requested, out.copied, length, nul, out.error, data);
		catalog_message_publish(record, formatted);
	}
