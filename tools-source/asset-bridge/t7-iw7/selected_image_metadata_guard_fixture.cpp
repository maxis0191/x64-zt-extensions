// Compile/run the reviewed mapper and the actual guarded G2 function before the CLI.
#define main selected_image_mapper_fixture_main
#include "selected_image_header_metadata_fixture.cpp"
#undef main
#include "selected_material_metadata_guarded.hpp"

namespace guard = zonetool::t7::selected_image_metadata_read_guard;
namespace material = zonetool::t7::selected_material_observation;
namespace
{
    unsigned guard_checks{};
    void guard_check(bool value)
    {
        ++guard_checks;
        if (!value) throw std::runtime_error("Selected metadata guard fixture failed");
    }
    void set_raw_delay(zonetool::t7::GfxImage& owned, unsigned char raw)
    {
        std::memcpy(reinterpret_cast<unsigned char*>(&owned) + 188, &raw, sizeof(raw));
    }
    void invalid_owned_refuses(const zonetool::t7::GfxImage& owned)
    {
        bool refused = false;
        try { (void)material::image_metadata(owned); }
        catch (const std::runtime_error& error)
        {
            refused = std::string_view(error.what()) == "Invalid selected owned delayLoadPixels representation";
        }
        guard_check(refused);
    }
}

int main()
{
    if (selected_image_mapper_fixture_main() != 0) return 1;
    try
    {
        guard_check(!guard::active);
        {
            const guard::scope outer;
            guard_check(guard::active);
            for (const unsigned char raw : std::array<unsigned char, 2>{0, 1})
            {
                zonetool::t7::GfxImage owned{}; set_raw_delay(owned, raw);
                guard_check(material::image_metadata(owned).at("delay_load_pixels") == (raw == 1));
            }
            for (const unsigned char raw : std::array<unsigned char, 2>{2, 0xff})
            {
                zonetool::t7::GfxImage owned{}; set_raw_delay(owned, raw);
                invalid_owned_refuses(owned);
            }
            {
                const guard::scope nested;
                guard_check(guard::active);
            }
            guard_check(guard::active);
            // Checking a different valid snapshot must not admit the consumed invalid one.
            zonetool::t7::GfxImage valid_snapshot{}; set_raw_delay(valid_snapshot, 0);
            zonetool::t7::GfxImage consumed_snapshot{}; set_raw_delay(consumed_snapshot, 2);
            guard::validate_if_active(valid_snapshot);
            invalid_owned_refuses(consumed_snapshot);
            // The same raw-byte check also precedes reader.one's typed return/copy.
            auto readable = [](const void*, std::size_t) {};
            material::reader<decltype(readable)> reader(readable);
            bool before_return = false;
            try { (void)reader.one(&consumed_snapshot); }
            catch (const std::runtime_error& error)
            {
                before_return = std::string_view(error.what()) == "Invalid selected owned delayLoadPixels representation";
            }
            guard_check(before_return);
        }
        guard_check(!guard::active);
        try
        {
            const guard::scope exceptional;
            throw std::runtime_error("Authored scope unwind");
        }
        catch (const std::runtime_error&) {}
        guard_check(!guard::active);
        zonetool::t7::GfxImage legacy_valid{}; set_raw_delay(legacy_valid, 0);
        guard_check(material::image_metadata(legacy_valid).at("delay_load_pixels") == false);
        if (guard_checks != 13) throw std::runtime_error("Exact selected metadata guard count required");
        std::printf("PASS selected metadata read guard fixture: %u checks; no engine.\n", guard_checks);
        return 0;
    }
    catch (const std::exception& error)
    {
        std::fprintf(stderr, "%s\n", error.what());
        return 1;
    }
}
