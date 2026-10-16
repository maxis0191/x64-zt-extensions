"""Pin-first in-memory checked allocator Source overlay; no invocation or I/O.

Legacy DEFAULT bytes are preserved. No consumer selects this overlay, and the
three pair hooks still reject. Authored C++ fixtures need separate admission.
"""
import hashlib

SOURCE_PIN = 'fab935826c898806855376662a8a03317b3ad8f1'
SOURCE_PATH = 'src/zonetool/zonetool/utils/memory.hpp'
SOURCE_BYTES = 3000
SOURCE_SHA256 = '9025b835313ee45ba3418e3322210dec3b6d334e504a1dd3b59e9f38e2898f35'

TYPES = r'''
	// Checked mode is opt-in Source only, not actual pair admission.
	enum class checked_memory_failure { none, allocation, overflow, capacity, not_live, copy, report_reuse };
	enum class checked_memory_release { not_attempted, succeeded, failed };
	struct checked_memory_tag final {};
	class checked_memory_error final : public std::exception
	{
		checked_memory_failure reason_;
	public:
		explicit checked_memory_error(checked_memory_failure reason) noexcept : reason_(reason) {}
		checked_memory_failure reason() const noexcept { return reason_; }
		const char* what() const noexcept override { return "Checked zone memory refused"; }
	};
	// The original owner's report must outlive the arena. No reset or authority.
	class checked_memory_report final
	{
		friend class zone_memory;
		bool bound_{};
		const void* owner_{};
		LPVOID original_pool_{};
		std::size_t capacity_{};
		checked_memory_failure primary_ = checked_memory_failure::none;
		DWORD primary_error_{};
		checked_memory_release release_ = checked_memory_release::not_attempted;
		unsigned release_attempts_{};
		bool release_result_available_{};
		BOOL release_result_{};
		DWORD release_error_{};
		bool cleanup_exception_{};
	public:
		checked_memory_report() = default;
		checked_memory_report(const checked_memory_report&) = delete;
		checked_memory_report& operator=(const checked_memory_report&) = delete;
		checked_memory_report(checked_memory_report&&) = delete;
		checked_memory_report& operator=(checked_memory_report&&) = delete;
		bool bound() const noexcept { return bound_; }
		const void* owner() const noexcept { return owner_; }
		LPVOID original_pool() const noexcept { return original_pool_; }
		std::size_t capacity() const noexcept { return capacity_; }
		checked_memory_failure primary() const noexcept { return primary_; }
		DWORD primary_error() const noexcept { return primary_error_; }
		checked_memory_release release() const noexcept { return release_; }
		unsigned release_attempts() const noexcept { return release_attempts_; }
		bool release_result_available() const noexcept { return release_result_available_; }
		BOOL release_result() const noexcept { return release_result_; }
		DWORD release_error() const noexcept { return release_error_; }
		bool cleanup_exception() const noexcept { return cleanup_exception_; }
	};
	// Ordinary arithmetic only. This helper does not validate an owner or pool.
	inline std::size_t checked_memory_bytes(std::size_t size, std::size_t count,
		std::size_t used, std::size_t capacity)
	{
		if (size && count > (std::numeric_limits<std::size_t>::max)() / size)
			throw checked_memory_error(checked_memory_failure::overflow);
		const auto bytes = size * count;
		if (used > capacity || bytes > capacity - used)
			throw checked_memory_error(checked_memory_failure::capacity);
		return bytes;
	}
'''

PRIVATE = r'''
		// These fields change class layout; no old object/CPP qualification carries.
		checked_memory_report* checked_report_{};
		enum class checked_phase { live, primary_failed, releasing, released, release_failed };
		checked_phase checked_phase_ = checked_phase::live;
		bool checked_release_attempted_{};
		static void checked_copy_source(const zone_memory& source)
		{
			// Mode is immutable; do not read/adopt the source pool first.
			if (source.checked_report_)
				throw checked_memory_error(checked_memory_failure::copy);
		}
		void checked_need_live() const
		{
			if (checked_phase_ != checked_phase::live)
				throw checked_memory_error(checked_memory_failure::not_live);
		}
		[[noreturn]] void checked_fail(checked_memory_failure reason, DWORD error = 0)
		{
			if (checked_report_->primary_ == checked_memory_failure::none)
			{
				checked_report_->primary_ = reason;
				checked_report_->primary_error_ = error;
			}
			checked_phase_ = checked_phase::primary_failed;
			throw checked_memory_error(reason);
		}
		template<class T> T* checked_allocate(std::size_t size, std::size_t count)
		{
			checked_need_live();
			if (count == 0) return nullptr;
			std::size_t bytes;
			try { bytes = checked_memory_bytes(size, count, mem_pos_, memory_size_); }
			catch (const checked_memory_error& error) { checked_fail(error.reason()); }
			auto pointer = reinterpret_cast<char*>(memory_pool_) + mem_pos_;
			memset(pointer, 0, bytes);
			mem_pos_ += bytes;
			return reinterpret_cast<T*>(pointer);
		}
		void checked_release_pool() noexcept
		{
			try
			{
				std::lock_guard<std::recursive_mutex> g(mutex_);
				if (checked_release_attempted_ || checked_phase_ == checked_phase::released ||
					checked_phase_ == checked_phase::release_failed) return;
				// One decision for this original pool across free() and destructor.
				checked_release_attempted_ = true;
				checked_phase_ = checked_phase::releasing;
				checked_report_->release_attempts_ = 1;
				const BOOL result = VirtualFree(memory_pool_, 0, MEM_RELEASE);
				const DWORD error = result ? 0 : GetLastError();
				checked_report_->release_result_ = result;
				checked_report_->release_result_available_ = true;
				checked_report_->release_error_ = error;
				checked_report_->release_ = result ? checked_memory_release::succeeded : checked_memory_release::failed;
				checked_phase_ = result ? checked_phase::released : checked_phase::release_failed;
				// Keep the original pool identity, even on failure. Never retry/clear.
			}
			catch (...)
			{
				// Unexpected lock/API exception: no invented OS return/error and no
				// retry. The checked destructor must not replace a primary exception.
				if (checked_phase_ != checked_phase::released && checked_phase_ != checked_phase::release_failed)
				{
					checked_phase_ = checked_phase::release_failed;
					checked_report_->release_ = checked_memory_release::failed;
					checked_report_->cleanup_exception_ = true;
				}
			}
		}
'''

