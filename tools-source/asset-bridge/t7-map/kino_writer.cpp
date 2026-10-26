// Generalized rigid static-mesh writer for IW7 (ZoneTool pin fab9358 serializers).
// Reads KMSH v1 files (one model each, N surfaces, one material per surface) and
// writes xmodel/<name>.xmb + xsurface/<name>_lod0.xsb using the exact assetmanager
// record order of zonetool::iw7::xmodel::dump / xsurface::dump. One root bone,
// one LOD, no physics. Derived from the model-lab original cube writer.
#define NOMINMAX
#include <Windows.h>
#include <io.h>
#include <fcntl.h>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cassert>
#include <cstring>
#include <cmath>
#include <string>
#include <vector>
#include <utility>
#include <stdexcept>
#include <filesystem>
#include <iostream>
#include <fstream>
#include <algorithm>
#define assert_sizeof(T, N) static_assert(sizeof(T)==N)
#define assert_offsetof(T, M, N) static_assert(offsetof(T,M)==N)
#include "zonetool/iw7/structs.hpp"
#include "zonetool/utils/io/assetmanager.hpp"

namespace fs = std::filesystem;
static fs::path output_root;
static void require(bool ok, const char* msg) { if (!ok) throw std::runtime_error(msg); }

namespace zonetool::filesystem {
file::file() = default;
file::file(const std::string& path) { initialize(path); }
file::file(const file& other) { require(!other.fp, "Open file cannot be copied"); initialize(other.filepath); }
file::file(file&& other) noexcept : fp(std::exchange(other.fp, nullptr)), filepath(std::move(other.filepath)) {}
file& file::operator=(file&& other) noexcept { if (this != &other) { close(); fp = std::exchange(other.fp, nullptr); filepath = std::move(other.filepath); } return *this; }
file& file::operator=(const file& other) { require(!other.fp, "Open file cannot be copied"); close(); initialize(other.filepath); return *this; }
file::~file() { close(); }
void file::initialize(const fs::path& path) { require(!fp, "Initialize opened file"); filepath = path; }
FILE* file::get_fp() { return fp; }
errno_t file::open(std::string mode, bool, bool) {
    const auto path = output_root / filepath;
    if (mode == "wb") {
        fs::create_directories(path.parent_path());
        require(!fs::exists(path), "Fresh output asset required");
        const auto error = _wfopen_s(&fp, path.c_str(), L"wb");
        require(!error && fp, "Writer open failed");
    } else {
        const auto error = _wfopen_s(&fp, path.c_str(), L"rb");
        require(!error && fp, "Reader open failed");
    }
    return 0;
}
size_t file::write(const void* data, size_t size, size_t count) { require(fp && fwrite(data, size, count, fp) == count, "Short write"); return count; }
size_t file::write_string(const char* str) { return write(str, 1, strlen(str) + 1); }
size_t file::write_string(const std::string& str) { return write_string(str.c_str()); }
size_t file::read(void* data, size_t size, size_t count) { require(fp && fread(data, size, count, fp) == count, "Truncated asset"); return count; }
size_t file::read_string(std::string* str) { str->clear(); for (size_t n = 0; n < 1024; n++) { char c; read(&c, 1, 1); if (!c) return n + 1; str->push_back(c); } throw std::runtime_error("Unbounded string refused"); }
int file::close() { if (!fp) return 0; return fclose(std::exchange(fp, nullptr)); }
}

using namespace zonetool;
using namespace zonetool::iw7;

static uint16_t to_half(float f) {
    uint32_t x; memcpy(&x, &f, 4);
    const uint32_t sign = (x >> 16) & 0x8000;
    int32_t exp = int32_t((x >> 23) & 0xFF) - 127 + 15;
    uint32_t mant = x & 0x7FFFFF;
    if (((x >> 23) & 0xFF) == 0xFF) return uint16_t(sign | 0x7C00 | (mant ? 0x200 : 0));
    if (exp >= 31) return uint16_t(sign | 0x7BFF);
    if (exp <= 0) {
        if (exp < -10) return uint16_t(sign);
        mant |= 0x800000;
        const uint32_t shift = uint32_t(14 - exp);
        uint32_t h = mant >> shift;
        if ((mant >> (shift - 1)) & 1) h++;
        return uint16_t(sign | h);
    }
    uint32_t h = sign | (uint32_t(exp) << 10) | (mant >> 13);
    if (mant & 0x1000) h++;
    return uint16_t(h);
}
// Same 10-10-10 candidate encoding as the model-lab writer (pinned H1 encoder).
static uint32_t pack_unit(const float* v) {
    uint32_t out = 0xC0000000u;
    for (unsigned i = 0; i < 3; i++) {
        const float c = std::clamp(v[i], -1.0f, 1.0f);
        out |= static_cast<uint32_t>(std::floor((c + 1) * 0.5f * 1023 + 0.5f)) << (10 * i);
    }
    return out;
}

