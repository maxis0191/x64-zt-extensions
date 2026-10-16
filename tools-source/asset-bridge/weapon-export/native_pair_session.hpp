#pragma once
// Inactive Source contracts and lifetime storage only. No native imports/I/O.
// A model event or successful cleanup report is never actual parse permission.
#include <array>
#include <cstdint>
#include <memory>
#include <optional>
#include <stdexcept>
#include <utility>

namespace player_pair_session
{
    [[noreturn]] inline void reject_native_activation()
    {
        throw std::logic_error("Native pair session inactive: schema bridge, FILE/route exclusion and fatal allocator closure are absent");
    }

    enum class Role { Weapon, Attachment };

    inline const char* relative_path(Role role)
    {
        switch (role)
        {
        case Role::Weapon: return "weapons\\sdk_shredder_clone_zm.json";
        case Role::Attachment: return "attachments\\sdk_shredder_clone_pap_zm.json";
        }
        throw std::logic_error("Unknown pair read role");
    }

    // Ordinary metadata. No real FILE/HANDLE acquisition or inspector is supplied.
    struct FileIdentity
    {
        std::uint64_t volume{};
        std::array<std::uint8_t, 16> id{};
        std::uint64_t bytes{};
        bool ordinary{};
    };

    struct ReadRequest
    {
        Role role;
        FileIdentity expected;
    };

    inline bool same_file(const FileIdentity& expected, const FileIdentity& actual)
    {
        return expected.ordinary && actual.ordinary && expected.bytes > 0 &&
            expected.bytes <= 2097152 && expected.volume == actual.volume &&
            expected.id == actual.id && expected.bytes == actual.bytes;
    }

    // Event-order model only. stream_cookie is NOT an OS identity. Native entry
    // hooks reject unconditionally, even if a caller fabricates every event.
    class FirstReadOrder final
    {
        enum class Phase { Fresh, Retained, Open, Checked, Sized, Read, Closed, Released, Failed };
        const ReadRequest request_;
        Phase phase_ = Phase::Fresh;
        std::uintptr_t stream_{};

        void need(bool condition)
        {
            if (!condition)
            {
                phase_ = Phase::Failed;
                throw std::logic_error("Invalid pair FILE/guard event order or identity");
            }
        }

    public:
        explicit FirstReadOrder(ReadRequest request) : request_(std::move(request))
        {
            relative_path(request_.role);
        }
        FirstReadOrder(const FirstReadOrder&) = delete;
        FirstReadOrder& operator=(const FirstReadOrder&) = delete;
        FirstReadOrder(FirstReadOrder&&) = delete;
        FirstReadOrder& operator=(FirstReadOrder&&) = delete;

        void guards_retained() { need(phase_ == Phase::Fresh); phase_ = Phase::Retained; }
        void opened(Role role, std::uintptr_t stream)
        {
            need(phase_ == Phase::Retained && role == request_.role && stream != 0);
            stream_ = stream;
            phase_ = Phase::Open;
        }
        void identity_checked(std::uintptr_t stream, const FileIdentity& actual)
        {
            need(phase_ == Phase::Open && stream == stream_ && same_file(request_.expected, actual));
            phase_ = Phase::Checked;
        }
        void before_size(std::uintptr_t stream)
        {
            need(phase_ == Phase::Checked && stream == stream_);
            phase_ = Phase::Sized;
        }
        void before_first_byte(std::uintptr_t stream)
        {
            need(phase_ == Phase::Sized && stream == stream_);
            phase_ = Phase::Read;
        }
        [[noreturn]] void checker_consumed_repositioned_or_closed()
        {
            phase_ = Phase::Failed;
            throw std::logic_error("Pair metadata checker must not read, seek, replace or close its stream");
        }
        void closed(std::uintptr_t stream)
        {
            need(stream_ != 0 && stream == stream_ && phase_ != Phase::Closed && phase_ != Phase::Released);
            stream_ = 0;
            phase_ = Phase::Closed;
        }
        void guards_released() { need(phase_ == Phase::Closed); phase_ = Phase::Released; }
    };

