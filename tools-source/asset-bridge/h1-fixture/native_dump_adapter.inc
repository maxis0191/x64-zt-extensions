// Fixture-only string bridge. This is NOT an IW7 engine script-string table.
// The token stays zero; the text is retrieved from the real H1 parser's table.
namespace h1_dump_fixture {
static zonetool::h1::xmodel* parser = nullptr;
static zonetool::h1::scr_string_t* source_token = nullptr;
static unsigned int string_calls = 0;
}
namespace zonetool::iw7 {
class xmodel { public: static void dump(XModel*); };
class xsurface { public: static void dump(XModelSurfs*); };
static const char* SL_ConvertToString(scr_string_t token)
{
    using namespace h1_dump_fixture;
    check(parser && source_token && token == 0 && *source_token == 0 && string_calls == 0,
          "fixture string bridge refuses unknown/repeated/unresolved token context");
    const char* text = parser->get_script_string(source_token);
    check(text && std::strcmp(text, "tag_origin") == 0, "H1 parser string table identity changed");
    ++string_calls;
    return text;
}
}
#define ZONETOOL_ERROR(...) ZONETOOL_INFO(__VA_ARGS__)
#include "zonetool/iw7/common/havok.hpp"
#include "production_dumps.inc"

// Hold new output directories against rename/deletion while the exact production
// filesystem writes. No input directory becomes a dump destination. Production
// wb IO is retained; this is fresh-directory isolation, not adversarial file IO.
class DumpDirectories
{
    std::vector<HANDLE> handles_;
public:
    explicit DumpDirectories(const std::filesystem::path& stage)
    {
        check_plain_ancestry(stage);
        try {
            for (const char* relative : {"dump", "dump/h1_original", "dump/h1_original/xmodel",
                                         "dump/h1_original/xsurface"}) {
                const auto path = stage / relative;
                check(CreateDirectoryW(path.c_str(), nullptr) != 0, "fresh dump directory required");
                const auto handle = CreateFileW(path.c_str(), FILE_READ_ATTRIBUTES,
                    FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_EXISTING,
                    FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
                check(handle != INVALID_HANDLE_VALUE, "cannot retain dump directory identity");
                handles_.push_back(handle);
                BY_HANDLE_FILE_INFORMATION info{};
                check(GetFileInformationByHandle(handle, &info) &&
                      (info.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) &&
                      !(info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT), "plain dump directory required");
            }
        } catch (...) { for (auto h : handles_) CloseHandle(h); throw; }
    }
    DumpDirectories(const DumpDirectories&) = delete;
    DumpDirectories& operator=(const DumpDirectories&) = delete;
    ~DumpDirectories() { for (auto h : handles_) CloseHandle(h); }
};

static void dump_original(zonetool::h1::xmodel& parser, zonetool::h1::XModel* source,
                          zonetool::iw7::XModel* model, zonetool::iw7::XModelSurfs* group)
{
    static_assert(offsetof(zonetool::iw7::XModel, noScalePartBits) == 120);
    static_assert(offsetof(zonetool::iw7::XModel, boneNames) == 152);
    static_assert(offsetof(zonetool::iw7::XModel, materialHandles) == 216);
    static_assert(offsetof(zonetool::iw7::XModel, boneInfo) == 616);
    static_assert(offsetof(zonetool::iw7::XModel, unknownIndex) == 704);
    static_assert(offsetof(zonetool::iw7::XModel, unknownIndex2) == 720);
    static_assert(offsetof(zonetool::iw7::XSurface, rigidVertLists) == 72);
    static_assert(offsetof(zonetool::iw7::XSurface, partBits) == 224);
    check(model->boneNames == source->boneNames && source->boneNames[0] == 0,
          "dump requires original unresolved bone token alias");
    check(!model->physicsLODData && !model->physicsLODDataSize && !model->physicsLODDataNameCount &&
          !model->numAimAssistBones && !model->unknown03Count && !model->unknownVec3Count &&
          !model->unknown04Count, "dump profile refuses optional physics/bones/streams");
    const auto stage = std::filesystem::current_path();
    check(stage.filename() == "probe", "dump requires dedicated probe stage directory");
    DumpDirectories directories(stage);
    zonetool::filesystem::set_fastfile("h1_original");
    h1_dump_fixture::parser = &parser;
    h1_dump_fixture::source_token = &source->boneNames[0];
    try {
        zonetool::iw7::xmodel::dump(model);
        zonetool::iw7::xsurface::dump(group);
    } catch (...) {
        h1_dump_fixture::parser = nullptr; h1_dump_fixture::source_token = nullptr; throw;
    }
    h1_dump_fixture::parser = nullptr; h1_dump_fixture::source_token = nullptr;
    check(h1_dump_fixture::string_calls == 1 && source->boneNames[0] == 0 && model->boneNames[0] == 0,
          "dump changed token or bypassed fixture string bridge");
    const auto output = stage / "dump/h1_original";
    unsigned int files = 0;
    for (const auto& entry : std::filesystem::recursive_directory_iterator(output)) {
        check(!(GetFileAttributesW(entry.path().c_str()) & FILE_ATTRIBUTE_REPARSE_POINT), "dump reparse refused");
        if (entry.is_directory()) continue;
        const auto relative = entry.path().lexically_relative(output).generic_string();
        check(relative == "xmodel/paris_h1_original_cube.xmb" ||
              relative == "xsurface/paris_h1_original_cube_lod0.xsb", "unexpected dump dependency output");
        check(entry.is_regular_file() && entry.file_size() > 0 && entry.file_size() <= 65536,
              "missing or oversized dump output");
        ++files;
    }
    check(files == 2, "both exact IW7 dump outputs required");
}
