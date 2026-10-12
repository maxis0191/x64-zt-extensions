#pragma once
#include <cstddef>
// Include the real pinned iw7/structs.hpp before this header in the NEW writer.
// These assertions have not been compiled in this source-only preparation.
namespace doom_two_bone_abi
{
using namespace zonetool::iw7;
static_assert(sizeof(XSurface)==256 && sizeof(XModelSurfs)==56);
static_assert(sizeof(XModel)==736 && sizeof(XModelLodInfo)==64);
static_assert(sizeof(GfxPackedVertex)==32 && sizeof(Face)==6);
static_assert(sizeof(DObjAnimMat)==32 && sizeof(XBoneInfo)==28 && sizeof(XBlendInfo)==2);
static_assert(sizeof(XModelAngle)==8 && sizeof(XModelTagPos)==12 && sizeof(scr_string_t)==4);
static_assert(offsetof(XModelSurfs,name)==0 && offsetof(XModelSurfs,surfs)==8);
static_assert(offsetof(XModelSurfs,numsurfs)==16 && offsetof(XModelSurfs,partBits)==20);
static_assert(offsetof(DObjAnimMat,quat)==0 && offsetof(DObjAnimMat,trans)==16 && offsetof(DObjAnimMat,transWeight)==28);
static_assert(offsetof(XBoneInfo,bounds)==0 && offsetof(XBoneInfo,radiusSquared)==24);
static_assert(offsetof(XSurface,flags)==0 && offsetof(XSurface,vertCount)==2 && offsetof(XSurface,triCount)==4);
static_assert(offsetof(XSurface,rigidVertListCount)==6 && offsetof(XSurface,blendVertCounts)==8);
static_assert(offsetof(XSurface,blendVertSize)==24 && offsetof(XSurface,verts0)==32 && offsetof(XSurface,triIndices)==40);
static_assert(offsetof(XSurface,rigidVertLists)==72 && offsetof(XSurface,blendVerts)==80);
static_assert(offsetof(XSurface,blendVertsBuffer)==88 && offsetof(XSurface,blendVertsView)==96 && offsetof(XSurface,partBits)==224);
static_assert(offsetof(GfxPackedVertex,selfVisibility)==12 && offsetof(GfxPackedVertex,color)==16);
static_assert(offsetof(GfxPackedVertex,texCoord)==20 && offsetof(GfxPackedVertex,normal)==24 && offsetof(GfxPackedVertex,tangent)==28);
static_assert(offsetof(XModel,numBones)==20 && offsetof(XModel,numRootBones)==21 && offsetof(XModel,numClientBones)==24);
static_assert(offsetof(XModel,boneNames)==152 && offsetof(XModel,parentList)==160 && offsetof(XModel,tagAngles)==168);
static_assert(offsetof(XModel,tagPositions)==176 && offsetof(XModel,partClassification)==184 && offsetof(XModel,baseMat)==192);
static_assert(offsetof(XModel,materialHandles)==216 && offsetof(XModel,lodInfo)==224);
static_assert(offsetof(XModel,boneInfo)==616 && offsetof(XModel,invHighMipRadius)==624);
static_assert(offsetof(XModel,unknownIndex)==704 && offsetof(XModel,unknownIndex2)==720);
static_assert(offsetof(XModelLodInfo,modelSurfs)==8 && offsetof(XModelLodInfo,partBits)==16 && offsetof(XModelLodInfo,surfs)==48);
static_assert(SURF_FLAG_VERTCOL_NONE==2 && SURF_FLAG_SKINNED==4 && SURF_FLAG_SELF_VISIBILITY==128);
}
