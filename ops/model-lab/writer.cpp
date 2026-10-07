// Original fixed rigid cube. No game process, retail mesh, or shared tool mutation.
// Includes the exact ZoneTool headers; the adapter only opens two fresh owned files.
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
#define assert_sizeof(T, N) static_assert(sizeof(T)==N)
#define assert_offsetof(T, M, N) static_assert(offsetof(T,M)==N)
#include "zonetool/iw7/structs.hpp"
#include "zonetool/utils/io/assetmanager.hpp"
#include "probe_geometry.hpp"

namespace fs=std::filesystem;
static fs::path output_root;
static void require(bool ok,const char* msg) { if(!ok)throw std::runtime_error(msg); }
static void unlinked(const fs::path& path) {
    for(auto p=fs::absolute(path);!p.empty();p=p.parent_path()) {
        const auto attrs=GetFileAttributesW(p.c_str());
        require(attrs==INVALID_FILE_ATTRIBUTES || !(attrs&FILE_ATTRIBUTE_REPARSE_POINT),"Reparse ancestry refused");
        if(p==p.parent_path())break;
    }
}
namespace zonetool::filesystem {
file::file()=default;
file::file(const std::string& path){initialize(path);}
file::file(const file& other){require(!other.fp,"Open file cannot be copied");initialize(other.filepath);}
file::file(file&& other) noexcept:fp(std::exchange(other.fp,nullptr)),filepath(std::move(other.filepath)){}
file& file::operator=(file&& other) noexcept { if(this!=&other){close();fp=std::exchange(other.fp,nullptr);filepath=std::move(other.filepath);}return *this; }
file& file::operator=(const file& other){require(!other.fp,"Open file cannot be copied");close();initialize(other.filepath);return *this;}
file::~file(){close();}
void file::initialize(const fs::path& path){require(!fp,"Initialize opened file");filepath=path;}
FILE* file::get_fp(){return fp;}
errno_t file::open(std::string mode,bool,bool) {
    require(filepath=="xmodel/paris_model_probe.xmb" || filepath=="xsurface/paris_model_probe_lod0.xsb","Only original probe paths allowed");
    const auto path=output_root/filepath;unlinked(path);
    if(mode=="wb") {
        fs::create_directories(path.parent_path());unlinked(path);
        HANDLE handle=CreateFileW(path.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
        require(handle!=INVALID_HANDLE_VALUE,"Fresh output asset required");
        int fd=_open_osfhandle(reinterpret_cast<intptr_t>(handle),_O_BINARY|_O_WRONLY);
        if(fd<0){CloseHandle(handle);throw std::runtime_error("Writer descriptor failed");}
        fp=_fdopen(fd,"wb");if(!fp){_close(fd);throw std::runtime_error("Writer stream failed");}
    } else {
        require(mode=="rb" && fs::file_size(path)<=8192,"Bounded owned roundtrip only");
        const auto error=_wfopen_s(&fp,path.c_str(),L"rb");require(!error && fp,"Reader open failed");
    }
    return 0;
}
size_t file::write(const void* data,size_t size,size_t count){require(fp && fwrite(data,size,count,fp)==count,"Short write");return count;}
size_t file::write_string(const char* str){return write(str,1,strlen(str)+1);}
size_t file::write_string(const std::string& str){return write_string(str.c_str());}
size_t file::read(void* data,size_t size,size_t count){require(fp && fread(data,size,count,fp)==count,"Truncated asset");return count;}
size_t file::read_string(std::string* str){str->clear();for(size_t n=0;n<256;n++){char c;read(&c,1,1);if(!c)return n+1;str->push_back(c);}throw std::runtime_error("Unbounded string refused");}
int file::close(){if(!fp)return 0;const auto result=fclose(std::exchange(fp,nullptr));return result;}
}

using namespace zonetool;
using namespace zonetool::iw7;
// Explicit candidate follows the pinned H1 encoder, not an asserted IW7 shader proof.
// IEEE half 0/1 are exact for this fixed UV set. No general mesh import is claimed.
static uint32_t pack_unit_candidate(const float* v){uint32_t out=0xC0000000u;for(unsigned i=0;i<3;i++){require(v[i]>=-1 && v[i]<=1,"Unit component range");out|=static_cast<uint32_t>(std::floor((v[i]+1)*0.5f*1023+0.5f))<<(10*i);}return out;}
static uint32_t pack_uv(const float* uv){require((uv[0]==0 || uv[0]==1)&&(uv[1]==0 || uv[1]==1),"Fixed UV corners required");return (uv[0]==1?0x3C00u:0u)|((uv[1]==1?0x3C00u:0u)<<16);}
static void dump_surface(XModelSurfs& asset){
    assetmanager::dumper d;require(d.open("xsurface/paris_model_probe_lod0.xsb",false),"Dumper surface open");
    d.dump_single(&asset);d.dump_string(asset.name);d.dump_array(asset.surfs,1);
    auto& s=asset.surfs[0];d.dump_array(s.verts0.packedVerts0,24);d.dump_array(s.triIndices,12);d.dump_array(s.rigidVertLists,1);
    d.dump_raw(s.blendVerts,0);d.dump_raw(s.lmapUnwrap,0);d.dump_raw(s.tensionData,0);d.dump_raw(s.tensionAccumTable,0);
    // No subdiv/SH flags: pinned dump_subdiv/dump_shprobesimplexdata emit nothing.
    d.close();
}
static void dump_model(XModel& m){
    assetmanager::dumper d;require(d.open("xmodel/paris_model_probe.xmb",false),"Dumper model open");
    d.dump_single(&m);d.dump_string(m.name);d.dump_string("tag_origin");
    d.dump_array(m.parentList,0);d.dump_array(m.tagAngles,0);d.dump_array(m.tagPositions,0);
    d.dump_array(m.partClassification,1);d.dump_array(m.baseMat,1);d.dump_array(m.reactiveMotionParts,0);
    d.dump_single(m.reactiveMotionTweaks);d.dump_array(m.collSurfs,0);d.dump_array(m.boneInfo,1);
    d.dump_array(m.invHighMipRadius,1);d.dump_array(m.materialHandles,1);d.dump_asset(m.materialHandles[0]);
    for(auto& lod:m.lodInfo)d.dump_asset(lod.modelSurfs);
    d.dump_asset(m.physicsAsset);d.dump_asset(m.physicsFXShape);
    // No Havok sidecar, physics names, or aim bones when their counts are zero.
    d.dump_asset(m.scriptableMoverDef);d.dump_asset(m.proceduralBones);
    d.dump_array(m.unknown03,0);d.dump_array(m.unknownVec3,0);d.dump_array(m.unknown04,0);d.close();
}
static XModelSurfs* read_surface(zone_memory& memory){
    assetmanager::reader r(&memory);require(r.open("xsurface/paris_model_probe_lod0.xsb",false),"Reader surface open");
    auto* a=r.read_single<XModelSurfs>();a->name=r.read_string();a->surfs=r.read_array<XSurface>();
    require(a->numsurfs==1,"Roundtrip surface count");auto& s=a->surfs[0];
    require(s.vertCount==24 && s.triCount==12 && s.rigidVertListCount==1 && s.flags==0x82,"Roundtrip bounded rigid surface");
    s.verts0.packedVerts0=r.read_array<GfxPackedVertex>();s.triIndices=r.read_array<Face>();s.rigidVertLists=r.read_array<XRigidVertList>();
    s.blendVerts=r.read_raw<XBlendInfo>();s.lmapUnwrap=r.read_raw<float[2]>();s.tensionData=r.read_raw<float>();s.tensionAccumTable=r.read_raw<unsigned short>();
    require(!s.rigidVertLists[0].collisionTree && !s.blendVerts && !s.lmapUnwrap && !s.tensionData && !s.tensionAccumTable,"Unexpected optional surface stream");
    r.close();return a;
}
static XModel* read_model(zone_memory& memory){
    assetmanager::reader r(&memory);require(r.open("xmodel/paris_model_probe.xmb",false),"Reader model open");
    auto* m=r.read_single<XModel>();m->name=r.read_string();require(std::string(r.read_string())=="tag_origin","Bone name roundtrip");
    require(m->numBones==1 && m->numRootBones==1 && !m->numClientBones && m->numsurfs==1 && m->numLods==1,"Model counts roundtrip");
    m->parentList=r.read_array<unsigned char>();m->tagAngles=r.read_array<XModelAngle>();m->tagPositions=r.read_array<XModelTagPos>();
    m->partClassification=r.read_array<unsigned char>();m->baseMat=r.read_array<DObjAnimMat>();m->reactiveMotionParts=r.read_array<ReactiveMotionModelPart>();
    m->reactiveMotionTweaks=r.read_single<ReactiveMotionModelTweaks>();m->collSurfs=r.read_array<XModelCollSurf_s>();m->boneInfo=r.read_array<XBoneInfo>();
    m->invHighMipRadius=r.read_array<unsigned short>();m->materialHandles=r.read_array<Material*>();m->materialHandles[0]=r.read_asset<Material>();
    for(auto& lod:m->lodInfo)lod.modelSurfs=r.read_asset<XModelSurfs>();
    m->physicsAsset=r.read_asset<PhysicsAsset>();m->physicsFXShape=r.read_asset<PhysicsFXShape>();
    m->scriptableMoverDef=r.read_asset<ScriptableDef>();m->proceduralBones=r.read_asset<XAnimProceduralBones>();
    m->unknown03=r.read_array<char>();m->unknownVec3=r.read_array<vec3_t>();m->unknown04=r.read_array<unk_1453E14D8>();r.close();return m;
}
int main(int argc,char** argv){try{
    const bool verify_existing=argc==3 && std::string(argv[1])=="--verify-existing";
    require(argc==2 || verify_existing,"Usage: model-writer.exe fresh-directory | --verify-existing owned-dump-directory");
    output_root=fs::absolute(argv[verify_existing?2:1]);unlinked(output_root);
    if(verify_existing){require(fs::is_directory(output_root),"Owned roundtrip directory required");}
    else{require(!fs::exists(output_root),"Fresh artifact directory required");fs::create_directories(output_root);unlinked(output_root);}
    GfxPackedVertex vertices[24]{};Face triangles[12]{};
    for(unsigned i=0;i<24;i++){auto& v=vertices[i];auto& input=probe_vertices[i];memcpy(v.xyz,input.xyz,sizeof(v.xyz));v.selfVisibility.packed=256u|(256u<<9)|(127u<<18);v.color.packed=0xFFFFFFFFu;v.texCoord.packed=pack_uv(input.uv);v.normal.packed=pack_unit_candidate(input.normal);v.tangent.packed=pack_unit_candidate(input.tangent);}
    for(unsigned i=0;i<12;i++){triangles[i]={probe_triangles[i][0],probe_triangles[i][1],probe_triangles[i][2]};}
    XRigidVertList rigid{};rigid.vertCount=24;rigid.triCount=12;
    XSurface surf{};surf.flags=0x82;surf.vertCount=24;surf.triCount=12;surf.rigidVertListCount=1;surf.verts0.packedVerts0=vertices;surf.triIndices=triangles;surf.rigidVertLists=&rigid;surf.partBits[0]=static_cast<int>(0x80000000u);
    XModelSurfs surfs{};surfs.name="paris_model_probe_lod0";surfs.surfs=&surf;surfs.numsurfs=1;surfs.partBits[0]=surf.partBits[0];
    scr_string_t bone=0;unsigned char classification=0;unsigned short mip=0;Material material_asset{};material_asset.name=probe_material_name;Material* material=probe_material_name?&material_asset:nullptr;
    DObjAnimMat base{};base.quat[3]=1;base.transWeight=2;XBoneInfo info{};for(float& f:info.bounds.halfSize)f=8;info.radiusSquared=192;
    // Pinned H1->IW7 converter uses 6; its comment records 0xFF fade-outs.
    // Keep collision's independent 0xFF sentinel unchanged. Pixel proof pending.
    XModel model{};model.name="paris_model_probe";model.hasLods=true;model.numLods=1;model.collLod=255;model.shadowCutoffLod=6;model.flags=XMODEL_FLAG_HAS_RIGID_VERT_LIST;
    model.numBones=1;model.numRootBones=1;model.numsurfs=1;model.scale=1;model.radius=std::sqrt(192.0f);for(float& f:model.bounds.halfSize)f=8;
    model.boneNames=&bone;model.partClassification=&classification;model.baseMat=&base;model.boneInfo=&info;model.invHighMipRadius=&mip;model.materialHandles=&material;
    model.lodInfo[0].numsurfs=1;model.lodInfo[0].modelSurfs=&surfs;model.lodInfo[0].partBits[0]=surf.partBits[0];
    if(!verify_existing){dump_surface(surfs);dump_model(model);}
    zone_memory memory(1024*1024);auto* rs=read_surface(memory);auto* rm=read_model(memory);
    require(std::string(rs->name)==surfs.name && std::string(rm->name)==model.name,"Names roundtrip");
    require(!memcmp(rs->surfs[0].verts0.packedVerts0,vertices,sizeof(vertices)),"Every position/packed UV/normal/tangent/color differs");
    require(!memcmp(rs->surfs[0].triIndices,triangles,sizeof(triangles)),"Every triangle index differs");
    require(!memcmp(rs->surfs[0].rigidVertLists,&rigid,sizeof(rigid)) && !memcmp(rs->partBits,surfs.partBits,sizeof(surfs.partBits)),"Rigid weights/part bits differ");
    require(!memcmp(rm->baseMat,&base,sizeof(base)) && !memcmp(rm->boneInfo,&info,sizeof(info)) && !memcmp(&rm->bounds,&model.bounds,sizeof(model.bounds)),"Rest pose/bone/model bounds differ");
    require(rm->radius==model.radius && rm->scale==1 && rm->partClassification[0]==0 && rm->invHighMipRadius[0]==0,"Scalar model metadata differs");
    require(rm->shadowCutoffLod==6 && rm->collLod==255,"Shadow cutoff or independent collision sentinel differs");
    require(rm->lodInfo[0].numsurfs==1 && rm->lodInfo[0].surfIndex==0 && std::string(rm->lodInfo[0].modelSurfs->name)==surfs.name && !memcmp(rm->lodInfo[0].partBits,model.lodInfo[0].partBits,sizeof(model.lodInfo[0].partBits)),"LOD reference differs");
    for(unsigned i=1;i<6;i++)require(!rm->lodInfo[i].modelSurfs,"Unexpected extra LOD");
    require(!rm->parentList && !rm->tagAngles && !rm->tagPositions && !rm->physicsAsset && !rm->physicsFXShape && !rm->scriptableMoverDef && !rm->proceduralBones && !rm->unknown03 && !rm->unknownVec3 && !rm->unknown04,"Unexpected model dependency");
    require((!material && !rm->materialHandles[0]) || (material && rm->materialHandles[0] && std::string(rm->materialHandles[0]->name)==probe_material_name),"Material reference differs");
    std::cout<<"{\"schema\":\"iw7.model-roundtrip/1\",\"vertices\":24,\"triangles\":12,\"bones\":1,\"surfaces\":1,\"lods\":1,\"shadow_cutoff_lod\":6,\"collision_lod\":255,\"geometry_roundtrip_verified\":true,\"read_existing_supported\":true,\"normal_encoding\":\"H1-1010102-candidate\",\"iw7_normal_encoding_verified\":false,\"material_reference\":"<<(probe_material_name?std::string("\"")+probe_material_name+"\"":"null")<<",\"ff_built\":false,\"pixels_verified\":false,\"ready\":false}\n";
    return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
