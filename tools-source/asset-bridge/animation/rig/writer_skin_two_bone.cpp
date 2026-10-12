// Distinct original two-bone candidate, not an extension of the rigid writer.
// Build only after rehashing the real pinned SDK and the prepared input header.
// This source has not yet been compiled or executed. Its output needs the
// independent Python reader before any separate FF or engine experiment.
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
#include <type_traits>
#define assert_sizeof(T, N) static_assert(sizeof(T)==N)
#define assert_offsetof(T, M, N) static_assert(offsetof(T,M)==N)
#include "zonetool/iw7/structs.hpp"
#include "zonetool/utils/io/assetmanager.hpp"
#include "skin_native_abi.hpp"
#include "skin_geometry.hpp"
#include "half_uv.hpp"

namespace fs=std::filesystem;
static fs::path output_root;
static std::string model_name,surfs_name;
static bool close_failed{};
static void require(bool ok,const char* message) {if(!ok)throw std::runtime_error(message);}
static void unlinked(const fs::path& path)
{
    require(path.is_absolute(),"Absolute native output required");
    for(auto p=path;!p.empty();p=p.parent_path()) {
        const auto attrs=GetFileAttributesW(p.c_str());
        require(attrs!=INVALID_FILE_ATTRIBUTES || GetLastError()==ERROR_FILE_NOT_FOUND || GetLastError()==ERROR_PATH_NOT_FOUND,"Output ancestry unreadable");
        require(attrs==INVALID_FILE_ATTRIBUTES || !(attrs&FILE_ATTRIBUTE_REPARSE_POINT),"Reparse output ancestry refused");
        if(p==p.parent_path())break;
    }
}
// The real header-only ZoneTool dumper calls this small file adapter. It can
// create only the two selected candidate paths and never opens a retail file.
namespace zonetool::filesystem {
file::file()=default;
file::file(const std::string& path){initialize(path);}
file::file(const file& other){require(!other.fp,"Open file cannot be copied");initialize(other.filepath);}
file::file(file&& other) noexcept:fp(std::exchange(other.fp,nullptr)),filepath(std::move(other.filepath)){}
file& file::operator=(file&& other) noexcept {if(this!=&other){close();fp=std::exchange(other.fp,nullptr);filepath=std::move(other.filepath);}return *this;}
file& file::operator=(const file& other){require(!other.fp,"Open file cannot be copied");close();initialize(other.filepath);return *this;}
file::~file(){close();}
void file::initialize(const fs::path& path){require(!fp,"Initialize opened file");filepath=path;}
FILE* file::get_fp(){return fp;}
errno_t file::open(std::string mode,bool,bool)
{
    require(mode=="wb" && !fp,"Native writer is create-only");
    require(filepath==fs::path("xmodel")/(model_name+".xmb") || filepath==fs::path("xsurface")/(surfs_name+".xsb"),"Only two-bone profile paths allowed");
    const auto path=output_root/filepath;unlinked(path);
    fs::create_directories(path.parent_path());unlinked(path);
    const auto handle=CreateFileW(path.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
    require(handle!=INVALID_HANDLE_VALUE,"Fresh native output file required");
    const int fd=_open_osfhandle(reinterpret_cast<intptr_t>(handle),_O_BINARY|_O_WRONLY);
    if(fd<0){CloseHandle(handle);throw std::runtime_error("Native writer descriptor failed");}
    fp=_fdopen(fd,"wb");if(!fp){_close(fd);throw std::runtime_error("Native writer stream failed");}
    return 0;
}
size_t file::write(const void* data,size_t size,size_t count)
{
    require(fp && data && size && count && size<=65536 && count<=65536/size,"Bounded native write");
    require(fwrite(data,size,count,fp)==count,"Short native write");
    return count;
}
size_t file::write_string(const char* value){require(value && strlen(value)<=128,"Bounded native name");return write(value,1,strlen(value)+1);}
size_t file::write_string(const std::string& value){return write_string(value.c_str());}
int file::close(){if(!fp)return 0;const auto result=fclose(std::exchange(fp,nullptr));close_failed=close_failed || result!=0;return result;}
}

using namespace zonetool;
using namespace zonetool::iw7;
static std::uint32_t quantized_component(float value)
{
    require(std::isfinite(value) && value>=-1.0f && value<=1.0f,"Finite unit component required");
    return static_cast<std::uint32_t>(std::floor((value+1.0f)*0.5f*1023.0f+0.5f));
}
static std::uint32_t pack_normal(const float* value)
{
    return 0xC0000000u | quantized_component(value[0]) | (quantized_component(value[1])<<10) | (quantized_component(value[2])<<20);
}
static std::uint32_t pack_tangent(const float* value,float handedness)
{
    // Equivalent to pinned Vec3PackUnitVecWithAlpha_H1 for this fixed +/-1
    // handedness. The shader interpretation remains an engine observation.
    require(handedness==-1.0f || handedness==1.0f,"Fixed tangent handedness required");
    return quantized_component(value[0]) | (quantized_component(value[1])<<10) | (quantized_component(value[2])<<20) | (quantized_component(handedness)<<30);
}
static void dump_surface(XModelSurfs& asset)
{
    assetmanager::dumper dump;
    require(dump.open("xsurface/"+surfs_name+".xsb",false),"Native surface dumper open");
    dump.dump_single(&asset);dump.dump_string(asset.name);dump.dump_array(asset.surfs,1);
    auto& surface=asset.surfs[0];
    dump.dump_array(surface.verts0.packedVerts0,8);dump.dump_array(surface.triIndices,6);
    dump.dump_array(surface.rigidVertLists,0);dump.dump_raw(surface.blendVerts,surface.blendVertSize & 0xFFFFFFFEu);
    dump.dump_raw(surface.lmapUnwrap,8*surface.vertCount);
    dump.dump_raw(surface.tensionData,4*(surface.blendVertCounts[0]+3*surface.blendVertCounts[1]));
    dump.dump_raw(surface.tensionAccumTable,32*surface.vertCount);
    // SUBDIV and SH probe flags absent: the pinned serializer emits no records.
    dump.close();
}
static void dump_model(XModel& model)
{
    assetmanager::dumper dump;
    require(dump.open("xmodel/"+model_name+".xmb",false),"Native model dumper open");
    dump.dump_single(&model);dump.dump_string(model.name);
    dump.dump_string("tag_origin");dump.dump_string("tag_probe");
    dump.dump_array(model.parentList,1);dump.dump_array(model.tagAngles,1);dump.dump_array(model.tagPositions,1);
    dump.dump_array(model.partClassification,2);dump.dump_array(model.baseMat,2);
    dump.dump_array(model.reactiveMotionParts,0);dump.dump_single(model.reactiveMotionTweaks);
    dump.dump_array(model.collSurfs,0);dump.dump_array(model.boneInfo,2);dump.dump_array(model.invHighMipRadius,1);
    dump.dump_array(model.materialHandles,1);dump.dump_asset(model.materialHandles[0]);
    for(auto& lod:model.lodInfo)dump.dump_asset(lod.modelSurfs);
    dump.dump_asset(model.physicsAsset);dump.dump_asset(model.physicsFXShape);
    dump.dump_asset(model.scriptableMoverDef);dump.dump_asset(model.proceduralBones);
    dump.dump_array(model.unknown03,0);dump.dump_array(model.unknownVec3,0);dump.dump_array(model.unknown04,0);
    dump.close();
}

int main(int argc,char** argv)
{
    try {
        require(argc==3,"Usage: two-bone-writer.exe fresh-absolute-directory first|second");
        const std::string hypothesis=argv[2];require(hypothesis=="first" || hypothesis=="second","Distinct first/second profile required");
        model_name=hypothesis=="first" ? doom_skin_input::first_name : doom_skin_input::second_name;
        surfs_name=model_name+"_lod0";
        output_root=fs::path(argv[1]);unlinked(output_root);
        require(!fs::exists(output_root),"Fresh native output directory required");
        fs::create_directories(output_root);unlinked(output_root);
        static_assert(sizeof(void*)==8 && sizeof(float)==4 && sizeof(int)==4);
        static_assert(std::is_trivially_copyable_v<XModel> && std::is_trivially_copyable_v<XSurface>);
        GfxPackedVertex vertices[8]{};Face triangles[6]{};XBlendInfo blend[24]{};
        const float tangent[3]={0.0f,1.0f,0.0f};
        for(unsigned i=0;i<8;++i) {
            auto& vertex=vertices[i];std::memcpy(vertex.xyz,doom_skin_input::positions[i],sizeof(vertex.xyz));
            vertex.selfVisibility.packed=256u|(256u<<9)|(127u<<18);vertex.color.packed=0xFFFFFFFFu;
            vertex.texCoord.packed=doom_mesh::pack_uv(doom_skin_input::uvs[i]);
            vertex.normal.packed=pack_normal(doom_skin_input::normals[i]);vertex.tangent.packed=pack_tangent(tangent,-1.0f);
            require(vertex.normal.packed==0xE0080000u && vertex.tangent.packed==0x200FFE00u,"Fixed original source codec words");
        }
        for(unsigned i=0;i<6;++i) {
            for(auto index:doom_skin_input::triangles[i])require(index<8,"Original triangle range");
            triangles[i]={doom_skin_input::triangles[i][0],doom_skin_input::triangles[i][1],doom_skin_input::triangles[i][2]};
        }
        std::memcpy(blend,hypothesis=="first" ? doom_skin_input::first_blend[0] : doom_skin_input::second_blend[0],sizeof(blend));
        XSurface surface;std::memset(&surface,0,sizeof(surface));
        surface.flags=SURF_FLAG_VERTCOL_NONE|SURF_FLAG_SKINNED|SURF_FLAG_SELF_VISIBILITY;
        surface.vertCount=8;surface.triCount=6;surface.blendVertCounts[0]=4;surface.blendVertCounts[1]=4;
        surface.blendVertSize=static_cast<unsigned int>(sizeof(blend));surface.verts0.packedVerts0=vertices;surface.triIndices=triangles;surface.blendVerts=blend;
        surface.partBits[0]=static_cast<int>(0xC0000000u); // proposed two-bone mask, engine proof pending
        XModelSurfs surfs;std::memset(&surfs,0,sizeof(surfs));
        surfs.name=surfs_name.c_str();surfs.surfs=&surface;surfs.numsurfs=1;surfs.partBits[0]=surface.partBits[0];
        unsigned char parents[1]{};XModelAngle angles[1]{};XModelTagPos tag_positions[1]{};DObjAnimMat bases[2]{};
        std::memcpy(parents,doom_skin_input::parents,sizeof(parents));std::memcpy(angles,doom_skin_input::angles,sizeof(angles));
        std::memcpy(tag_positions,doom_skin_input::tag_positions,sizeof(tag_positions));std::memcpy(bases,doom_skin_input::bases,sizeof(bases));
        scr_string_t bone_names[2]{};unsigned char classification[2]{};unsigned short mip{};
        Material material;std::memset(&material,0,sizeof(material));material.name=doom_skin_input::material_name;Material* material_handle=&material;
        XBoneInfo infos[2]{};
        for(unsigned i=0;i<2;++i){infos[i].bounds.midPoint[2]=i==0 ? 8.0f : 0.0f;infos[i].bounds.halfSize[1]=4.0f;infos[i].bounds.halfSize[2]=8.0f;infos[i].radiusSquared=i==0 ? 272.0f : 80.0f;}
        XModel model;std::memset(&model,0,sizeof(model));
        model.name=model_name.c_str();model.hasLods=true;model.numLods=1;model.collLod=255;model.shadowCutoffLod=6;
        model.numBones=2;model.numRootBones=1;model.numsurfs=1;model.scale=1.0f;model.radius=std::sqrt(272.0f);
        model.bounds.midPoint[2]=8.0f;model.bounds.halfSize[1]=4.0f;model.bounds.halfSize[2]=8.0f;
        model.boneNames=bone_names;model.parentList=parents;model.tagAngles=angles;model.tagPositions=tag_positions;
        model.partClassification=classification;model.baseMat=bases;model.boneInfo=infos;model.invHighMipRadius=&mip;model.materialHandles=&material_handle;
        model.lodInfo[0].dist=1000000.0f;model.lodInfo[0].numsurfs=1;model.lodInfo[0].modelSurfs=&surfs;model.lodInfo[0].partBits[0]=surface.partBits[0];
        model.unknownIndex=255;model.unknownIndex2=255;
        dump_surface(surfs);dump_model(model);require(!close_failed,"Native output close failed");
        require(fs::file_size(output_root/"xmodel"/(model_name+".xmb"))<=65536 && fs::file_size(output_root/"xsurface"/(surfs_name+".xsb"))<=65536,"Bounded native outputs");
        std::cout<<"{\"schema\":\"iw7.doom-two-bone-writer-emission/1\",\"hypothesis\":\""<<hypothesis<<"\",\"vertices\":8,\"triangles\":6,\"bones\":2,\"rigid_lists\":0,\"blend_bytes\":48,\"native_files_emitted\":true,\"independent_read_verified\":false,\"part_bits_engine_verified\":false,\"iw7_shader_encoding_verified\":false,\"weight_direction_engine_verified\":false,\"draw_verified\":false,\"pixels_verified\":false,\"ready\":false}\n";
        return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