    // Cleanup outcome only, never a readiness/admission flag.
    class CleanupReport final
    {
        bool failed_ = false;
    public:
        void failed_restore() noexcept { failed_ = true; }
        bool cleanup_failed() const noexcept { return failed_; }
    };

    // Env is an owned fake in this lot. No real CWD/filesystem Env exists here.
    // Native mutable aliases/concurrency cannot be proved by this generic scope.
    template<class Env> class ScopedRoute final
    {
        Env& env_;
        CleanupReport& report_;
        typename Env::Snapshot saved_;
        void restore() noexcept
        {
            try { if (!env_.restore(saved_)) report_.failed_restore(); }
            catch (...) { report_.failed_restore(); }
        }
    public:
        ScopedRoute(Env& env, CleanupReport& report)
            : env_(env), report_(report), saved_(env.capture())
        {
            try { env_.enter(); }
            catch (...) { restore(); throw; }
        }
        ~ScopedRoute() noexcept { restore(); }
        ScopedRoute(const ScopedRoute&) = delete;
        ScopedRoute& operator=(const ScopedRoute&) = delete;
        ScopedRoute(ScopedRoute&&) = delete;
        ScopedRoute& operator=(ScopedRoute&&) = delete;
    };

    template<class W, class A> struct BorrowedRoots
    {
        const W* weapon;
        const A* attachment;
    };

    // One-shot ordinary lifetime storage, NOT a factory for admitted native
    // parsing. A native Factory/schema bridge is intentionally absent. All
    // factories authored here use fakes. No bool/token can enable native hooks.
    template<class Guards, class Raw, class Route, class Arena, class WeaponParser,
        class AttachmentParser, class W, class A, class Inventory>
    class OwnedPair final
    {
        // Reverse destruction: views/inventory -> parsers/maps -> arena ->
        // route -> immutable raw buffers -> original guards last.
        std::unique_ptr<Guards> guards_;
        std::unique_ptr<Raw> raw_;
        std::unique_ptr<Route> route_;
        std::unique_ptr<Arena> arena_;
        std::unique_ptr<WeaponParser> weapon_;
        std::unique_ptr<AttachmentParser> attachment_;
        std::optional<BorrowedRoots<W, A>> roots_;
        std::unique_ptr<Inventory> inventory_;

        template<class T> static std::unique_ptr<T> required(std::unique_ptr<T> value)
        {
            if (!value) throw std::logic_error("Missing pair lifetime component");
            return value;
        }
    public:
        template<class Factory> explicit OwnedPair(Factory& factory)
            : guards_(required(factory.guards())), raw_(required(factory.raw())),
              route_(required(factory.route())), arena_(required(factory.arena())),
              weapon_(required(factory.weapon())), attachment_(required(factory.attachment()))
        {
        }
        ~OwnedPair() noexcept
        {
            inventory_.reset();
            roots_.reset();
        }
        OwnedPair(const OwnedPair&) = delete;
        OwnedPair& operator=(const OwnedPair&) = delete;
        OwnedPair(OwnedPair&&) = delete;
        OwnedPair& operator=(OwnedPair&&) = delete;

        void retain_returned_roots(const W* weapon, const A* attachment)
        {
            if (roots_ || !weapon || !attachment) throw std::logic_error("Two fresh returned pair roots required");
            roots_.emplace(BorrowedRoots<W, A>{weapon, attachment});
        }
        const BorrowedRoots<W, A>& roots() const
        {
            if (!roots_) throw std::logic_error("Returned roots are absent");
            return *roots_;
        }
        void retain_copied_inventory(std::unique_ptr<Inventory> inventory)
        {
            if (!roots_ || inventory_) throw std::logic_error("One copied inventory after roots required");
            inventory_ = required(std::move(inventory));
        }
    };

    // Cleanup contracts above apply ONLY to normal return/status refusal and
    // exceptions that unwind. fab935 zone_memory VirtualAlloc failure calls
    // MessageBoxA/std::exit(0), bypassing this stack. That fatal branch is NOT
    // COVERED. Fake constructor throws and capacity/base checks do not qualify
    // it. No actual arena, route or parser activation is supplied by this lot.
}
