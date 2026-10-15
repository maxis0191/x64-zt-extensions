#pragma once
// Included inside zonetool::iw7, after the pinned native structs. No engine
// lookup, mutation, serializer or platform IO is performed by this validator.
namespace player_definition_readset
{
    using readable_fn = bool (*)(const void*, size_t, void*);
    using copy_fn = bool (*)(void*, const void*, size_t, void*);
    using script_name_fn = const char* (*)(scr_string_t, void*, bool*);

    struct Reader
    {
        static constexpr size_t byte_limit = 1024 * 1024;
        static constexpr size_t element_limit = 8192;
        static constexpr size_t dynamic_limit = 64;
        static constexpr size_t string_limit = 512;
        static constexpr size_t script_call_limit = 2048;
        static constexpr size_t json_limit = 2 * 1024 * 1024;
        static constexpr size_t allocation_limit = 16 * 1024 * 1024;
        readable_fn readable;
        copy_fn copy;
        script_name_fn script_name;
        void* context;
        size_t bytes = 0;
        size_t elements = 0;
        size_t script_calls = 0;
        size_t copied_text_bytes = 0;
        size_t json_bytes = 0;
        size_t allocation_bytes = 0;
        std::array<const char*, 2> native_string_matrices{};
        size_t matrix_count = 0;
        size_t flat_empty_string_arrays = 0;
        const char* refusal = nullptr;

