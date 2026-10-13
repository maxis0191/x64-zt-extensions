// Original keyed clip through the real pinned ZoneTool XAnim dump body.
// Prepared only: no native build/output/runtime has been validated yet.
#define NOMINMAX
#include <Windows.h>
#include <io.h>
#include <fcntl.h>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cwchar>
#include <cmath>
#include <string>
#include <vector>
#include <utility>
#include <stdexcept>
#include <filesystem>
#include <iostream>
#include <type_traits>
#define assert_sizeof(T, N) static_assert(sizeof(T)==N)
#define assert_offsetof(T, M, N) static_assert(offsetof(T,M)==N)
#include "zonetool/iw7/structs.hpp"
#include "zonetool/utils/io/assetmanager.hpp"
#include "probe_native_abi.hpp"
#include "probe_clip.hpp"
static_assert(sizeof(original_probe::data_byte)==4 && sizeof(original_probe::data_short)==2);
static_assert(sizeof(original_probe::random_data_short)==32 && sizeof(original_probe::bone_counts)==10);

namespace fs = std::filesystem;
using namespace std::string_literals;
static fs::path output_root;
static bool close_failed{};
static size_t bytes_written{};
static constexpr auto asset_name = "paris_original_probe_bend";
static void require(bool ok, const char* message) { if(!ok) throw std::runtime_error(message); }
static void unlinked(const fs::path& path) {
    require(path.is_absolute(), "absolute output required");
    for(auto p=path; !p.empty(); p=p.parent_path()) {
        const auto attrs=GetFileAttributesW(p.c_str());
        require(attrs!=INVALID_FILE_ATTRIBUTES || GetLastError()==ERROR_FILE_NOT_FOUND || GetLastError()==ERROR_PATH_NOT_FOUND, "unreadable output ancestry");
        require(attrs==INVALID_FILE_ATTRIBUTES || !(attrs&FILE_ATTRIBUTE_REPARSE_POINT), "reparse output refused");
        if(p==p.parent_path()) break;
    }
}

// Restricted local IO adapter. The serialization implementation itself is the
// production dump method in generated probe_dump.inc plus assetmanager.hpp.
namespace zonetool::filesystem {
file::file()=default;
file::file(const std::string& path){initialize(path);}
file::file(const file& other){require(!other.fp,"copy of open file");initialize(other.filepath);}
file::file(file&& other) noexcept:fp(std::exchange(other.fp,nullptr)),filepath(std::move(other.filepath)){}
file& file::operator=(file&& other) noexcept {if(this!=&other){close();fp=std::exchange(other.fp,nullptr);filepath=std::move(other.filepath);}return *this;}
file& file::operator=(const file& other){require(!other.fp,"copy of open file");close();initialize(other.filepath);return *this;}
file::~file(){close();}
void file::initialize(const fs::path& path){require(!fp,"initialize open file");filepath=path;}
FILE* file::get_fp(){return fp;}
errno_t file::open(std::string mode,bool,bool) {
    require(mode=="wb" && !fp, "create-only writer");
    require(filepath==fs::path("xanim")/(std::string(asset_name)+".xab"), "unexpected output name");
    const auto target=output_root/filepath;unlinked(target);
    const auto handle=CreateFileW(target.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
    require(handle!=INVALID_HANDLE_VALUE,"fresh output file required");
    const int fd=_open_osfhandle(reinterpret_cast<intptr_t>(handle),_O_BINARY|_O_WRONLY);
    if(fd<0){CloseHandle(handle);throw std::runtime_error("file descriptor failed");}
    fp=_fdopen(fd,"wb");if(!fp){_close(fd);throw std::runtime_error("file stream failed");}
    return 0;
}
size_t file::write(const void* data,size_t size,size_t count) {
    require(fp && data && size && count && size<=65536 && count<=65536/size && bytes_written<=65536-size*count,"64 KiB native output budget");
    require(fwrite(data,size,count,fp)==count,"short write");bytes_written+=size*count;return count;
}
size_t file::write_string(const char* text){require(text && strlen(text)<=128,"bounded name");return write(text,1,strlen(text)+1);}
size_t file::write_string(const std::string& text){return write_string(text.c_str());}
int file::close(){if(!fp)return 0;const auto result=fclose(std::exchange(fp,nullptr));close_failed=close_failed || result!=0;return result;}
}
namespace zonetool::iw7 {
// Local identity table only for this original asset; no engine script VM.
static const char* SL_ConvertToString(scr_string_t id) {
    switch(static_cast<unsigned>(id)) {
    case 1:return "tag_origin";case 2:return "tag_probe";case 3:return "probe_contact";
    default:throw std::runtime_error("unknown original script string");
    }
}
}
#include "probe_dump.inc"

int wmain(int argc,wchar_t** argv) {
    try {
        require(argc==3,"usage: writer_probe.exe <fresh absolute output> <candidate frequency: 1>");
        wchar_t* end=nullptr;const auto frequency=std::wcstof(argv[2],&end);
        require(end && end!=argv[2] && *end==L'\0' && frequency==1.0f,"only the evidence-bound candidate frequency 1 is supported");
        output_root=fs::path(argv[1]);unlinked(output_root);
        require(!fs::exists(output_root) && fs::is_directory(output_root.parent_path()),"fresh output under existing parent required");
        require(fs::create_directory(output_root),"output create failed");unlinked(output_root);
        require(fs::create_directory(output_root/"xanim"),"xanim directory create failed");
        using namespace zonetool::iw7;
        XAnimParts asset{};
        scr_string_t names[]={static_cast<scr_string_t>(1),static_cast<scr_string_t>(2)};
        XAnimNotifyInfo note{};note.name=static_cast<scr_string_t>(3);note.time=0.5f;
        asset.name=asset_name;asset.names=names;
        asset.dataByte=original_probe::data_byte;asset.dataByteCount=4;
        asset.dataShort=original_probe::data_short;asset.dataShortCount=1;
        asset.randomDataShort=original_probe::random_data_short;asset.randomDataShortCount=16;
        asset.numframes=30;asset.framerate=30.0f;asset.frequency=frequency;asset.flags=ANIM_LOOP;
        std::memcpy(asset.boneCount,original_probe::bone_counts,10);
        asset.notify=&note;asset.notifyCount=1;
        xanim_parts::dump(&asset);
        require(!close_failed && bytes_written>136 && bytes_written<65536,"native output incomplete");
        std::cout << "Original probe serialized; native reader and runtime acceptance still required.\n";
        return 0;
    } catch(const std::exception& error){std::cerr<<error.what()<<"\n";return 2;}
}
