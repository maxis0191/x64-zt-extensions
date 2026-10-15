#pragma once
// Windows/MSVC leaf frames only. No RAII, JSON, allocation, broad handler or
// global engine hook. The standalone original H1 job remains the fault boundary
// for the later, unchanged public serializers and their repeated SL calls.
namespace player_definition_access
{
    using script_function = char* (*)(unsigned int);
    inline int av_filter(unsigned long code)
    {
        return code == EXCEPTION_ACCESS_VIOLATION ? EXCEPTION_EXECUTE_HANDLER : EXCEPTION_CONTINUE_SEARCH;
    }
    __declspec(noinline) inline bool copy(void* destination, const void* source, size_t bytes) noexcept
    {
        __try
        {
            std::memcpy(destination, source, bytes);
            return true;
        }
        __except (av_filter(GetExceptionCode()))
        {
            return false;
        }
    }
    __declspec(noinline) inline bool script(script_function function, unsigned int id, const char** result) noexcept
    {
        *result = nullptr;
        __try
        {
            *result = function(id);
            return *result != nullptr;
        }
        __except (av_filter(GetExceptionCode()))
        {
            *result = nullptr;
            return false;
        }
    }
}
