// Reuse the frozen synthetic ranges/types, not a second engine observer.
#define main legacy_material_fixture_main
#include "selected_material_observation_fixture.cpp"
#undef main
#include "selected_material_parts_observation.hpp"

namespace parts = t7::selected_material_parts_observation;

namespace
{
    nlohmann::ordered_json observe_parts(fixture& f, unsigned index = 4,
        std::uint32_t expected_hash = 0xA0AB1041u)
    {
        f.model.name = f.model_name.c_str();
        f.material.name = f.material_name.c_str();
        f.image.name = f.image_name.c_str();
        f.technique.name = f.technique_name.c_str();
        const auto text = parts::observe_binding_parts(&f.model, f.model_name, 0, 0,
            [&](const void* pointer, std::size_t bytes) { f.readable(pointer, bytes); }, {index, expected_hash});
        check(text.size() <= observation::output_limit);
        return nlohmann::ordered_json::parse(text);
    }
}

int main()
{
    try
    {
        fixture good;
        good.seven_bindings();
        good.image.streamedPartCount = 4;
        const std::uint32_t packed = 0x12345678u;
        std::memcpy(&good.image.streamedParts[0].levelCountAndSize, &packed, sizeof(packed));
        good.image.streamedParts[0].width = 64;
        good.image.streamedParts[0].height = 32;
        good.image.streamedParts[0].xpakEntry.key = 0xfedcba9876543210ull;
        const std::array<std::uint64_t, 3> opaque = {
            0x8000000000000001ull, 0xffffffffffffffffull, 0x0123456789abcdefull};
        std::memcpy(reinterpret_cast<std::uint8_t*>(&good.image.streamedParts[0].xpakEntry) + 8,
            opaque.data(), sizeof(opaque));
        const auto result = observe_parts(good);
        const auto& image = result.at("textures")[4].at("image");
        const auto& part0 = image.at("streamed_parts")[0];
        check(result.at("schema") == "iw7.t7-selected-material-observation/3" &&
            result.at("image_selection").at("mode") == "exact_binding_stream_parts");
        check(image.at("stream_part_count_in_bounds") == true && image.at("streamed_parts").size() == 4 &&
            part0.at("index") == 0 && result.at("stream_parts_header_copies") == 2);
        check(part0.at("level_count_and_size_u32") == 0x12345678u && part0.at("level_count_raw") == 8 &&
            part0.at("pixel_size_raw") == 0x01234567u && part0.at("width") == 64 && part0.at("height") == 32);
        check(part0.at("xpak_key_hex") == "fedcba9876543210" &&
            part0.at("opaque_descriptor_words_hex") == nlohmann::ordered_json::array({
                "8000000000000001", "ffffffffffffffff", "0123456789abcdef"}));
        check(image.at("format_raw_u32") == 28 && image.at("format_raw_byte0") == 28 &&
            image.at("format_field_width_runtime_verified") == false &&
            part0.at("descriptor_field_semantics_verified") == false && part0.at("payload_bytes_read") == 0);
        check(good.image_reads == 2 && result.at("headers_rechecked") == true &&
            result.at("stream_parts_headers_rechecked") == true && result.at("pixels_copied") == false &&
            result.at("atomic_snapshot_proven") == false && result.at("allocation_retained") == false &&
            result.at("ready") == false && result.at("textures")[0].at("image_read_state") == "not_attempted");
        const auto legacy = good.observe_binding();
        check(legacy.at("schema") == "iw7.t7-selected-material-observation/2" &&
            !legacy.at("textures")[4].at("image").contains("streamed_parts"));

        fixture overcount;
        overcount.seven_bindings();
        overcount.image.streamedPartCount = 255;
        const auto over = observe_parts(overcount);
        check(over.at("textures")[4].at("image").at("streamed_part_count") == 255 &&
            over.at("textures")[4].at("image").at("stream_part_count_in_bounds") == false &&
            over.at("textures")[4].at("image").at("streamed_parts").size() == 4);

        fixture width;
        width.seven_bindings();
        const std::uint32_t format = 0xabcd004du;
        std::memcpy(&width.image.format, &format, sizeof(format));
        const auto raw = observe_parts(width);
        check(raw.at("textures")[4].at("image").at("format_raw_u32") == 0xabcd004du &&
            raw.at("textures")[4].at("image").at("format_raw_byte0") == 77 &&
            raw.at("textures")[4].at("image").at("resident_metadata_admitted") == false);

        for (unsigned refusal_case = 0; refusal_case < 4; ++refusal_case)
        {
            fixture denied;
            denied.seven_bindings();
            denied.deny_image = refusal_case == 0;
            denied.change_image_name = refusal_case == 1;
            const auto refused = observe_parts(denied, refusal_case == 2 ? 7u : 4u,
                refusal_case == 3 ? 0xA0AB1040u : 0xA0AB1041u);
            check(refused.at("refused") == true && refused.at("schema") == "iw7.t7-selected-material-observation/3" &&
                refused.at("failure_stage") == (refusal_case == 0 ? "image_header" :
                    refusal_case == 1 ? "image_name_recheck" : "texture_selection"));
            check(refused.at("failure_index") == (refusal_case == 2 ? 7 : 4) &&
                refused.at("headers_rechecked") == false && refused.at("stream_parts_headers_rechecked") == false &&
                refused.at("pixels_copied") == false && refused.at("allocation_retained") == false &&
                refused.at("ready") == false);
            check(refusal_case == 1 ? denied.image_reads == 2 : denied.image_reads == 0);
        }

        unsigned guard_calls = 0;
        auto readable = [&](const void*, std::size_t) { ++guard_calls; };
        parts::header_capture capture(readable);
        capture.range(&good.image, sizeof(good.image));
        capture.range(&good.image, sizeof(good.image));
        bool third_refused = false;
        try { capture.range(&good.image, sizeof(good.image)); }
        catch (const std::exception&) { third_refused = true; }
        check(third_refused && capture.ambiguous && capture.count == 2 && guard_calls == 2);

        parts::header_capture budget(readable);
        std::array<std::uint8_t, observation::read_limit> buffer{};
        budget.range(buffer.data(), buffer.size() - 2 * sizeof(good.image));
        budget.range(&good.image, sizeof(good.image));
        const auto calls_before = guard_calls;
        bool budget_refused = false;
        try { budget.range(&good.image, sizeof(good.image)); }
        catch (const std::exception&) { budget_refused = true; }
        check(budget_refused && budget.count == 1 && guard_calls == calls_before);

        parts::header_capture overflow(readable);
        bool overflow_refused = false;
        try { overflow.range(reinterpret_cast<const void*>(std::numeric_limits<std::uintptr_t>::max() - 1), 4); }
        catch (const std::exception&) { overflow_refused = true; }
        check(overflow_refused && overflow.count == 0 && guard_calls == calls_before);
        std::printf("PASS selected image stream parts fixture: %u checks; no pixels or engine calls.\n", checks);
        return 0;
    }
    catch (const std::exception& error) { std::fprintf(stderr, "%s\n", error.what()); return 1; }
}