struct InSurface { std::string material; std::vector<float> pos, uv; std::vector<uint32_t> nt, col; std::vector<uint16_t> idx; };
struct InModel { std::string name; std::vector<InSurface> surfs; };

template <typename T> static T rd(std::ifstream& in) { T v{}; in.read(reinterpret_cast<char*>(&v), sizeof(T)); require(bool(in), "Truncated KMSH"); return v; }
static std::string rdstr(std::ifstream& in) { const auto n = rd<uint16_t>(in); require(n > 0 && n < 256, "Bad KMSH string"); std::string s(n, '\0'); in.read(s.data(), n); require(bool(in), "Truncated KMSH string"); return s; }

static InModel load(const fs::path& p) {
    std::ifstream in(p, std::ios::binary);
    require(bool(in), "Open KMSH");
    require(rd<uint32_t>(in) == 0x48534D4B && rd<uint32_t>(in) == 2, "KMSH v2 required");
    InModel m; m.name = rdstr(in);
    const auto ns = rd<uint32_t>(in);
    require(ns >= 1 && ns <= 1024, "Surface count");
    for (uint32_t s = 0; s < ns; s++) {
        InSurface su; su.material = rdstr(in);
        const auto vc = rd<uint32_t>(in), tc = rd<uint32_t>(in);
        require(vc >= 3 && vc <= 65535 && tc >= 1 && tc <= 65535, "Surface size");
        su.pos.resize(vc * 3); su.nt.resize(vc * 2); su.uv.resize(vc * 2); su.col.resize(vc); su.idx.resize(tc * 3);
        in.read(reinterpret_cast<char*>(su.pos.data()), vc * 12);
        in.read(reinterpret_cast<char*>(su.nt.data()), vc * 8);
        in.read(reinterpret_cast<char*>(su.uv.data()), vc * 8);
        in.read(reinterpret_cast<char*>(su.col.data()), vc * 4);
        in.read(reinterpret_cast<char*>(su.idx.data()), tc * 6);
        require(bool(in), "Truncated KMSH surface");
        for (auto i : su.idx) require(i < vc, "Index range");
        for (auto f : su.pos) require(std::isfinite(f), "Finite positions");
        m.surfs.push_back(std::move(su));
    }
    return m;
}

