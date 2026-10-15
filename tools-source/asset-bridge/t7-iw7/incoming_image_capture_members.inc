// Added only to the new derived cache. The frozen registration cache stays byte-identical.
template <typename Readable, typename Query, typename Copy>
void record_incoming(const GfxImage* pointer, const std::string& expected_raw_name,
    Readable readable, Query query, Copy copy) noexcept
{
    try
    {
        scalar::require(!attempted_, "Incoming image sample is single-use");
        attempted_ = true;
        scalar::require(pointer && reinterpret_cast<std::uintptr_t>(pointer) % alignof(GfxImage) == 0,
            "Aligned incoming IMAGE source header required");
        base::reader<Readable> read(readable);
        alignas(GfxImage) std::array<std::uint8_t, span> first{}, second{};
        const auto one = [&](auto& target)
        {
            fresh_query(query, pointer);
            read.range(pointer, span);
            if (!copy(target.data(), pointer, span))
            { copy_fault_ = true; throw std::runtime_error("Incoming header copy fault"); }
            ++copies_;
            scalar::require(target[offsetof(GfxImage, delayLoadPixels)] <= 1,
                "Invalid incoming delayLoadPixels raw byte");
        };
        one(first);
        const auto first_name = owned_name(read, first, copy);
        one(second);
        const auto second_name = owned_name(read, second, copy);
        scalar::require(first == second && first_name == second_name && first_name == expected_raw_name,
            "Incoming header/name changed within callback");
        fresh_query(query, pointer);
        GfxImage copied{};
        std::memcpy(&copied, first.data(), span);
        // Association here is ONLY this callback header and its twice-owned exact name.
        // It is not the selected MODEL binding, renderer identity or a resolved asset.
        const scalar::admission gate{scalar::source_profile, span, true, true, true, true};
        auto dto = scalar::build(copied, gate, std::optional<std::string>{first_name});
        owned_ = first; name_ = first_name; image_ = std::move(dto); observed_ = true;
    }
    catch (const std::exception& error) { fail(error.what()); }
    catch (...) { fail("Unknown incoming image copy refusal"); }
}
nlohmann::ordered_json incoming_snapshot() const
{
    return {{"header_observed", observed_}, {"header_copies", copies_},
        {"completed_header_bytes", copy_fault_ ? nlohmann::ordered_json(nullptr) : nlohmann::ordered_json(copies_ * span)},
        {"header_rechecked", observed_}, {"name_rechecked", observed_},
        {"callback_header_name_rechecked", observed_}, {"copy_fault", copy_fault_},
        {"image", observed_ ? image_ : nlohmann::ordered_json(nullptr)},
        {"refused", !observed_}, {"reason", observed_ ? nlohmann::ordered_json(nullptr) : nlohmann::ordered_json(error_.data())}};
}
