#pragma once
// Observe the existing incoming IMAGE event. Never link, look up or retain an asset.
#include "selected_image_incoming_capture.hpp"
#include <vector>
#include <string_view>

namespace zonetool::t7::incoming_image_event_observation
{
    namespace capture = registration_image_header_capture;
    namespace scalar = selected_image_header_metadata;
    inline constexpr char profile[] = "t7-incoming-image-header-observation-v1";
    inline constexpr char schema[] = "iw7.t7-incoming-image-header-observation/1";
    inline constexpr char option[] = "-t7-iw7-incoming-image-header-v1";
    inline constexpr char target[] = "$camo_base_normal";
    inline constexpr std::size_t target_length = sizeof(target)-1;
    inline constexpr unsigned callback_limit = 65536;
    inline constexpr unsigned case_count_limit = 16;
    inline constexpr std::size_t read_limit = 2u*1024u*1024u;
    static_assert(ASSET_TYPE_IMAGE == 9);
    static_assert(offsetof(GfxImage,streamedParts)==0 && sizeof(GfxStreamedPartInfo)==40);
    static_assert(offsetof(GfxImage,streamedPartCount)==160 && offsetof(GfxImage,mapType)==162);
    static_assert(offsetof(GfxImage,levelCount1)==191 && offsetof(GfxImage,width1)==192 && offsetof(GfxImage,height1)==194);
    static_assert(offsetof(GfxImage,width)==196 && offsetof(GfxImage,height)==198 && offsetof(GfxImage,depth)==200);
    static_assert(offsetof(GfxImage,levelCount)==208 && offsetof(GfxImage,streaming)==210);
    static_assert(offsetof(GfxImage,totalSize)==232 && offsetof(GfxImage,format)==240);

    // Called on the original post_unpack thread BEFORE arm/hook installation/ComInit.
    inline bool exact_selection(const std::vector<std::string>& args, bool requested)
    {
        if (!requested) return false;
        scalar::require(args.size() == 5 && !args[0].empty() && args[1] == option &&
            args[2] == "mp_freerun_04" && args[3] == "p7_fre_platform_cap_02" && args[4] == "0",
            "Exclusive exact incoming-image arguments required before bootstrap");
        return true;
    }

    // Calls are serialized by the EXISTING observer mutex. No flag parsing in callbacks.
    class collector
    {
        bool armed_{}, map_started_{}, finished_{}, refused_{}, cap_refused_{};
        unsigned callbacks_{}, nonmatches_{};
        std::size_t read_bytes_{};
        std::array<unsigned, 4> counts_{};
        std::array<nlohmann::ordered_json, 4> cases_{};
        std::array<char, 192> error_{};

        void fail(const char* why) noexcept
        {
            refused_ = true;
            if (!why) why = "Incoming event observation refused";
            unsigned i=0;
            for (; i<error_.size()-1 && why[i]; ++i) error_[i]=why[i];
            error_[i]=0;
        }
        template <typename Readable> void range(Readable& readable, const void* p, std::size_t n)
        {
            if (!n || n > read_limit-read_bytes_) cap_refused_=true;
            scalar::require(n && n <= read_limit-read_bytes_, "Incoming callback read budget exceeded");
            read_bytes_ += n;
            readable(p,n);
        }
        template <typename Readable, typename Copy> unsigned char byte(
            Readable& readable, Copy& copy, std::uintptr_t address)
        {
            const auto p=reinterpret_cast<const unsigned char*>(address);
            range(readable,p,1);
            unsigned char value{};
            if (!copy(&value,p,1)) throw std::runtime_error("Incoming name probe copy fault");
            return value;
        }
        template <typename Readable, typename Copy> std::optional<std::string> probe(
            const GfxImage* image, Readable& readable, Copy& copy)
        {
            const auto base=reinterpret_cast<std::uintptr_t>(image);
            scalar::require(base && offsetof(GfxImage,name)+sizeof(std::uintptr_t) <= UINTPTR_MAX-base,
                "Incoming name-field address overflow");
            std::uintptr_t address{};
            auto raw=reinterpret_cast<unsigned char*>(&address);
            for (std::size_t i=0;i<sizeof(address);++i)
                raw[i]=byte(readable,copy,base+offsetof(GfxImage,name)+i);
            scalar::require(address && target_length+2 <= UINTPTR_MAX-address, "Incoming name address overflow");
            std::string name;
            unsigned offset=0;
            auto first=byte(readable,copy,address);
            if (first == ',') { name+=','; offset=1; }
            for (std::size_t i=0;i<target_length;++i)
            {
                const auto c=(i==0 && offset==0) ? first : byte(readable,copy,address+offset+i);
                if (c != static_cast<unsigned char>(target[i])) return std::nullopt;
                name+=static_cast<char>(c);
            }
            if (byte(readable,copy,address+offset+target_length) != 0) return std::nullopt;
            return name; // Only these two exact ASCII names can reach publication.
        }

