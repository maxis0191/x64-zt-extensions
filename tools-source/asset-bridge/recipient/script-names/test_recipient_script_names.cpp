// Prepared pure native harness. NOT compiled/executed during source-only work.
#include "recipient_script_names.hpp"
#include <functional>
#include <iostream>

namespace rn = recipient_script_names;
int checks = 0;
void check(bool value) { if (!value) throw std::runtime_error("fixture failed"); ++checks; }
void refuses(const std::function<void()>& action)
{
    bool refused = false;
    try { action(); } catch (const std::runtime_error&) { refused = true; }
    check(refused);
}
rn::metadata meta(const char* name) { return {name, name, 3, 20, 5, false}; }
void missing(rn::observation& value)
{
    for (std::size_t i = 0; i < 2; ++i)
        value.direct(i, false, -1, nullptr, []() -> rn::metadata { throw std::runtime_error("unexpected metadata access"); });
}

int main()
{
    int first = 1, second = 2;
    rn::observation canonical;
    canonical.enumerate(&first, rn::keys[0], [] { return meta(rn::keys[0]); });
    canonical.direct(0, true, 49, &first, [] { return meta(rn::keys[0]); });
    canonical.direct(1, false, -1, nullptr, [] { return meta(rn::keys[1]); });
    check(canonical.json().find("\"matched\":1") != std::string::npos);

    rn::observation numeric;
    numeric.enumerate(&first, rn::keys[1], [] { return meta(rn::keys[1]); });
    numeric.direct(0, true, 49, &first, [] { return meta(rn::keys[1]); });
    numeric.direct(1, true, 49, &first, [] { return meta(rn::keys[1]); });
    check(numeric.json().find("\"decimal_names\":1") != std::string::npos);
    check(numeric.json().find("\"token_alias_inferred\":false") != std::string::npos);

    rn::observation distinct;
    distinct.enumerate(&first, rn::keys[0], [] { return meta(rn::keys[0]); });
    distinct.enumerate(&second, rn::keys[1], [] { return meta(rn::keys[1]); });
    missing(distinct);
    check(distinct.json().find("\"identity\":2") != std::string::npos);

    rn::observation duplicate;
    for (int i = 0; i < 2; ++i)
        duplicate.enumerate(&first, rn::keys[0], [] { return meta(rn::keys[0]); });
    missing(duplicate);
    check(duplicate.json().find("\"enum_occurrences\":2") != std::string::npos);
    refuses([&] { duplicate.enumerate(&second, rn::keys[0], [] { return meta(rn::keys[0]); }); });

    rn::observation empty;
    int factory_reads = 0;
    const auto forbidden = [&]() -> rn::metadata { ++factory_reads; throw std::runtime_error("unexpected metadata read"); };
    empty.enumerate(nullptr, nullptr, forbidden);
    empty.enumerate(&first, nullptr, forbidden);
    empty.enumerate(&first, "9999", forbidden);
    empty.enumerate(&first, "scripts/other/module", forbidden);
    missing(empty);
    check(factory_reads == 0);
    check(empty.json().find("\"callbacks\":4") != std::string::npos);
    check(empty.json().find("\"matched\":0") != std::string::npos);

    rn::observation bounded;
    for (std::size_t i = 0; i < rn::max_callbacks; ++i) bounded.enumerate(nullptr, nullptr, forbidden);
    refuses([&] { bounded.enumerate(&first, "9999", forbidden); });
    check(factory_reads == 0);
    const std::string long_name(241, 'x');
    refuses([&] { rn::bounded_name(long_name.c_str()); });
    check(rn::bounded_name(std::string(240, 'x').c_str()).size() == 240);
    refuses([] { rn::bounded_name(""); });
    refuses([] { rn::bounded_name("bad\nname"); });

    rn::observation invalid;
    refuses([&] { invalid.direct(0, true, 48, &first, forbidden); });
    refuses([&] { rn::observation x; x.direct(0, true, 49, nullptr, [] { return meta(rn::keys[0]); }); });
    refuses([&] { rn::observation x; x.enumerate(&first, rn::keys[0], [] { auto m=meta(rn::keys[0]);m.source_len=-1;return m; }); });
    refuses([&] { rn::observation x; x.enumerate(&first, rn::keys[0], [] { auto m=meta(rn::keys[0]);m.bytecode_len=rn::max_length+1;return m; }); });
    refuses([&] { rn::observation x; x.enumerate(&first, rn::keys[0], [] { return meta(rn::keys[1]); }); });
    refuses([&] { rn::observation x; x.json(); });
    refuses([&] { rn::observation x; missing(x); x.direct(0, false, -1, nullptr, forbidden); });
    check(canonical.json().size() <= rn::max_output);
    // Metadata contains no buffer/bytecode pointer; the mock factories cannot
    // supply payload storage. Real engine ABI and wrapper remain separate gates.
    std::cout << canonical.json();
    std::cout << "PURE_SCRIPT_NAME_CHECKS=" << checks << '\n';
    return 0;
}