static void write_model(const InModel& in) {
    const auto n = in.surfs.size();
    std::vector<std::vector<GfxPackedVertex>> verts(n);
    std::vector<std::vector<Face>> faces(n);
    std::vector<XRigidVertList> rigid(n);
    std::vector<XSurface> surfs(n);
    std::vector<Material> mats(n);
    std::vector<Material*> handles(n);
    std::vector<unsigned short> mips(n, 0);
    float mn[3] = { 1e30f, 1e30f, 1e30f }, mx[3] = { -1e30f, -1e30f, -1e30f };
    for (size_t s = 0; s < n; s++) {
        const auto& su = in.surfs[s];
        const auto vc = su.col.size(), tc = su.idx.size() / 3;
        verts[s].resize(vc); faces[s].resize(tc);
        for (size_t i = 0; i < vc; i++) {
            auto& v = verts[s][i];
            memcpy(v.xyz, &su.pos[i * 3], 12);
            for (int k = 0; k < 3; k++) { mn[k] = std::min(mn[k], v.xyz[k]); mx[k] = std::max(mx[k], v.xyz[k]); }
            v.selfVisibility.packed = 256u | (256u << 9) | (127u << 18);
            v.color.packed = su.col[i];
            v.texCoord.packed = uint32_t(to_half(su.uv[i * 2])) | (uint32_t(to_half(su.uv[i * 2 + 1])) << 16);
            // Packed BO3 normal/tangent words: IW7 uses the same encoding (the
            // pinned T7->IW7 converter copies them unchanged).
            v.normal.packed = su.nt[i * 2];
            v.tangent.packed = su.nt[i * 2 + 1];
        }
        for (size_t i = 0; i < tc; i++) faces[s][i] = { su.idx[i * 3], su.idx[i * 3 + 1], su.idx[i * 3 + 2] };
        rigid[s] = {}; rigid[s].vertCount = uint16_t(vc); rigid[s].triCount = uint16_t(tc);
        auto& x = surfs[s]; x = {};
        // VERTCOL_NONE + SELF_VISIBILITY with the default cone, as the pinned converters.
        x.flags = 0x82; x.vertCount = uint16_t(vc); x.triCount = uint16_t(tc); x.rigidVertListCount = 1;
        x.verts0.packedVerts0 = verts[s].data(); x.triIndices = faces[s].data(); x.rigidVertLists = &rigid[s];
        x.partBits[0] = static_cast<int>(0x80000000u);
        mats[s] = {}; mats[s].name = su.material.c_str(); handles[s] = &mats[s];
    }
    const std::string surfs_name = in.name + "_lod0";
    XModelSurfs ms{}; ms.name = surfs_name.c_str(); ms.surfs = surfs.data(); ms.numsurfs = uint16_t(n); ms.partBits[0] = static_cast<int>(0x80000000u);

    scr_string_t bone = 0; unsigned char classification = 0;
    DObjAnimMat base{}; base.quat[3] = 1; base.transWeight = 2;
    XBoneInfo info{};
    float r2 = 0;
    for (int k = 0; k < 3; k++) {
        info.bounds.midPoint[k] = (mn[k] + mx[k]) * 0.5f;
        info.bounds.halfSize[k] = std::max(0.5f, (mx[k] - mn[k]) * 0.5f);
        r2 += std::max(mn[k] * mn[k], mx[k] * mx[k]);
    }
    info.radiusSquared = r2;
    XModel model{};
    model.name = in.name.c_str(); model.hasLods = true; model.numLods = 1; model.collLod = 255; model.shadowCutoffLod = 6;
    model.flags = XMODEL_FLAG_HAS_RIGID_VERT_LIST;
    model.numBones = 1; model.numRootBones = 1; model.numsurfs = uint16_t(n); model.scale = 1; model.radius = std::sqrt(r2);
    model.bounds = info.bounds;
    model.boneNames = &bone; model.partClassification = &classification; model.baseMat = &base; model.boneInfo = &info;
    model.invHighMipRadius = mips.data(); model.materialHandles = handles.data();
    model.lodInfo[0].numsurfs = uint16_t(n); model.lodInfo[0].modelSurfs = &ms; model.lodInfo[0].partBits[0] = static_cast<int>(0x80000000u);
    model.lodInfo[0].dist = 1000000.0f;

    {
        assetmanager::dumper d; require(d.open("xsurface\\" + surfs_name + ".xsb", false), "Dumper surface open");
        d.dump_single(&ms); d.dump_string(ms.name); d.dump_array(ms.surfs, ms.numsurfs);
        for (size_t s = 0; s < n; s++) {
            auto& x = surfs[s];
            d.dump_array(x.verts0.packedVerts0, x.vertCount); d.dump_array(x.triIndices, x.triCount);
            d.dump_array(x.rigidVertLists, x.rigidVertListCount);
            d.dump_raw(x.blendVerts, 0); d.dump_raw(x.lmapUnwrap, 0); d.dump_raw(x.tensionData, 0); d.dump_raw(x.tensionAccumTable, 0);
        }
        d.close();
    }
    {
        assetmanager::dumper d; require(d.open("xmodel\\" + in.name + ".xmb", false), "Dumper model open");
        d.dump_single(&model); d.dump_string(model.name); d.dump_string("tag_origin");
        d.dump_array(model.parentList, 0); d.dump_array(model.tagAngles, 0); d.dump_array(model.tagPositions, 0);
        d.dump_array(model.partClassification, 1); d.dump_array(model.baseMat, 1); d.dump_array(model.reactiveMotionParts, 0);
        d.dump_single(model.reactiveMotionTweaks); d.dump_array(model.collSurfs, 0); d.dump_array(model.boneInfo, 1);
        d.dump_array(model.invHighMipRadius, model.numsurfs);
        d.dump_array(model.materialHandles, model.numsurfs);
        for (unsigned i = 0; i < model.numsurfs; i++) d.dump_asset(model.materialHandles[i]);
        for (auto& lod : model.lodInfo) d.dump_asset(lod.modelSurfs);
        d.dump_asset(model.physicsAsset); d.dump_asset(model.physicsFXShape);
        d.dump_asset(model.scriptableMoverDef); d.dump_asset(model.proceduralBones);
        d.dump_array(model.unknown03, 0); d.dump_array(model.unknownVec3, 0); d.dump_array(model.unknown04, 0);
        d.close();
    }
    size_t tris = 0, vs = 0; for (auto& su : in.surfs) { tris += su.idx.size() / 3; vs += su.col.size(); }
    std::cout << "{\"model\":\"" << in.name << "\",\"surfaces\":" << n << ",\"vertices\":" << vs << ",\"triangles\":" << tris
              << ",\"mins\":[" << mn[0] << "," << mn[1] << "," << mn[2] << "],\"maxs\":[" << mx[0] << "," << mx[1] << "," << mx[2] << "]}\n";
}