    public:
        bool arm(const std::vector<std::string>& args, bool requested)
        {
            // Invalid or mixed argv must throw before ANY state becomes armed.
            const bool selected=exact_selection(args,requested);
            if (!selected) return false;
            scalar::require(!armed_ && !finished_, "Incoming observer is single-use");
            armed_=true;
            return true;
        }
        void begin_map()
        {
            scalar::require(armed_ && !finished_ && !map_started_, "Original early incoming context required");
            map_started_=true;
        }
        template <typename Readable, typename Query, typename Copy>
        void observe(XAssetType type, XAssetHeader incoming, Readable readable, Query query, Copy copy) noexcept
        {
            if (!armed_ || finished_ || refused_ || type != ASSET_TYPE_IMAGE) return;
            try
            {
                if (++callbacks_ > callback_limit) cap_refused_=true;
                scalar::require(callbacks_ <= callback_limit, "Incoming IMAGE callback cap exceeded");
                const auto pointer=reinterpret_cast<const GfxImage*>(incoming.data);
                const auto raw_name=probe(pointer,readable,copy);
                if (!raw_name) { ++nonmatches_; return; }
                const bool reference=(*raw_name)[0] == ',';
                const unsigned slot=(map_started_ ? 2u : 0u)+(reference ? 0u : 1u);
                if (++counts_[slot] > case_count_limit) cap_refused_=true;
                scalar::require(counts_[slot] <= case_count_limit, "Exact incoming-name case cap exceeded");
                if (counts_[slot] != 1) return; // Count ambiguity; never overwrite/retry a sample.
                capture::cache sample;
                sample.reset();
                sample.record_incoming(pointer,*raw_name,
                    [&](const void* p,std::size_t n){range(readable,p,n);},query,copy);
                auto snapshot=sample.incoming_snapshot();
                cases_[slot]={{"phase",map_started_ ? "map_load" : "bootstrap"},
                    {"name_category",reference ? "reference" : "ordinary"},
                    {"callback_ordinal",callbacks_}, {"raw_name",*raw_name}, {"effective_name",target},
                    {"leading_comma_reference",reference}, {"snapshot",std::move(snapshot)}};
                if (cases_[slot].at("snapshot").at("refused") == true)
                    fail("Exact target incoming header/name copy refused");
            }
            catch (const std::exception& error) { fail(error.what()); }
            catch (...) { fail("Unknown incoming event refusal"); }
        }
        nlohmann::ordered_json finish(bool map_complete, bool lock_refused=false)
        {
            scalar::require(armed_ && !finished_, "Original incoming observation context required");
            if (lock_refused) fail("Existing observer lock acquisition failed");
            finished_=true;
            const unsigned references=counts_[0]+counts_[2], ordinary=counts_[1]+counts_[3];
            auto rows=nlohmann::ordered_json::array();
            for (unsigned i=0;i<cases_.size();++i)
            {
                auto row=cases_[i];
                if (row.is_null()) row={{"phase",i<2 ? "bootstrap" : "map_load"},
                    {"name_category",i%2==0 ? "reference" : "ordinary"},
                    {"callback_ordinal",nullptr},{"raw_name",nullptr},{"effective_name",nullptr},
                    {"leading_comma_reference",nullptr},{"snapshot",nullptr}};
                const bool observed=!row.at("snapshot").is_null() && row.at("snapshot").at("header_observed") == true;
                row["matching_events_in_phase"]=counts_[i];
                row["state"]=!counts_[i] ? "not_observed" : !observed ? "target_matched_sample_refused" :
                    counts_[i]>1 ? "repeated_target_ambiguous" : "first_complete_sample";
                row["single_event_observed_in_phase"]=counts_[i]==1;
                row["unique_in_phase"]=!refused_ && map_complete && map_started_ && observed && counts_[i]==1;
                row["repeated_headers_compared"]=false;
                row["conflict_absence_proven"]=false;
                unsigned nonzero=0;
                if (observed)
                {
                    const auto& image=row.at("snapshot").at("image");
                    for (const auto key : {"width","height","depth","width1","height1","level_count","level_count1",
                        "map_type","dxgi_format","total_size","flags","streaming","streamed_part_count"})
                        if (image.at(key).template get<std::uint64_t>() != 0) ++nonzero;
                }
                row["nonzero_descriptor_scalar_fields"]=observed ? nlohmann::ordered_json(nonzero) : nlohmann::ordered_json(nullptr);
                row["descriptor_admissible"]=false;
                rows.push_back(std::move(row));
            }
            nlohmann::ordered_json result={{"schema",schema},{"source_profile",profile},
                {"native_source_commit","fab935826c898806855376662a8a03317b3ad8f1"},
                {"target_name",target},{"zone","mp_freerun_04"},
                {"arm_phase","before_db_add_hook_create"},{"capture_phase","before_image_bypass"},
                {"name_comparison_rule","strip_one_leading_comma_then_exact_case_and_dollar"},
                {"arm_generation",1},{"exact_argv_validated_before_arm",true},
                {"bootstrap_complete",map_started_},{"map_complete",map_complete && map_started_},
                {"window_complete",!refused_ && map_complete && map_started_},{"cap_refused",cap_refused_},
                {"image_callbacks",callbacks_},{"non_target_callbacks",nonmatches_},{"callback_limit",callback_limit},
                {"target_case_limit_per_phase",case_count_limit},{"read_bytes",read_bytes_},{"read_limit",read_limit},
                {"reference_events",references},{"ordinary_name_events",ordinary},
                {"reference_name_observed",references!=0},{"ordinary_name_observed",ordinary!=0},
                {"ordinary_absence_scope",ordinary ? nlohmann::ordered_json(nullptr) : nlohmann::ordered_json(
                    refused_ || !map_complete ? "partial_or_refused_callback_window" : "not_observed_in_this_bounded_callback_window")},
                {"cases",std::move(rows)},{"refused",refused_ || !map_complete || !map_started_},
                {"reason",refused_ ? nlohmann::ordered_json(error_.data()) : !map_complete || !map_started_ ?
                    nlohmann::ordered_json("map_load_not_complete") : nlohmann::ordered_json(nullptr)},
                {"descriptor_admissible",false},{"qualified_object_mip_count",nullptr},
                {"source_asset_name_association_proven",false},{"model_binding_correlated",false},{"renderer_binding_proven",false},
                {"same_pointer_proven",false},{"same_object_proven",false},{"allocation_retained",false},
                {"atomic_snapshot_proven",false},{"runtime_abi_proven",false},{"lifetime_proven",false},
                {"pixels_copied",false},{"payload_bytes_read",0},{"ready",false}};
            scalar::require(result.dump().size() <= 32u*1024u,"Bounded incoming observation report required");
            return result;
        }
    };
}
