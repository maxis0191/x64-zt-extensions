#pragma once
#include <cstddef>
// Compile against the real pinned SDK, never replacement packed structs.
// These assertions are prepared source, not evidence of a native compilation.
namespace probe_native_abi {
using namespace zonetool::iw7;
static_assert(sizeof(void*) == 8 && sizeof(scr_string_t) == 4);
static_assert(sizeof(XAnimParts) == 136 && sizeof(XAnimNotifyInfo) == 8);
static_assert(offsetof(XAnimParts, name) == 0 && offsetof(XAnimParts, names) == 8);
static_assert(offsetof(XAnimParts, dataByte) == 16 && offsetof(XAnimParts, dataShort) == 24);
static_assert(offsetof(XAnimParts, dataInt) == 32 && offsetof(XAnimParts, randomDataShort) == 40);
static_assert(offsetof(XAnimParts, randomDataByte) == 48 && offsetof(XAnimParts, randomDataInt) == 56);
static_assert(offsetof(XAnimParts, indices) == 64 && offsetof(XAnimParts, notify) == 72);
static_assert(offsetof(XAnimParts, deltaPart) == 80 && offsetof(XAnimParts, randomDataShortCount) == 88);
static_assert(offsetof(XAnimParts, randomDataByteCount) == 92 && offsetof(XAnimParts, indexCount) == 96);
static_assert(offsetof(XAnimParts, framerate) == 100 && offsetof(XAnimParts, frequency) == 104);
static_assert(offsetof(XAnimParts, dataByteCount) == 108 && offsetof(XAnimParts, dataShortCount) == 110);
static_assert(offsetof(XAnimParts, dataIntCount) == 112 && offsetof(XAnimParts, randomDataIntCount) == 114);
static_assert(offsetof(XAnimParts, numframes) == 116 && offsetof(XAnimParts, flags) == 118);
static_assert(offsetof(XAnimParts, boneCount) == 119 && offsetof(XAnimParts, notifyCount) == 129);
static_assert(offsetof(XAnimParts, assetType) == 130 && offsetof(XAnimParts, unk1) == 131);
static_assert(offsetof(XAnimParts, unk2) == 132 && offsetof(XAnimNotifyInfo, time) == 4);
static_assert(sizeof(XAnimDeltaPart) == 24 && sizeof(XAnimPartTrans) == 48);
static_assert(sizeof(XAnimDeltaPartQuat2) == 24 && sizeof(XAnimDeltaPartQuat) == 24);
}