CONSTRUCTOR = r'''		zone_memory(checked_memory_tag, const std::size_t& size, checked_memory_report& report)
			: memory_pool_(nullptr), memory_size_(size), mem_pos_(0), checked_report_(&report)
		{
			if (report.bound_) throw checked_memory_error(checked_memory_failure::report_reuse);
			report.bound_ = true;
			report.owner_ = this;
			report.capacity_ = size;
			memory_pool_ = VirtualAlloc(nullptr, size, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
			if (!memory_pool_)
			{
				const DWORD error = GetLastError();
				checked_fail(checked_memory_failure::allocation, error);
			}
			report.original_pool_ = memory_pool_;
		}

'''


def replacements():
    """Only explicit checked branches alter the pinned legacy Source."""
    lock = '\t\t\tstd::lock_guard<std::recursive_mutex> g(this->mutex_);\n'
    result = [
        ('#include <mutex>\n', '#include <mutex>\n#include <cstddef>\n#include <exception>\n#include <limits>\n'),
        ('namespace zonetool\n{\n', 'namespace zonetool\n{\n' + TYPES),
        ('\t\tstd::recursive_mutex mutex_;\n', '\t\tstd::recursive_mutex mutex_;\n' + PRIVATE),
        ('memory_pool_(mem.memory_pool_)', 'memory_pool_((checked_copy_source(mem), mem.memory_pool_))'),
        ('\t\tzone_memory(const std::size_t& size)\n', CONSTRUCTOR + '\t\tzone_memory(const std::size_t& size)\n'),
        ('\t\tvoid free()\n\t\t{\n', '\t\tvoid free()\n\t\t{\n\t\t\tif (checked_report_) { checked_release_pool(); return; }\n'),
    ]
    for signature, checked in [
        ('\t\tvoid clear()\n', '\t\t\t\tchecked_need_live();\n\t\t\t\tmemset(memory_pool_, 0, memory_size_);\n\t\t\t\tmem_pos_ = 0;\n'),
        ('\t\tvoid print_statistics()\n', '\t\t\t\tchecked_need_live();\n\t\t\t\tprintf("ZoneTool memory statistics: used %ub of ram (%fmb).\\n", static_cast<unsigned int>(mem_pos_), static_cast<float>(mem_pos_) / 1024 / 1024);\n'),
    ]:
        anchor = signature + '\t\t{\n'
        body = '\t\t\tif (checked_report_)\n\t\t\t{\n\t\t\t\tstd::lock_guard<std::recursive_mutex> g(mutex_);\n' + checked + '\t\t\t\treturn;\n\t\t\t}\n'
        result.append((anchor, anchor + body))
    for signature in ('\t\tchar* duplicate_string(const char* name)\n', '\t\tchar* duplicate_string(const std::string& name)\n'):
        anchor = signature + '\t\t{\n' + lock
        result.append((anchor, anchor + '\t\t\tif (checked_report_) checked_need_live();\n'))
    anchor = '\t\tT* manual_allocate(std::size_t size, std::size_t count = 1)\n\t\t{\n' + lock
    result.append((anchor, anchor + '\t\t\tif (checked_report_) return checked_allocate<T>(size, count);\n'))
    return result


def render(source, *, stage_checked=False):
    if type(source) is not str or '\0' in source:
        raise ValueError('Bounded exact Source text required')
    try:
        raw = source.encode('utf-8', errors='strict')
    except UnicodeError as error:
        raise ValueError('Strict UTF-8 Source text required') from error
    if len(raw) > 65536 or len(raw) != SOURCE_BYTES or hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('Pinned memory Source drift')
    if type(stage_checked) is not bool:
        raise ValueError('Literal Source-only staging selection required')
    metadata = {'source_only': True, 'native_pin': SOURCE_PIN, 'source_path': SOURCE_PATH,
                'checked_overlay_staged': stage_checked, 'layout_changed': stage_checked,
                'actual_activation': False, 'allocator_closure_qualified': False,
                'legacy_fatal_covered': False, 'cpp_fixture_executed': False}
    if not stage_checked:
        return source, metadata
    result = source
    for anchor, replacement in replacements():
        if result.count(anchor) != 1:
            raise ValueError('Unique pinned checked-memory staging anchor required')
        result = result.replace(anchor, replacement, 1)
    metadata['staged_source_sha256'] = hashlib.sha256(result.encode('utf-8')).hexdigest()
    return result, metadata
