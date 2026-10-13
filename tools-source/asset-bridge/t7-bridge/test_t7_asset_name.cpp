// Portable boundary tests of the actual production helper, not a mirrored rule.
// Source prepared only; no compile or native execution is claimed.
#include "t7_asset_name.hpp"
#include <array>
#include <iostream>

int main()
{
    using zonetool::t7::resident_iw7::checked_asset_name;
    unsigned checks = 0;
    const std::array<std::string, 7> allowed{
        "prop_barrel", "props/barrel_lod0", "props\\barrel_lod0", "Prop.Mixed-Case_01",
        "props/barrel 01", "props/com10", std::string(255, 'a')};
    const std::array<std::string, 39> refused{
        "", "../escape", "../../../../escape", "props/../escape", "props\\..\\escape",
        "props/./escape", "./escape", "/absolute", "\\absolute", "//server/share",
        "\\\\server\\share", "C:/absolute", "C:relative", "props/name:ads", "props//name",
        "props\\\\name", "props/", "props\\", "name.", "name ", "props./name", "props /name",
        "CON", "nul.mesh", "props/Aux.xmb", "prn", "COM1", "lPt9.xsb", "props/conin$",
        "CONOUT$", "CLOCK$", "name?", "name*", "name\"", "name|", "name<", "name>",
        "CON .txt", "props/COM1 .xsb"};
    try
    {
        for (const auto& value : allowed)
        {
            if (checked_asset_name(value) != value) return 1;
            ++checks;
        }
        for (const auto& value : refused)
        {
            bool rejected = false;
            try { (void)checked_asset_name(value); }
            catch (const std::runtime_error&) { rejected = true; }
            if (!rejected) return 2;
            ++checks;
        }
        for (const auto& value : {std::string("a\0b", 3), std::string("a\nb"),
                                 std::string("a\x7f"), std::string("a\xff"), std::string(256, 'a')})
        {
            bool rejected = false;
            try { (void)checked_asset_name(value); }
            catch (const std::runtime_error&) { rejected = true; }
            if (!rejected) return 3;
            ++checks;
        }
    }
    catch (const std::exception& error)
    {
        std::cerr << error.what() << '\n';
        return 4;
    }
    std::cout << "T7_ASSET_NAME_CHECKS=" << checks << '\n';
    return 0;
}