// KIMG v1: name, dxgi format, width, height, levels, disk flags, full mip chain bytes.
static void write_image(const fs::path& p) {
    std::ifstream in(p, std::ios::binary);
    require(bool(in), "Open KIMG");
    require(rd<uint32_t>(in) == 0x474D494B && rd<uint32_t>(in) == 1, "KIMG v1 required");
    const std::string name = rdstr(in);
    const auto fmt = rd<uint32_t>(in), w = rd<uint32_t>(in), h = rd<uint32_t>(in), levels = rd<uint32_t>(in), flags = rd<uint32_t>(in), size = rd<uint32_t>(in);
    require(w >= 1 && w <= 4096 && h >= 1 && h <= 4096 && levels >= 1 && levels <= 13 && size >= 1 && size <= (64u << 20), "KIMG bounds");
    std::vector<unsigned char> pixels(size);
    in.read(reinterpret_cast<char*>(pixels.data()), size);
    require(bool(in), "Truncated KIMG");
    GfxImage image{};
    image.imageFormat = static_cast<DXGI_FORMAT>(fmt);
    image.flags = flags;
    image.mapType = MAPTYPE_2D;
    image.semantic = TS_COLOR_MAP;
    image.category = IMG_CATEGORY_LOAD_FROM_FILE;
    image.dataLen1 = size; image.dataLen2 = size;
    image.width = uint16_t(w); image.height = uint16_t(h); image.depth = 1; image.numElements = 1;
    image.levelCount = uint8_t(levels); image.streamed = 0;
    image.pixelData = pixels.data();
    image.name = name.c_str();
    assetmanager::dumper d; require(d.open("images\\" + name + ".iw7Image", false), "Dumper image open");
    d.dump_single(&image); d.dump_string(image.name); d.dump_array(image.pixelData, image.dataLen1);
    d.close();
}

int main(int argc, char** argv) {
    try {
        if (argc == 4 && std::string(argv[1]) == "--images") {
            const fs::path input = fs::absolute(argv[2]);
            output_root = fs::absolute(argv[3]);
            require(fs::is_directory(input), "Existing KIMG input required");
            size_t n = 0;
            for (auto& e : fs::directory_iterator(input)) if (e.is_regular_file() && e.path().extension() == ".kimg") { write_image(e.path()); n++; }
            std::cout << "{\"images\":" << n << "}\n";
            return 0;
        }
        require(argc == 3, "Usage: kino-writer.exe <kmsh-dir> <fresh-output-dir> | --images <kimg-dir> <output-dir>");
        const fs::path input = fs::absolute(argv[1]);
        output_root = fs::absolute(argv[2]);
        require(fs::is_directory(input) && !fs::exists(output_root), "Existing input and fresh output required");
        fs::create_directories(output_root);
        std::vector<fs::path> files;
        for (auto& e : fs::directory_iterator(input)) if (e.is_regular_file() && e.path().extension() == ".kmsh") files.push_back(e.path());
        std::sort(files.begin(), files.end());
        require(!files.empty(), "No KMSH input");
        for (auto& f : files) write_model(load(f));
        return 0;
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