        bool fail(const char* field) { if (!refusal) refusal = field; return false; }
        bool json_token(size_t payload, const char* field)
        {
            // Conservative allowance for fixed Source keys, punctuation and
            // dump(4) indentation. UTF-8 strings are charged at six bytes per
            // copied byte, including escaping, before either serializer runs.
            constexpr size_t overhead = 256;
            if (payload > json_limit - json_bytes || overhead > json_limit - json_bytes - payload) return fail(field);
            // Finite Source estimate for keys/values and vector/string growth;
            // this is not a measurement or cap of the runtime allocator.
            const auto allocation = overhead * 4 + payload * 2;
            if (allocation > allocation_limit - allocation_bytes) return fail(field);
            json_bytes += overhead + payload;
            allocation_bytes += allocation;
            return true;
        }
        bool span(const void* address, size_t size, const char* field)
        {
            if (!size) return true;
            const auto start = reinterpret_cast<std::uintptr_t>(address);
            if (!address || size > byte_limit - bytes || size > (std::numeric_limits<std::uintptr_t>::max)() - start ||
                !readable || !readable(address, size, context)) return fail(field);
            bytes += size;
            return true;
        }
        template<class T> bool object(const T* address, const char* field)
        {
            return span(address, sizeof(T), field);
        }
        template<class T> bool load(const T* address, T& result, const char* field)
        {
            static_assert(std::is_trivially_copyable_v<T>);
            if (!span(address, sizeof(T), field)) return false;
            return (copy && copy(&result, address, sizeof(T), context)) || fail(field);
        }
        template<class T> bool scalar(const T* address, const char* field)
        {
            if constexpr (std::is_array_v<T>)
            {
                if (!span(address, sizeof(T), field)) return false;
                for (size_t i = 0; i < std::extent_v<T>; ++i)
                    if (!scalar(&(*address)[i], field)) return false;
                return true;
            }
            else
            {
                static_assert(std::is_arithmetic_v<T> || std::is_enum_v<T>, "Finite scalar readset only");
                if (!json_token(64, field)) return false;
                if constexpr (std::is_same_v<std::remove_cv_t<T>, bool>)
                {
                    static_assert(sizeof(T) == 1);
                    std::uint8_t raw;
                    if (!load(reinterpret_cast<const std::uint8_t*>(address), raw, field)) return false;
                    return raw <= 1 || fail(field);
                }
                else if constexpr (std::is_floating_point_v<T>)
                {
                    T raw;
                    if (!load(address, raw, field)) return false;
                    return std::isfinite(raw) || fail(field);
                }
                else
                {
                    // Preserve integer/enum representation without interpreting
                    // or normalizing it, but require the guarded copy as well.
                    T raw;
                    if (!load(address, raw, field)) return false;
                }
                return true;
            }
        }
        template<class Count> bool count(Count value, size_t& result, const char* field)
        {
            static_assert(std::is_integral_v<Count>);
            if constexpr (std::is_signed_v<Count>) if (value < 0) return fail(field);
            if (static_cast<std::uint64_t>(value) > dynamic_limit) return fail(field);
            result = static_cast<size_t>(value);
            return true;
        }
        template<class T> bool array_span(const T* address, size_t count, const char* field, bool required = false)
        {
            if (count > dynamic_limit || count > element_limit - elements ||
                count > (std::numeric_limits<size_t>::max)() / sizeof(T)) return fail(field);
            if (!address) return !required || !count || fail(field);
            elements += count;
            return span(address, count * sizeof(T), field);
        }
        bool string(const char* value, const char* field, bool nullable = true)
        {
            if (!value) return (nullable && json_token(4, field)) || fail(field);
            std::array<unsigned char, string_limit> copied{};
            for (size_t i = 0; i < string_limit; ++i)
            {
                const auto start = reinterpret_cast<std::uintptr_t>(value);
                if (i > (std::numeric_limits<std::uintptr_t>::max)() - start) return fail(field);
                const auto* current = reinterpret_cast<const char*>(start + i);
                char byte;
                if (!load(current, byte, field)) return false;
                copied[i] = static_cast<unsigned char>(byte);
                if (byte == '\0')
                {
                    // Validate the bounded copy, never strlen/std::string of
                    // the engine pointer. This does not promise its lifetime
                    // for the later calls made by the unchanged serializers.
                    copied_text_bytes += i + 1;
                    if (!json_token(i * 6 + 2, field)) return false;
                    for (size_t pos = 0; pos < i;)
                    {
                        const auto lead = copied[pos++];
                        if (lead < 0x80) continue;
                        size_t continuation;
                        std::uint32_t code, minimum;
                        if (lead >= 0xC2 && lead <= 0xDF) { continuation = 1; code = lead & 0x1F; minimum = 0x80; }
                        else if (lead >= 0xE0 && lead <= 0xEF) { continuation = 2; code = lead & 0x0F; minimum = 0x800; }
                        else if (lead >= 0xF0 && lead <= 0xF4) { continuation = 3; code = lead & 7; minimum = 0x10000; }
                        else return fail(field);
                        if (continuation > i - pos) return fail(field);
                        for (size_t n = 0; n < continuation; ++n)
                        {
                            const auto next = copied[pos++];
                            if ((next & 0xC0) != 0x80) return fail(field);
                            code = (code << 6) | (next & 0x3F);
                        }
                        if (code < minimum || code > 0x10FFFF || (code >= 0xD800 && code <= 0xDFFF)) return fail(field);
                    }
                    return true;
                }
            }
            return fail(field);
        }
        template<class T> bool asset(const T* value, const char* field)
        {
            if (!value) return json_token(2, field);
            // Only the native name reference is observed; no dependency body
            // is serialized. The header span precedes the name dereference.
            if (!object(value, field)) return false;
            const char* name;
            return load(&value->name, name, field) && string(name, field, false);
        }
        bool script(scr_string_t value, const char* field)
        {
            if (!value) return json_token(2, field); // Native empty-string bypass, without a resolver call.
            // Negative IDs are conservatively refused here; no positive
            // numeric range is claimed to prove membership of the engine pool.
            if (value < 0 || !script_name || script_calls >= script_call_limit) return fail(field);
            ++script_calls;
            bool converted = false;
            const char* name = script_name(value, context, &converted);
            return (converted && string(name, field, false)) || fail(field);
        }
        template<class T> bool scalars(const T* values, size_t count, const char* field, bool required = false)
        {
            if (!array_span(values, count, field, required)) return false;
            if (values) for (size_t i = 0; i < count; ++i) if (!scalar(&values[i], field)) return false;
            return true;
        }
        template<class T> bool assets(T* const* values, size_t count, const char* field)
        {
            if (!array_span(values, count, field)) return false;
            if (values) for (size_t i = 0; i < count; ++i)
            {
                T* value;
                if (!load(&values[i], value, field) || !asset(value, field)) return false;
            }
            return true;
        }
        bool scripts(const scr_string_t* values, size_t count, const char* field)
        {
            if (!array_span(values, count, field)) return false;
            if (values) for (size_t i = 0; i < count; ++i)
            {
                scr_string_t value;
                if (!load(&values[i], value, field) || !script(value, field)) return false;
            }
            return true;
        }
        template<class T> bool fx(const T& value, const char* field)
        {
            decltype(value.u.fx) reference;
            return scalar(&value.type, field) && load(&value.u.fx, reference, field) && asset(reference, field);
        }
        template<class T> bool effects(const T* values, size_t count, const char* field)
        {
            if (!array_span(values, count, field)) return false;
            if (values) for (size_t i = 0; i < count; ++i) if (!fx(values[i], field)) return false;
            return true;
        }
        bool string_field(const char* const* address, const char* field)
        {
            const char* value;
            return load(address, value, field) && string(value, field);
        }
        template<class T> bool asset_field(T* const* address, const char* field)
        {
            T* value;
            return load(address, value, field) && asset(value, field);
        }
        bool script_field(const scr_string_t* address, const char* field)
        {
            scr_string_t value;
            return load(address, value, field) && script(value, field);
        }
        template<size_t N> bool exact_name(const char* const* address, const char (&expected)[N], const char* field)
        {
            static_assert(N <= string_limit);
            const char* value;
            if (!load(address, value, field) || !value) return fail(field);
            const auto start = reinterpret_cast<std::uintptr_t>(value);
            for (size_t i = 0; i < N; ++i)
            {
                char byte;
                if (i > (std::numeric_limits<std::uintptr_t>::max)() - start ||
                    !load(reinterpret_cast<const char*>(start + i), byte, field) || byte != expected[i]) return fail(field);
            }
            return true;
        }
        template<class T, size_t N> bool native_string_array(const T (*address)[N], size_t count, const char* field)
        {
            static_assert(std::is_same_v<std::remove_cv_t<T>, const char*>);
            static_assert(N > 0);
            if (count != N || count > dynamic_limit || !span(address, sizeof(*address), field)) return fail(field);
            bool any = false, all = true;
            const auto previous_json = json_bytes;
            const auto previous_bytes = bytes;
            const auto previous_allocation = allocation_bytes;
            for (size_t i = 0; i < N; ++i)
            {
                const char* value;
                if (!load(&(*address)[i], value, field)) return false;
                if (value) { any = true; if (!string(value, field, false)) return false; }
                else all = false;
            }
            // The pinned macro assigns the whole array on each nonnull slot.
            // A mixed null/non-null array is not silently repaired or passed to
            // an unqualified null C-string conversion. Preserve the serializer.
            if (any && !all) return fail(field);
            const auto cells = any ? N * N : N;
            if (cells > element_limit - elements) return fail(field);
            elements += cells;
            if (!any)
            {
                ++flat_empty_string_arrays;
                for (size_t i = 0; i < N; ++i) if (!json_token(2, field)) return false;
            }
            if (all)
            {
                const auto one_array = json_bytes - previous_json;
                const auto one_read = bytes - previous_bytes;
                const auto one_allocation = allocation_bytes - previous_allocation;
                if (N - 1 > (json_limit - json_bytes) / one_array ||
                    N - 1 > (byte_limit - bytes) / one_read ||
                    N - 1 > (allocation_limit - allocation_bytes) / one_allocation || matrix_count >= native_string_matrices.size()) return fail(field);
                json_bytes += (N - 1) * one_array; // Pinned macro repeats the whole native array.
                bytes += (N - 1) * one_read;
                allocation_bytes += (N - 1) * one_allocation;
                native_string_matrices[matrix_count++] = field;
            }
            return true;
        }
        template<class T, class Visit> bool pointer_array(T* const* address, size_t count,
            const char* field, Visit visit, bool required = false)
        {
            T* values;
            if (!json_token(8, field) || !load(address, values, field) || !array_span(values, count, field, required)) return false;
            if (values) for (size_t i = 0; i < count; ++i) if (!visit(&values[i])) return false;
            return true;
        }
        template<class T, size_t N, class Visit> bool inline_objects(const T (*address)[N], const char* field, Visit visit)
        {
            static_assert(N > 0 && N <= dynamic_limit);
            if (!array_span(*address, N, field, true)) return false;
            for (size_t i = 0; i < N; ++i) if (!visit(&(*address)[i])) return false;
            return true;
        }
        template<class T, class Count, class Visit> bool counted_array(T* const* address, const Count* count_address,
            const char* field, Visit visit, bool required = false)
        {
            Count raw;
            size_t size;
            return load(count_address, raw, field) && count(raw, size, field) &&
                pointer_array(address, size, field, visit, required);
        }
        template<class T> bool fixed_scalars(const T* address, size_t count, const char* field)
        {
            if constexpr (std::is_pointer_v<T>)
                return pointer_array(address, count, field, [&](const auto* value) { return scalar(value, field); }, true);
            else
            {
                static_assert(std::is_array_v<T>);
                if (count > std::extent_v<T> || !span(address, sizeof(T), field)) return fail(field);
                return scalars(*address, count, field, true);
            }
        }
    };
}
