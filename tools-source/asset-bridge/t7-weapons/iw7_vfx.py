"""Decode and encode ZoneTool IW7 particle systems (.iw7VFX), stdlib only.

The file is the `assetmanager::dumper` stream written by ZoneTool
`vfx::binary::dump` (src/zonetool/zonetool/iw7/assets/particle_system.cpp) and
read back by `vfx::binary::parse`. Each pointer is one token:

* ARRAY  (8): existing u8, then u32 count and count * sizeof(T) raw bytes;
* STRING (6): existing u8, then the bytes and a terminating NUL;
* ASSET  (7): existing u8, then the asset name and a NUL;
* OFFSET (9): u32 entry index, u32 element index: the pointer was already
  written (the dumper keeps one entry per written pointer, [start, start +
  sizeof(T) * (count - 1)], and reuses the first entry containing the new
  range).

Order (mirrors the C++): system (single), name, emitters; per emitter its
states, per state its 3 module groups, per group its modules, per module its
curves / linked assets by module type; then the emitter fade curve; finally
the scripted input nodes.

The decoded model is a JSON-ready dict. Every struct is decoded with the field
names of zonetool/iw7/structs.hpp; bytes that no field covers and that are not
zero are kept in `_gaps` ({"offset": "hex"}). A pointer field that leads to
streamed data becomes two keys: `<field>@ptr` (the original pointer value, as
a hex string) and `<field>` (the decoded children: a list, a name, or None
when the pointer was written as NONEXISTING). Non-finite floats are kept as
`"f32:XXXXXXXX"` bit strings.

The encoder replays the dumper itself: it keeps the dumper's entry table and
writes OFFSET tokens exactly where ZoneTool would, from the pointer values in
the model. A slot whose pointer is 0 but carries data, or whose pointer would
alias different data (after an edit), gets a fresh synthetic pointer so the
written stream stays loadable. Counts (`numEmitters`, `numControlPoints`,
`numAssets`...) are taken from the list lengths.
"""
import argparse
import copy
import json
import math
import os
import re
import struct
import sys
from collections import Counter

FORMAT = "zonetool-iw7-particlesystem"

T_STRING, T_ASSET, T_ARRAY, T_OFFSET = 6, 7, 8, 9

# ---------------------------------------------------------------------------
# Type system (MSVC x64 layout: natural alignment, base class first)


class Arr:
    def __init__(self, elem, count):
        self.elem, self.count = elem, count


class Enum:
    def __init__(self, base, names):
        self.base, self.names = base, names
        self.index = {n: i for i, n in enumerate(names) if n}


class Struct:
    def __init__(self, name, fields, base=None, size=None):
        """`size` fixes the record size of a union member (ParticleModuleDef, ParticleLinkedAssetDef)."""
        self.name = name
        self.members = []
        off = 0
        align = 1
        if base is not None:
            self.members = list(base.members)
            off, align = base.size, base.align
        for fname, spec in fields:
            a = alignof(spec)
            off = (off + a - 1) // a * a
            self.members.append((fname, off, spec))
            off += sizeof(spec)
            align = max(align, a)
        self.align = align
        self.size = (off + align - 1) // align * align
        if size is not None:
            assert size >= self.size, (name, size, self.size)
            self.size = size


PRIMS = {
    "u8": ("<B", 1), "i8": ("<b", 1), "bool": ("<B", 1),
    "u16": ("<H", 2), "i16": ("<h", 2),
    "u32": ("<I", 4), "i32": ("<i", 4),
    "u64": ("<Q", 8), "f32": ("<f", 4), "ptr": ("<Q", 8),
}


def sizeof(spec):
    if isinstance(spec, str):
        return PRIMS[spec][1]
    if isinstance(spec, Enum):
        return PRIMS[spec.base][1]
    if isinstance(spec, Arr):
        return sizeof(spec.elem) * spec.count
    return spec.size


def alignof(spec):
    if isinstance(spec, str):
        return PRIMS[spec][1]
    if isinstance(spec, Enum):
        return PRIMS[spec.base][1]
    if isinstance(spec, Arr):
        return alignof(spec.elem)
    return spec.align


def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def _get(spec, buf, off, cover):
    if isinstance(spec, Struct):
        return {n: _get(s, buf, off + o, cover) for n, o, s in spec.members}
    if isinstance(spec, Arr):
        step = sizeof(spec.elem)
        return [_get(spec.elem, buf, off + i * step, cover) for i in range(spec.count)]
    base = spec.base if isinstance(spec, Enum) else spec
    fmt, size = PRIMS[base]
    for i in range(off, off + size):
        cover[i] = 1
    value = struct.unpack_from(fmt, buf, off)[0]
    if isinstance(spec, Enum):
        return spec.names[value] if value < len(spec.names) and spec.names[value] else value
    if base == "f32":
        if not math.isfinite(value):
            return "f32:%08x" % struct.unpack_from("<I", buf, off)[0]
        return value
    if base == "bool":
        return bool(value) if value in (0, 1) else value
    if base == "ptr":
        return "0x%x" % value
    return value


def _put(spec, value, buf, off, path):
    if isinstance(spec, Struct):
        if not isinstance(value, dict):
            raise ValueError("%s: expected an object for %s" % (path, spec.name))
        for n, o, s in spec.members:
            key = n + "@ptr" if (n + "@ptr") in value else n
            if key not in value:
                raise ValueError("%s: missing field %s" % (path, n))
            _put(s, value[key], buf, off + o, path + "." + n)
        return
    if isinstance(spec, Arr):
        if not isinstance(value, list) or len(value) != spec.count:
            raise ValueError("%s: expected a list of %d" % (path, spec.count))
        step = sizeof(spec.elem)
        for i, v in enumerate(value):
            _put(spec.elem, v, buf, off + i * step, "%s[%d]" % (path, i))
        return
    base = spec.base if isinstance(spec, Enum) else spec
    fmt = PRIMS[base][0]
    if isinstance(spec, Enum) and isinstance(value, str):
        if value not in spec.index:
            raise ValueError("%s: unknown enum value %s" % (path, value))
        value = spec.index[value]
    elif base == "f32" and isinstance(value, str):
        if not value.startswith("f32:"):
            raise ValueError("%s: bad float %r" % (path, value))
        struct.pack_into("<I", buf, off, int(value[4:], 16))
        return
    elif base == "ptr" and isinstance(value, str):
        value = int(value, 16)
    elif base == "ptr" and value is None:
        value = 0
    struct.pack_into(fmt, buf, off, int(value) if base != "f32" else float(value))


def decode_struct(spec, buf, off=0):
    """Decode one struct record; uncovered non-zero bytes go to `_gaps`."""
    cover = bytearray(len(buf))
    out = _get(spec, buf, off, cover)
    gaps = {}
    i, end = off, off + spec.size
    while i < end:
        if not cover[i] and buf[i]:
            j = i
            while j < end and not cover[j] and buf[j]:
                j += 1
            gaps[str(i - off)] = buf[i:j].hex()
            i = j
        else:
            i += 1
    if gaps:
        out["_gaps"] = gaps
    return out


def encode_struct(spec, value, path="struct"):
    buf = bytearray(spec.size)
    _put(spec, value, buf, 0, path)
    for k, h in value.get("_gaps", {}).items():
        raw = bytes.fromhex(h)
        o = int(k)
        buf[o:o + len(raw)] = raw
    return bytes(buf)


# ---------------------------------------------------------------------------
# IW7 particle structs (zonetool/iw7/structs.hpp)

MODULE_TYPES = [
    "PARTICLE_MODULE_INIT_ATLAS", "PARTICLE_MODULE_INIT_ATTRIBUTES",
    "PARTICLE_MODULE_INIT_BEAM", "PARTICLE_MODULE_INIT_CAMERA_OFFSET",
    "PARTICLE_MODULE_INIT_CLOUD", "PARTICLE_MODULE_INIT_DECAL",
    "PARTICLE_MODULE_INIT_FLARE", "PARTICLE_MODULE_INIT_GEO_TRAIL",
    "PARTICLE_MODULE_INIT_LIGHT_OMNI", "PARTICLE_MODULE_INIT_LIGHT_SPOT",
    "PARTICLE_MODULE_INIT_MATERIAL", "PARTICLE_MODULE_INIT_MIRROR_TEXTURE",
    "PARTICLE_MODULE_INIT_MODEL", "PARTICLE_MODULE_INIT_OCCLUSION_QUERY",
    "PARTICLE_MODULE_INIT_ORIENTED_SPRITE", "PARTICLE_MODULE_INIT_PARTICLE_SIM",
    "PARTICLE_MODULE_INIT_PLAYER_FACING", "PARTICLE_MODULE_INIT_RELATIVE_VELOCITY",
    "PARTICLE_MODULE_INIT_ROTATION", "PARTICLE_MODULE_INIT_ROTATION_3D",
    "PARTICLE_MODULE_INIT_RUNNER", "PARTICLE_MODULE_INIT_SOUND",
    "PARTICLE_MODULE_INIT_SPAWN", "PARTICLE_MODULE_INIT_SPAWN_SHAPE_BOX",
    "PARTICLE_MODULE_INIT_SPAWN_SHAPE_CYLINDER", "PARTICLE_MODULE_INIT_SPAWN_SHAPE_ELLIPSOID",
    "PARTICLE_MODULE_INIT_SPAWN_SHAPE_MESH", "PARTICLE_MODULE_INIT_SPAWN_SHAPE_SPHERE",
    "PARTICLE_MODULE_INIT_TAIL", "PARTICLE_MODULE_INIT_VECTOR_FIELD",
    "PARTICLE_MODULE_INIT_VOLUMETRIC", "PARTICLE_MODULE_ATTRACTOR",
    "PARTICLE_MODULE_COLOR_GRAPH", "PARTICLE_MODULE_COLOR_LERP",
    "PARTICLE_MODULE_EMISSION_GRAPH", "PARTICLE_MODULE_EMISSIVE_GRAPH",
    "PARTICLE_MODULE_FORCE", "PARTICLE_MODULE_GRAVITY",
    "PARTICLE_MODULE_INTENSITY_GRAPH", "PARTICLE_MODULE_PARENT_VELOCITY_GRAPH",
    "PARTICLE_MODULE_PHYSICS_LIGHT", "PARTICLE_MODULE_PHYSICS_RAY_CAST",
    "PARTICLE_MODULE_POSITION_GRAPH", "PARTICLE_MODULE_ROTATION_GRAPH",
    "PARTICLE_MODULE_ROTATION_GRAPH_3D", "PARTICLE_MODULE_SIZE_GRAPH",
    "PARTICLE_MODULE_SIZE_LERP", "PARTICLE_MODULE_VELOCITY_GRAPH",
    "PARTICLE_MODULE_TEST_AGE", "PARTICLE_MODULE_TEST_BIRTH",
    "PARTICLE_MODULE_TEST_DEATH", "PARTICLE_MODULE_TEST_GRAVITY",
    "PARTICLE_MODULE_TEST_IMPACT", "PARTICLE_MODULE_TEST_POS",
]
MT = {n: i for i, n in enumerate(MODULE_TYPES)}

ELEMENT_TYPES = [
    "PARTICLE_ELEMENT_TYPE_BILLBOARD_SPRITE", "PARTICLE_ELEMENT_TYPE_BEAM",
    "PARTICLE_ELEMENT_TYPE_CLOUD", "PARTICLE_ELEMENT_TYPE_SPARK_CLOUD",
    "PARTICLE_ELEMENT_TYPE_DECAL", "PARTICLE_ELEMENT_TYPE_FLARE",
    "PARTICLE_ELEMENT_TYPE_GEO_TRAIL", "PARTICLE_ELEMENT_TYPE_LIGHT_OMNI",
    "PARTICLE_ELEMENT_TYPE_LIGHT_SPOT", "PARTICLE_ELEMENT_TYPE_MODEL",
    "PARTICLE_ELEMENT_TYPE_ORIENTED_SPRITE", "PARTICLE_ELEMENT_TYPE_RUNNER",
    "PARTICLE_ELEMENT_TYPE_TAIL", "PARTICLE_ELEMENT_TYPE_VECTOR_FIELD",
    "PARTICLE_ELEMENT_TYPE_VOLUMETRIC",
]
MODULE_GROUPS = ["PARTICLE_MODULE_GROUP_INIT", "PARTICLE_MODULE_GROUP_UPDATE",
                 "PARTICLE_MODULE_GROUP_TEST"]

MODTYPE16 = Enum("u16", MODULE_TYPES)
ELEMTYPE32 = Enum("u32", ELEMENT_TYPES)

F4 = Arr("f32", 4)
FRANGE = Struct("ParticleFloatRange", [("min", "f32"), ("max", "f32")])
IRANGE = Struct("ParticleIntRange", [("min", "i32"), ("max", "i32")])
BOUNDS = Struct("Bounds", [("midPoint", Arr("f32", 3)), ("halfSize", Arr("f32", 3))])
CONTROL_POINT = Struct("ParticleCurveControlPointDef", [
    ("time", "f32"), ("value", "f32"), ("invTimeDelta", "f32"), ("pad", Arr("u32", 1))])
CURVE = Struct("ParticleCurveDef", [
    ("controlPoints", "ptr"), ("numControlPoints", "i32"), ("scale", "f32")])
LINKED_LIST = Struct("ParticleLinkedAssetListDef", [("assetList", "ptr"), ("numAssets", "i32")])
MODULE = Struct("ParticleModule", [("type", MODTYPE16), ("m_flags", "u32")])


def _m(name, fields, base=MODULE):
    return Struct(name, fields, base)


def _pad(n, t="u32"):
    return ("m_pad", Arr(t, n))


SPAWN_SHAPE = _m("ParticleModuleInitSpawnShape", [
    ("m_axisFlags", "i8"), ("m_spawnFlags", "i8"), ("m_normalAxis", "i8"), ("m_spawnType", "i8"),
    ("m_volumeCubeRoot", "f32"), ("m_offset", F4)])
EVENT_HANDLER = Struct("ParticleModuleTestEventHandlerData", [
    ("m_nextState", "u32"), ("m_linkedAssetList", LINKED_LIST), ("m_kill", "bool"),
    ("m_pad", Arr("u32", 1))])
MODULE_TEST = _m("ParticleModuleTest", [
    ("m_moduleIndex", "u16"), ("m_useOrientationOptions", Arr("i8", 1)),
    ("m_useScaleOptions", Arr("i8", 1)), ("m_useVelocityOptions", Arr("i8", 1)),
    ("m_eventHandlerData", EVENT_HANDLER)])
SPAWN_MESH_ASSET = Struct("ParticleSpawnMeshAssetDef", [
    ("m_numVertsTotal", "u32"), ("m_numTrisTotal", "u32"), ("m_pad", Arr("u32", 2))])

LL = ("m_linkedAssetList", LINKED_LIST)
EVT_LL = "m_eventHandlerData.m_linkedAssetList"

# module type -> (union member, struct, expected size, curves field, curve count, linked list path)
MODULE_DEFS = {
    MT["PARTICLE_MODULE_INIT_ATLAS"]: ("initAtlas", _m("ParticleModuleInitAtlas", [
        ("m_playRate", "i32"), ("m_startFrame", "i32"), ("m_loopCount", "i32")]), 20, None, 0, None),
    MT["PARTICLE_MODULE_INIT_ATTRIBUTES"]: ("initAttributes", _m("ParticleModuleInitAttributes", [
        ("m_useNonUniformInterpolationForColor", "bool"), ("m_useNonUniformInterpolationForSize", "bool"),
        _pad(6, "i8"), ("m_sizeMin", F4), ("m_sizeMax", F4), ("m_colorMin", F4), ("m_colorMax", F4),
        ("m_velocityMin", F4), ("m_velocityMax", F4)]), 112, None, 0, None),
    MT["PARTICLE_MODULE_INIT_BEAM"]: ("initBeam", _m("ParticleModuleInitBeam", [
        ("m_beamFlags", "u32"), ("m_splitDistance", "f32"), ("m_startPos", F4), ("m_endPos", F4),
        ("m_offset", F4), ("m_curvePoint1", F4), ("m_curvePoint2", F4), LL,
        ("m_scrollRateUV", "f32"), ("m_scrollRateSpiralGraph", "f32"),
        ("m_spiralRepeatDistance", "f32")]), 128, None, 0, "m_linkedAssetList"),
    MT["PARTICLE_MODULE_INIT_CAMERA_OFFSET"]: ("initCameraOffset", _m(
        "ParticleModuleInitCameraOffset", [_pad(2)]), 16, None, 0, None),
    MT["PARTICLE_MODULE_INIT_CLOUD"]: ("initCloud", _m("ParticleModuleInitCloud", [
        _pad(2), ("curves", Arr(CURVE, 2))]), 48, "curves", 2, None),
    MT["PARTICLE_MODULE_INIT_DECAL"]: ("initDecal", _m("ParticleModuleInitDecal", [
        ("m_fadeInTime", "u16"), ("m_fadeOutTime", "u16"), ("m_stoppableFadeOutTime", "u16"),
        ("m_lerpWaitTime", "u16"), ("m_lerpColor", F4), LL]), 48, None, 0, "m_linkedAssetList"),
    MT["PARTICLE_MODULE_INIT_FLARE"]: ("initFlare", _m("ParticleModuleInitFlare", [
        _pad(1), ("m_position", "f32"), ("m_direction", F4), ("m_angularRotCount", "i32"),
        ("m_flareFlags", "u32"), ("m_depthScaleRange", FRANGE), ("m_depthScaleValue", FRANGE),
        ("m_radialRot", FRANGE), ("m_radialScaleX", FRANGE), ("m_radialScaleY", FRANGE),
        ("m_curves", Arr(CURVE, 4))]), 144, "m_curves", 4, None),
    MT["PARTICLE_MODULE_INIT_GEO_TRAIL"]: ("initGeoTrail", _m("ParticleModuleInitGeoTrail", [
        ("m_numPointsMax", "u32"), ("m_splitDistance", "f32"), ("m_splitAngle", "f32"),
        ("m_centerOffset", "f32"), ("m_numSheets", "u32"), ("m_fadeInDistance", "f32"),
        ("m_fadeOutDistance", "f32"), ("m_tileDistance", "f32"), ("m_tileOffset", FRANGE),
        ("m_scrollTime", "f32"), ("m_useLocalVelocity", "bool"), ("m_useVerticalTexture", "bool"),
        ("m_cameraFacing", "bool"), ("m_fixLeadingEdge", "bool"), ("m_clampUVs", "bool"),
        _pad(3, "i8"), ("m_pad2", Arr("u32", 1))]), 64, None, 0, None),
    MT["PARTICLE_MODULE_INIT_LIGHT_OMNI"]: ("initLightOmni", _m("ParticleModuleInitLightOmni", [
        LL, ("m_tonemappingScaleFactor", "f32"), ("m_intensityIR", "f32"),
        ("m_disableVolumetric", "bool"), ("m_exponent", "u8"), ("__pad0", Arr("i8", 2)),
        ("m_shadowSoftness", "f32"), ("m_shadowBias", "f32"), ("m_shadowArea", "f32")]),
        48, None, 0, "m_linkedAssetList"),
    MT["PARTICLE_MODULE_INIT_LIGHT_SPOT"]: ("initLightSpot", _m("ParticleModuleInitLightSpot", [
        ("m_fovOuter", "f32"), ("m_fovInner", "f32"), ("m_bulbRadius", "f32"), ("m_bulbLength", "f32"),
        ("m_brightness", "f32"), ("unk1", "f32"), ("m_intensityUV", "f32"), ("m_intensityIR", "f32"),
        ("m_shadowNearPlane", "f32"), ("m_toneMappingScaleFactor", "f32"), ("m_shadowSoftness", "f32"),
        ("m_shadowBias", "f32"), ("m_shadowArea", "f32"), ("m_disableVolumetric", "bool"),
        ("m_disableShadowMap", "bool"), ("m_disableDynamicShadows", "bool"), ("m_exponent", "bool"),
        LL]), 80, None, 0, "m_linkedAssetList"),
    MT["PARTICLE_MODULE_INIT_MATERIAL"]: ("initMaterial", _m("ParticleModuleInitMaterial", [
        _pad(2), LL]), 32, None, 0, "m_linkedAssetList"),
    MT["PARTICLE_MODULE_INIT_MIRROR_TEXTURE"]: ("initMirrorTexture", _m("ParticleModuleInitMirrorTexture", [
        ("m_mirrorHorizontal", "u32"), ("m_mirrorVertical", "u32")]), 16, None, 0, None),
    MT["PARTICLE_MODULE_INIT_MODEL"]: ("initModel", _m("ParticleModuleInitModel", [
        ("m_usePhysics", "bool"), ("m_motionBlurHQ", "bool"), LL]), 32, None, 0, "m_linkedAssetList"),
    MT["PARTICLE_MODULE_INIT_OCCLUSION_QUERY"]: ("initOcclusionQuery", _m("ParticleModuleInitOcclusionQuery", [
        ("m_fadeInTime", "f32"), ("m_fadeOutTime", "f32"), ("m_scale", FRANGE),
        ("m_worldSize", Arr("f32", 2))]), 32, None, 0, None),
    MT["PARTICLE_MODULE_INIT_ORIENTED_SPRITE"]: ("initOrientedSprite", _m("ParticleModuleInitOrientedSprite", [
        _pad(2), ("m_orientationQuat", F4)]), 32, None, 0, None),
    MT["PARTICLE_MODULE_INIT_PARTICLE_SIM"]: ("initParticleSim", _m("ParticleModuleInitParticleSim", [
        LL, ("m_scaleFactor", FRANGE), ("m_holdLastFrame", "bool"), _pad(3)]),
        48, None, 0, "m_linkedAssetList"),
    MT["PARTICLE_MODULE_INIT_PLAYER_FACING"]: ("initPlayerFacing", _m(
        "ParticleModuleInitPlayerFacing", [_pad(2)]), 16, None, 0, None),
    MT["PARTICLE_MODULE_INIT_RELATIVE_VELOCITY"]: ("initRelativeVelocity", _m(
        "ParticleModuleInitRelativeVelocity", [("m_velocityType", "u32"), ("m_useBoltInfo", "bool")]),
        16, None, 0, None),
    MT["PARTICLE_MODULE_INIT_ROTATION"]: ("initRotation", _m("ParticleModuleInitRotation", [
        _pad(2), ("m_rotationAngle", FRANGE), ("m_rotationRate", FRANGE)]), 32, None, 0, None),
    MT["PARTICLE_MODULE_INIT_ROTATION_3D"]: ("initRotation3D", _m("ParticleModuleInitRotation3D", [
        _pad(2), ("m_rotationAngleMin", F4), ("m_rotationAngleMax", F4), ("m_rotationRateMin", F4),
        ("m_rotationRateMax", F4)]), 80, None, 0, None),
    MT["PARTICLE_MODULE_INIT_RUNNER"]: ("initRunner", _m("ParticleModuleInitRunner", [
        _pad(2), LL]), 32, None, 0, "m_linkedAssetList"),
    MT["PARTICLE_MODULE_INIT_SOUND"]: ("initSound", _m("ParticleModuleInitSound", [
        _pad(2), LL]), 32, None, 0, "m_linkedAssetList"),
    MT["PARTICLE_MODULE_INIT_SPAWN"]: ("initSpawn", _m("ParticleModuleInitSpawn", [
        _pad(2), ("m_curves", Arr(CURVE, 1))]), 32, "m_curves", 1, None),
    MT["PARTICLE_MODULE_INIT_SPAWN_SHAPE_BOX"]: ("initSpawnShapeBox", _m("ParticleModuleInitSpawnShapeBox", [
        ("m_useBeamInfo", "bool"), _pad(15, "i8"), ("m_dimensionsMin", F4), ("m_dimensionsMax", F4)],
        SPAWN_SHAPE), 80, None, 0, None),
    MT["PARTICLE_MODULE_INIT_SPAWN_SHAPE_CYLINDER"]: ("initSpawnShapeCylinder", _m(
        "ParticleModuleInitSpawnShapeCylinder", [
            ("m_hasRotation", "bool"), ("m_rotateCalculatedOffset", "bool"), ("m_halfHeight", "f32"),
            ("m_radius", FRANGE), ("unk", F4), ("m_directionQuat", F4)], SPAWN_SHAPE), 80, None, 0, None),
    MT["PARTICLE_MODULE_INIT_SPAWN_SHAPE_ELLIPSOID"]: ("initSpawnShapeEllipsoid", _m(
        "ParticleModuleInitSpawnShapeEllipsoid", [
            ("m_radiusMin", F4), ("m_radiusMax", F4), _pad(4)], SPAWN_SHAPE), 80, None, 0, None),
    MT["PARTICLE_MODULE_INIT_SPAWN_SHAPE_MESH"]: ("initSpawnShapeMesh", _m(
        "ParticleModuleInitSpawnShapeMesh", [
            ("m_numMeshAssets", "u32"), LL, ("m_meshAssetData", "ptr"), _pad(3)], SPAWN_SHAPE),
        80, None, 0, "m_linkedAssetList"),
    MT["PARTICLE_MODULE_INIT_SPAWN_SHAPE_SPHERE"]: ("initSpawnShapeSphere", _m(
        "ParticleModuleInitSpawnShapeSphere", [
            _pad(2), ("m_radius", FRANGE), ("m_offset2", F4)], SPAWN_SHAPE), 64, None, 0, None),
    MT["PARTICLE_MODULE_INIT_TAIL"]: ("initTail", _m("ParticleModuleInitTail", [
        ("m_averagePastVelocities", "u16"), ("m_maxParentSpeed", "u16"), ("m_tailLeading", "bool"),
        ("m_scaleWithVelocity", "bool"), ("m_rotateAroundPivot", "bool")]), 16, None, 0, None),
    MT["PARTICLE_MODULE_INIT_VECTOR_FIELD"]: ("initVectorField", _m("ParticleModuleInitVectorField", [
        _pad(2), LL]), 32, None, 0, "m_linkedAssetList"),
    MT["PARTICLE_MODULE_INIT_VOLUMETRIC"]: ("initVolumetric", _m("ParticleModuleInitVolumetric", [
        ("m_density", "f32"), ("m_falloff", "f32"), ("m_noiseAmplitude", "f32"), ("m_noiseMode", "u32"),
        _pad(2)]), 32, None, 0, None),
    MT["PARTICLE_MODULE_ATTRACTOR"]: ("attractor", _m("ParticleModuleAttractor", [
        _pad(3), ("m_killWhenNear", "bool"), ("m_forceMag", "f32"), ("m_nearDistanceSq", "f32"),
        ("m_attractPoint", F4)]), 48, None, 0, None),
    MT["PARTICLE_MODULE_COLOR_GRAPH"]: ("colorGraph", _m("ParticleModuleColorGraph", [
        ("firstCurve", "bool"), _pad(3, "i8"), ("m_modulateColorByAlpha", "bool"),
        ("m_curves", Arr(CURVE, 8))]), 144, "m_curves", 8, None),
    MT["PARTICLE_MODULE_COLOR_LERP"]: ("colorLerp", _m("ParticleModuleColorLerp", [
        _pad(2), ("m_colorBegin", F4), ("m_colorEnd", F4)]), 48, None, 0, None),
    MT["PARTICLE_MODULE_EMISSION_GRAPH"]: ("emissionGraph", _m("ParticleModuleEmissionGraph", [
        _pad(2), ("m_curves", Arr(CURVE, 2))]), 48, "m_curves", 2, None),
    MT["PARTICLE_MODULE_EMISSIVE_GRAPH"]: ("emissiveGraph", _m("ParticleModuleEmissiveGraph", [
        ("firstCurve", "bool"), _pad(7, "i8"), ("m_curves", Arr(CURVE, 2))]), 48, "m_curves", 2, None),
    MT["PARTICLE_MODULE_FORCE"]: ("force", _m("ParticleModuleForce", [
        _pad(2), ("m_forceMin", F4), ("m_forceMax", F4)]), 48, None, 0, None),
    MT["PARTICLE_MODULE_GRAVITY"]: ("gravity", _m("ParticleModuleGravity", [
        ("m_gravityPercentage", FRANGE)]), 16, None, 0, None),
    MT["PARTICLE_MODULE_INTENSITY_GRAPH"]: ("intensityGraph", _m("ParticleModuleIntensityGraph", [
        ("firstCurve", "bool"), _pad(7, "i8"), ("m_curves", Arr(CURVE, 2))]), 48, "m_curves", 2, None),
    MT["PARTICLE_MODULE_PARENT_VELOCITY_GRAPH"]: ("parentVelocityGraph", _m(
        "ParticleModuleParentVelocityGraph", [_pad(2), ("m_curves", Arr(CURVE, 2))]),
        48, "m_curves", 2, None),
    MT["PARTICLE_MODULE_PHYSICS_LIGHT"]: ("physicsLight", _m("ParticleModulePhysicsLight", [
        ("m_ignoreEmitterOrientation", "bool"), ("m_useSurfaceType", "bool"), _pad(6, "i8"), LL]),
        32, None, 0, "m_linkedAssetList"),
    MT["PARTICLE_MODULE_PHYSICS_RAY_CAST"]: ("physicsRayCast", _m("ParticleModulePhysicsRayCast", [
        ("m_bounce", FRANGE), ("m_bounds", BOUNDS), ("m_useItemClip", "bool"), ("m_useSurfaceType", "bool"),
        ("m_collideWithWater", "bool"), ("m_ignoreContentItem", "bool"), _pad(3, "i8")]), 48, None, 0, None),
    MT["PARTICLE_MODULE_POSITION_GRAPH"]: ("positionGraph", _m("ParticleModulePositionGraph", [
        _pad(2), ("m_curves", Arr(CURVE, 6))]), 112, "m_curves", 6, None),
    MT["PARTICLE_MODULE_ROTATION_GRAPH"]: ("rotationGraph", _m("ParticleModuleRotationGraph", [
        ("m_useRotationRate", "bool"), _pad(1), ("m_curves", Arr(CURVE, 2))]), 48, "m_curves", 2, None),
    MT["PARTICLE_MODULE_ROTATION_GRAPH_3D"]: ("rotationGraph3D", _m("ParticleModuleRotationGraph3D", [
        ("m_useRotationRate", "bool"), _pad(1), ("m_curves", Arr(CURVE, 6))]), 112, "m_curves", 6, None),
    MT["PARTICLE_MODULE_SIZE_GRAPH"]: ("sizeGraph", _m("ParticleModuleSizeGraph", [
        ("firstCurve", "bool"), _pad(7, "i8"), ("m_curves", Arr(CURVE, 6)), ("m_sizeBegin", F4),
        ("m_sizeEnd", F4)]), 144, "m_curves", 6, None),
    MT["PARTICLE_MODULE_SIZE_LERP"]: ("sizeLerp", _m("ParticleModuleSizeLerp", [
        _pad(2), ("m_sizeBegin", F4), ("m_sizeEnd", F4)]), 48, None, 0, None),
    MT["PARTICLE_MODULE_VELOCITY_GRAPH"]: ("velocityGraph", _m("ParticleModuleVelocityGraph", [
        _pad(2), ("m_curves", Arr(CURVE, 6)), ("m_velocityBegin", F4), ("m_velocityEnd", F4)]),
        144, "m_curves", 6, None),
    MT["PARTICLE_MODULE_TEST_AGE"]: ("testAge", _m("ParticleModuleTestAge", [("m_age", "f32")], MODULE_TEST),
                                     56, None, 0, EVT_LL),
    MT["PARTICLE_MODULE_TEST_BIRTH"]: ("testBirth", MODULE_TEST, 48, None, 0, EVT_LL),
    MT["PARTICLE_MODULE_TEST_DEATH"]: ("testDeath", MODULE_TEST, 48, None, 0, EVT_LL),
    MT["PARTICLE_MODULE_TEST_GRAVITY"]: ("testGravity", MODULE_TEST, 48, None, 0, EVT_LL),
    MT["PARTICLE_MODULE_TEST_IMPACT"]: ("testImpact", MODULE_TEST, 48, None, 0, EVT_LL),
    MT["PARTICLE_MODULE_TEST_POS"]: ("testPos", MODULE_TEST, 48, None, 0, EVT_LL),
}

MODULE_DATA_SIZE = 144

# ParticleLinkedAssetDef (32-byte union) by the parent module type:
# (struct of the active member, [(field, "asset"|"string", asset size)])
_PTR = "ptr"


LINKED_ASSET_SIZE = 32
MODULE_DEF_SIZE = 160
ASSET_SIZES = {"material": 0x118, "model": 0x2E0, "particleSystem": 0x80, "lightDef": 0x28,
               "vectorField": 48, "physicsFXPipeline": 0x20, "physicsFXShape": 0x18}


def _la_sized(fields):
    st = Struct("ParticleLinkedAssetDef", [(f, _PTR) for f, _ in fields], size=LINKED_ASSET_SIZE)
    return st, [(f, kind, ASSET_SIZES.get(f.rstrip("012"), 8)) for f, kind in fields]


_LA_PSYS = _la_sized([("particleSystem", "asset")])
LINKED_ASSET_DEFS = {
    MT["PARTICLE_MODULE_INIT_MATERIAL"]: _la_sized([("material", "asset")]),
    MT["PARTICLE_MODULE_INIT_MODEL"]: _la_sized([("model", "asset")]),
    MT["PARTICLE_MODULE_INIT_SPAWN_SHAPE_MESH"]: _la_sized([("model", "asset")]),
    MT["PARTICLE_MODULE_PHYSICS_LIGHT"]: _la_sized([("physicsFXPipeline", "asset"),
                                                    ("physicsFXShape", "asset")]),
    MT["PARTICLE_MODULE_INIT_PARTICLE_SIM"]: _la_sized([("particleSim", "asset")]),
    MT["PARTICLE_MODULE_INIT_DECAL"]: _la_sized([("material0", "asset"), ("material1", "asset"),
                                                 ("material2", "asset")]),
    MT["PARTICLE_MODULE_INIT_SOUND"]: _la_sized([("sound", "string")]),
    MT["PARTICLE_MODULE_INIT_VECTOR_FIELD"]: _la_sized([("vectorField", "asset")]),
    MT["PARTICLE_MODULE_INIT_LIGHT_OMNI"]: _la_sized([("lightDef", "asset")]),
    MT["PARTICLE_MODULE_INIT_LIGHT_SPOT"]: _la_sized([("lightDef", "asset")]),
}
for _t in ("INIT_BEAM", "INIT_RUNNER", "TEST_AGE", "TEST_BIRTH", "TEST_DEATH", "TEST_GRAVITY",
           "TEST_IMPACT", "TEST_POS"):
    LINKED_ASSET_DEFS[MT["PARTICLE_MODULE_" + _t]] = _LA_PSYS

MODULE_GROUP = Struct("ParticleModuleGroupDef", [
    ("moduleDefs", "ptr"), ("numModules", "i32"), ("disabled", "bool")])
STATE = Struct("ParticleStateDef", [
    ("moduleGroupDefs", "ptr"), ("elementType", ELEMTYPE32), ("flags", "u64"), ("pad", Arr("u32", 2))])
EMITTER = Struct("ParticleEmitterDef", [
    ("stateDefs", "ptr"), ("numStates", "i32"), ("particleSpawnRate", FRANGE), ("particleLife", FRANGE),
    ("particleDelay", FRANGE), ("particleCountMax", "u32"), ("particleBurstCount", IRANGE),
    ("emitterLife", FRANGE), ("emitterDelay", FRANGE), ("randomSeed", "i32"), ("spawnRangeSq", FRANGE),
    ("fadeOutMaxDistance", "f32"), ("fadeCurveDef", CURVE), ("spawnFrustumCullRadius", "f32"),
    ("flags", "u32"), ("gravityOptions", "u32"), ("groupIDs", Arr("i32", 4)), ("unk1", "f32"),
    ("unk2", "f32"), ("particleSpawnShapeRange", FRANGE), ("pad", Arr("u32", 1))])
SCRIPTED_INPUT_NODE = Struct("ParticleScriptedInputNodeDef", [
    ("m_type", "u32"), ("m_flags", "u32"), ("m_emitterIndex", "u32"), ("m_pad", Arr("u32", 5)),
    ("m_inputRecord", Struct("ParticleScriptedInputRecord", [
        ("key", "u32"), ("dirty", "bool"), ("value", "bool"), ("pad", Arr("u32", 2))]))])
SYSTEM = Struct("ParticleSystemDef", [
    ("name", "ptr"), ("emitterDefs", "ptr"), ("scriptedInputNodeDefs", "ptr"), ("version", "i32"),
    ("numEmitters", "i32"), ("numScriptedInputNodes", "i32"), ("flags", "u32"),
    ("occlusionOverrideEmitterIndex", "i32"), ("phaseOptions", "u32"), ("drawFrustumCullRadius", "f32"),
    ("updateFrustumCullRadius", "f32"), ("sunDistance", "f32"), ("preRollMSec", "i32"),
    ("editorPosition", F4), ("editorRotation", F4), ("gameTweakPosition", F4),
    ("gameTweakRotation", F4)])

_MODULE_DEF_CACHE = {}


def module_def_struct(module_type):
    """ParticleModuleDef with the union member selected by moduleType."""
    if module_type not in _MODULE_DEF_CACHE:
        member = MODULE_DEFS.get(module_type)
        data_name, data_struct = (member[0], member[1]) if member else ("moduleBase", MODULE)
        _MODULE_DEF_CACHE[module_type] = Struct("ParticleModuleDef", [
            ("moduleType", MODTYPE16), ("m_pad", Arr("u32", 3)), (data_name, data_struct)], size=MODULE_DEF_SIZE)
    return _MODULE_DEF_CACHE[module_type]


def _check_layouts():
    expect = [(SYSTEM, 0x80), (EMITTER, 144), (STATE, 32), (MODULE_GROUP, 16), (CONTROL_POINT, 16),
              (CURVE, 16), (LINKED_LIST, 16), (SCRIPTED_INPUT_NODE, 48), (SPAWN_MESH_ASSET, 16),
              (MODULE_TEST, 48), (SPAWN_SHAPE, 32), (module_def_struct(MT["PARTICLE_MODULE_COLOR_GRAPH"]), 160)]
    for st, size in expect:
        assert st.size == size, (st.name, st.size, size)
    for mt, (_, st, size, *_rest) in MODULE_DEFS.items():
        assert st.size == size and size <= MODULE_DATA_SIZE, (MODULE_TYPES[mt], st.size, size)
    assert dict((n, o) for n, o, _ in MODULE_DEFS[MT["PARTICLE_MODULE_INIT_FLARE"]][1].members)["m_curves"] == 80
    assert dict((n, o) for n, o, _ in MODULE_DEFS[MT["PARTICLE_MODULE_INIT_LIGHT_SPOT"]][1].members)[
        "m_linkedAssetList"] == 64
    assert dict((n, o) for n, o, _ in MODULE_DEFS[MT["PARTICLE_MODULE_INIT_SPAWN_SHAPE_MESH"]][1].members)[
        "m_numMeshAssets"] == 32


_check_layouts()


# ---------------------------------------------------------------------------
# Reader (mirrors assetmanager::reader)


class FormatError(ValueError):
    pass


class _Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.entries = []      # (kind, blob) in read order
        self.root_refs = []    # (slot pointer, element index, element size) of offsets to entry 0

    def _take(self, n):
        if self.pos + n > len(self.data):
            raise FormatError("truncated at 0x%x (need %d bytes)" % (self.pos, n))
        b = self.data[self.pos:self.pos + n]
        self.pos += n
        return b

    def _u8(self):
        return self._take(1)[0]

    def _u32(self):
        return struct.unpack("<I", self._take(4))[0]

    def _cstr(self):
        end = self.data.find(b"\0", self.pos)
        if end < 0:
            raise FormatError("unterminated string at 0x%x" % self.pos)
        s = self.data[self.pos:end]
        self.pos = end + 1
        return s

    def _offset(self, slot_ptr, elem_size):
        index, element = self._u32(), self._u32()
        if index >= len(self.entries):
            raise FormatError("offset to entry %d of %d at 0x%x" % (index, len(self.entries), self.pos))
        if index == 0:
            self.root_refs.append((slot_ptr, element, elem_size))
        return self.entries[index], element

    def string(self, slot_ptr):
        at = self.pos
        t = self._u8()
        if t == T_STRING:
            if self._u8() == 0:
                return None
            s = self._cstr()
            self.entries.append(("string", s + b"\0"))
            return s.decode("latin-1")
        if t == T_OFFSET:
            (kind, blob), element = self._offset(slot_ptr, 1)
            end = blob.find(b"\0", element)
            if end < 0:
                raise FormatError("string offset into a %s entry without NUL at 0x%x" % (kind, at))
            return blob[element:end].decode("latin-1")
        raise FormatError("expected STRING/OFFSET, got %d at 0x%x" % (t, at))

    def asset(self, slot_ptr, asset_size):
        at = self.pos
        t = self._u8()
        if t == T_ASSET:
            if self._u8() == 0:
                return None
            s = self._cstr()
            self.entries.append(("asset", s))
            return s.decode("latin-1")
        if t == T_OFFSET:
            (kind, blob), element = self._offset(slot_ptr, asset_size)
            if kind != "asset" or element != 0:
                raise FormatError("asset offset into a %s entry (element %d) at 0x%x" % (kind, element, at))
            return blob.decode("latin-1")
        raise FormatError("expected ASSET/OFFSET, got %d at 0x%x" % (t, at))

    def array(self, slot_ptr, elem_size, expected):
        """Returns the raw element bytes (None for NONEXISTING)."""
        at = self.pos
        t = self._u8()
        if t == T_ARRAY:
            if self._u8() == 0:
                return None
            count = self._u32()
            if count == 0:
                return None
            blob = self._take(count * elem_size)
            if count != expected:
                raise FormatError("array of %d where the struct counts %d at 0x%x" % (count, expected, at))
            self.entries.append(("array", blob))
            return blob
        if t == T_OFFSET:
            (kind, blob), element = self._offset(slot_ptr, elem_size)
            start = element * elem_size
            region = blob[start:start + expected * elem_size]
            if len(region) != expected * elem_size:
                raise FormatError("array offset past its %s entry at 0x%x" % (kind, at))
            return region
        raise FormatError("expected ARRAY/OFFSET, got %d at 0x%x" % (t, at))


def _ptr(value):
    if value is None:
        return 0
    return int(value, 16) if isinstance(value, str) else int(value)


def _attach(d, key, value):
    """Replace pointer field `key` by `key@ptr` (pointer) + `key` (children), in place, keeping order."""
    items = list(d.items())
    d.clear()
    for k, v in items:
        if k == key:
            d[key + "@ptr"] = v
            d[key] = value
        else:
            d[k] = v


def _path_get(d, path):
    for p in path.split("."):
        d = d[p]
    return d


def _elements(blob, spec):
    return [decode_struct(spec, blob[i:i + spec.size]) for i in range(0, len(blob), spec.size)]


def _read_curve(r, curve):
    blob = r.array(_ptr(curve["controlPoints"]), CONTROL_POINT.size, curve["numControlPoints"])
    _attach(curve, "controlPoints", None if blob is None else _elements(blob, CONTROL_POINT))


def _read_linked_list(r, ll, module_type):
    blob = r.array(_ptr(ll["assetList"]), LINKED_ASSET_SIZE, ll["numAssets"])
    assets = None
    if blob is not None:
        if module_type not in LINKED_ASSET_DEFS:
            raise FormatError("linked assets under module type %r" % module_type)
        spec, slots = LINKED_ASSET_DEFS[module_type]
        assets = _elements(blob, spec)
        for a in assets:
            for field, kind, size in slots:
                p = _ptr(a[field])
                _attach(a, field, r.string(p) if kind == "string" else r.asset(p, size))
    _attach(ll, "assetList", assets)


def _read_module(r, module):
    mt = module["moduleType"]
    mt = MT[mt] if isinstance(mt, str) else mt
    member = MODULE_DEFS.get(mt)
    if member is None:
        return
    data_name, _, _, curves_field, curve_count, ll_path = member
    data = module[data_name]
    if curves_field:
        for i in range(curve_count):
            _read_curve(r, data[curves_field][i])
    if ll_path:
        _read_linked_list(r, _path_get(data, ll_path), mt)
    if mt == MT["PARTICLE_MODULE_INIT_SPAWN_SHAPE_MESH"]:
        blob = r.array(_ptr(data["m_meshAssetData"]), SPAWN_MESH_ASSET.size, data["m_numMeshAssets"])
        _attach(data, "m_meshAssetData", None if blob is None else _elements(blob, SPAWN_MESH_ASSET))


def _decode_modules(blob):
    out = []
    for i in range(0, len(blob), MODULE_DEF_SIZE):
        raw = blob[i:i + MODULE_DEF_SIZE]
        out.append(decode_struct(module_def_struct(struct.unpack_from("<H", raw, 0)[0]), raw))
    return out


def decode(data):
    """Decode an .iw7VFX byte string into the JSON-ready model."""
    r = _Reader(bytes(data))
    blob = r.array(None, SYSTEM.size, 1)
    if blob is None:
        raise FormatError("missing ParticleSystemDef")
    system = decode_struct(SYSTEM, blob)
    _attach(system, "name", r.string(_ptr(system["name"])))

    blob = r.array(_ptr(system["emitterDefs"]), EMITTER.size, system["numEmitters"])
    emitters = None if blob is None else _elements(blob, EMITTER)
    for e in emitters or []:
        blob = r.array(_ptr(e["stateDefs"]), STATE.size, e["numStates"])
        states = None if blob is None else _elements(blob, STATE)
        for s in states or []:
            blob = r.array(_ptr(s["moduleGroupDefs"]), MODULE_GROUP.size, 3)
            if blob is None:
                raise FormatError("state without its 3 module groups")
            groups = _elements(blob, MODULE_GROUP)
            for g in groups:
                blob = r.array(_ptr(g["moduleDefs"]), MODULE_DEF_SIZE, g["numModules"])
                modules = None if blob is None else _decode_modules(blob)
                for m in modules or []:
                    _read_module(r, m)
                _attach(g, "moduleDefs", modules)
            _attach(s, "moduleGroupDefs", groups)
        _attach(e, "stateDefs", states)
        _read_curve(r, e["fadeCurveDef"])
    _attach(system, "emitterDefs", emitters)

    blob = r.array(_ptr(system["scriptedInputNodeDefs"]), SCRIPTED_INPUT_NODE.size,
                   system["numScriptedInputNodes"])
    _attach(system, "scriptedInputNodeDefs", None if blob is None else _elements(blob, SCRIPTED_INPUT_NODE))
    if r.pos != len(r.data):
        raise FormatError("%d trailing bytes after the scripted input nodes" % (len(r.data) - r.pos))

    root = None
    for slot_ptr, element, size in r.root_refs:
        if slot_ptr is None:
            continue
        cand = slot_ptr - element * size
        if root is not None and cand != root:
            raise FormatError("inconsistent offsets to the root entry")
        root = cand
    return {"format": FORMAT, "rootPtr": None if root is None else "0x%x" % root, "system": system}


# ---------------------------------------------------------------------------
# Writer (mirrors assetmanager::dumper, including its pointer de-duplication)


class PointerConflict(Exception):
    def __init__(self, holder, key, why):
        super().__init__(why)
        self.holder, self.key, self.why = holder, key, why


class _Dumper:
    def __init__(self):
        self.out = bytearray()
        self.entries = []   # [start, end, kind, blob]
        self.offsets = 0

    def _find(self, start, end, size):
        for i, (s, e, kind, blob) in enumerate(self.entries):
            if s <= start and e >= end:
                return i, (start - s) // size, kind, blob, s
        return None

    def _offset(self, index, element):
        self.offsets += 1
        self.out += struct.pack("<BII", T_OFFSET, index, element)

    def string(self, holder, key, value):
        if value is None:
            self.out += bytes((T_STRING, 0))
            return
        raw = value.encode("latin-1")
        ptr = _ptr(holder[key + "@ptr"])
        if ptr == 0:
            raise PointerConflict(holder, key, "string %r has a null pointer" % value)
        hit = self._find(ptr, ptr, 1)
        if hit:
            index, element, kind, blob, _ = hit
            end = blob.find(b"\0", element)
            if end < 0 or blob[element:end] != raw:
                raise PointerConflict(holder, key, "string %r aliases entry %d" % (value, index))
            self._offset(index, element)
            return
        self.entries.append([ptr, ptr, "string", raw + b"\0"])
        self.out += bytes((T_STRING, 1)) + raw + b"\0"

    def asset(self, holder, key, value, size):
        if value is None:
            self.out += bytes((T_ASSET, 0))
            return
        raw = value.encode("latin-1")
        ptr = _ptr(holder[key + "@ptr"])
        if ptr == 0:
            raise PointerConflict(holder, key, "asset %r has a null pointer" % value)
        hit = self._find(ptr, ptr, size)
        if hit:
            index, element, kind, blob, _ = hit
            if kind != "asset" or element != 0 or blob != raw:
                raise PointerConflict(holder, key, "asset %r aliases entry %d" % (value, index))
            self._offset(index, element)
            return
        self.entries.append([ptr, ptr, "asset", raw])
        self.out += bytes((T_ASSET, 1)) + raw + b"\0"

    def root(self, blob, ptr):
        """dump_single(asset): always written; its pointer is only known when an offset used it."""
        self.entries.append([ptr, ptr, "array", bytes(blob)])
        self.out += struct.pack("<BBI", T_ARRAY, 1, 1) + blob

    def array(self, holder, key, blob, elem_size):
        count = 0 if blob is None else len(blob) // elem_size
        ptr = _ptr(holder[key + "@ptr"])
        if count == 0:
            self.out += bytes((T_ARRAY, 0))
            return
        if ptr == 0:
            raise PointerConflict(holder, key, "array %s has a null pointer" % key)
        end = ptr + elem_size * (count - 1)
        hit = self._find(ptr, end, elem_size)
        if hit:
            index, element, kind, old, start = hit
            region = old[element * elem_size:element * elem_size + len(blob)]
            if region != blob or (ptr - start) % elem_size:
                raise PointerConflict(holder, key, "array %s aliases entry %d with other data" % (key, index))
            self._offset(index, element)
            return
        self.entries.append([ptr, end, "array", bytes(blob)])
        self.out += struct.pack("<BBI", T_ARRAY, 1, count) + blob


def _sync_count(d, list_key, count_key):
    items = d.get(list_key)
    if items is not None:
        d[count_key] = len(items)


def _encode_elements(spec, items, path):
    return b"".join(encode_struct(spec, it, "%s[%d]" % (path, i)) for i, it in enumerate(items))


def _write_curve(w, curve, path):
    _sync_count(curve, "controlPoints", "numControlPoints")
    pts = curve["controlPoints"]
    w.array(curve, "controlPoints", None if pts is None else _encode_elements(CONTROL_POINT, pts, path),
            CONTROL_POINT.size)


def _write_linked_list(w, ll, mt, path):
    _sync_count(ll, "assetList", "numAssets")
    assets = ll["assetList"]
    if assets is None:
        w.array(ll, "assetList", None, LINKED_ASSET_SIZE)
        return
    if assets and mt not in LINKED_ASSET_DEFS:
        raise ValueError("%s: module type %r has no linked assets" % (path, mt))
    spec, slots = LINKED_ASSET_DEFS.get(mt, (None, []))
    w.array(ll, "assetList", _encode_elements(spec, assets, path) if assets else b"", LINKED_ASSET_SIZE)
    for a in assets:
        for field, kind, size in slots:
            if kind == "string":
                w.string(a, field, a[field])
            else:
                w.asset(a, field, a[field], size)


def _module_type(m):
    mt = m["moduleType"]
    return MT[mt] if isinstance(mt, str) else int(mt)


def _prepare_module(m):
    """Sync counts inside a module before its ParticleModuleDef bytes are written."""
    member = MODULE_DEFS.get(_module_type(m))
    if member is None:
        return
    data_name, _, _, curves_field, curve_count, ll_path = member
    data = m[data_name]
    if curves_field:
        for c in data[curves_field]:
            _sync_count(c, "controlPoints", "numControlPoints")
    if ll_path:
        _sync_count(_path_get(data, ll_path), "assetList", "numAssets")
    if _module_type(m) == MT["PARTICLE_MODULE_INIT_SPAWN_SHAPE_MESH"]:
        _sync_count(data, "m_meshAssetData", "m_numMeshAssets")


def _write_module(w, m, path):
    mt = _module_type(m)
    member = MODULE_DEFS.get(mt)
    if member is None:
        return
    data_name, _, _, curves_field, curve_count, ll_path = member
    data = m[data_name]
    if curves_field:
        for i in range(curve_count):
            _write_curve(w, data[curves_field][i], "%s.%s[%d]" % (path, curves_field, i))
    if ll_path:
        _write_linked_list(w, _path_get(data, ll_path), mt, path + "." + ll_path)
    if mt == MT["PARTICLE_MODULE_INIT_SPAWN_SHAPE_MESH"]:
        mesh = data["m_meshAssetData"]
        w.array(data, "m_meshAssetData",
                None if mesh is None else _encode_elements(SPAWN_MESH_ASSET, mesh, path), SPAWN_MESH_ASSET.size)


def _encode_once(model):
    w = _Dumper()
    system = model["system"]
    for e in system["emitterDefs"] or []:
        _sync_count(e, "stateDefs", "numStates")
        _sync_count(e["fadeCurveDef"], "controlPoints", "numControlPoints")
        for s in e["stateDefs"] or []:
            for g in s["moduleGroupDefs"]:
                _sync_count(g, "moduleDefs", "numModules")
                for m in g["moduleDefs"] or []:
                    _prepare_module(m)
    _sync_count(system, "emitterDefs", "numEmitters")
    _sync_count(system, "scriptedInputNodeDefs", "numScriptedInputNodes")

    w.root(encode_struct(SYSTEM, system, "system"), _ptr(model.get("rootPtr")))
    w.string(system, "name", system["name"])
    emitters = system["emitterDefs"]
    w.array(system, "emitterDefs", None if emitters is None else _encode_elements(EMITTER, emitters, "emitters"),
            EMITTER.size)
    for ei, e in enumerate(emitters or []):
        states = e["stateDefs"]
        w.array(e, "stateDefs", None if states is None else
                _encode_elements(STATE, states, "emitters[%d].states" % ei), STATE.size)
        for si, s in enumerate(states or []):
            groups = s["moduleGroupDefs"]
            if groups is None or len(groups) != 3:
                raise ValueError("emitters[%d].states[%d]: needs exactly 3 module groups" % (ei, si))
            w.array(s, "moduleGroupDefs", _encode_elements(MODULE_GROUP, groups, "groups"), MODULE_GROUP.size)
            for gi, g in enumerate(groups):
                mods = g["moduleDefs"]
                path = "emitters[%d].states[%d].groups[%d]" % (ei, si, gi)
                blob = None
                if mods is not None:
                    blob = b"".join(encode_struct(module_def_struct(_module_type(m)), m, "%s.modules[%d]" % (path, mi))
                                    for mi, m in enumerate(mods))
                w.array(g, "moduleDefs", blob, MODULE_DEF_SIZE)
                for mi, m in enumerate(mods or []):
                    _write_module(w, m, "%s.modules[%d]" % (path, mi))
        _write_curve(w, e["fadeCurveDef"], "emitters[%d].fadeCurve" % ei)
    nodes = system["scriptedInputNodeDefs"]
    w.array(system, "scriptedInputNodeDefs", None if nodes is None else
            _encode_elements(SCRIPTED_INPUT_NODE, nodes, "scriptedInputNodes"), SCRIPTED_INPUT_NODE.size)
    return w


FRESH_POINTER_BASE = 0x7F0000000000


def encode(model, strict=False, stats=None):
    """Encode a model (from decode() or JSON) into .iw7VFX bytes.

    strict=True raises PointerConflict instead of assigning fresh pointers
    (used by the round trip: a stock file never needs one). `stats`, when a
    dict, receives the number of OFFSET tokens and of reassigned pointers.
    """
    if model.get("format") != FORMAT:
        raise ValueError("not a %s model" % FORMAT)
    model = copy.deepcopy(model)
    fresh = FRESH_POINTER_BASE
    for attempt in range(100000):
        try:
            w = _encode_once(model)
        except PointerConflict as c:
            if strict:
                raise
            c.holder[c.key + "@ptr"] = "0x%x" % fresh
            fresh += 0x10000
            continue
        if stats is not None:
            stats["offsets"] = w.offsets
            stats["reassigned"] = attempt
        return bytes(w.out)
    raise RuntimeError("pointer conflicts did not converge")


# ---------------------------------------------------------------------------
# Builders for new content (zeroed structs, empty children; pointers are
# assigned by encode()).


def new_model(name, version=15):
    system = decode_struct(SYSTEM, bytes(SYSTEM.size))
    system["version"] = version
    system["occlusionOverrideEmitterIndex"] = -1
    # Stock header values: with zeroed cull radii and sun distance the game draws nothing.
    system["flags"] = SYSTEM_FLAG_BASE
    system["drawFrustumCullRadius"] = -1.0
    system["updateFrustumCullRadius"] = -1.0
    system["sunDistance"] = 100000.0
    system["editorRotation"] = [0.0, 0.0, 0.0, 1.0]
    _attach(system, "name", name)
    _attach(system, "emitterDefs", [])
    _attach(system, "scriptedInputNodeDefs", None)
    return {"format": FORMAT, "rootPtr": None, "system": system}


# System flag bits, derived from the content as the cp_zmb systems set them. Under mask 0x41007 the
# rule reproduces 1139 of the 1162 non-empty stock systems; the other 23 differ only by 0x1000:
# 0x40000 always, 0x1 particles (sprites, tails, beams...), 0x2 models and clouds, 0x6 omni lights,
# 0x1000 runners, decals and physics (ray cast) modules.
SYSTEM_FLAG_BASE = 0x40000
SYSTEM_FLAGS_BY_TYPE = {"MODEL": 0x2, "CLOUD": 0x2, "SPARK_CLOUD": 0x2, "LIGHT_OMNI": 0x6, "LIGHT_SPOT": 0x6,
                        "RUNNER": 0x1000, "DECAL": 0x1000}


def system_flags(model):
    """System flags derived from the element types and modules of a model's emitters."""
    flags = SYSTEM_FLAG_BASE
    for e in model["system"].get("emitterDefs") or []:
        for st in e.get("stateDefs") or []:
            t = st["elementType"].replace("PARTICLE_ELEMENT_TYPE_", "")
            flags |= SYSTEM_FLAGS_BY_TYPE.get(t, 0x1)
            for g in st.get("moduleGroupDefs") or []:
                for m in g.get("moduleDefs") or []:
                    if m["moduleType"].startswith("PARTICLE_MODULE_PHYSICS"):
                        flags |= 0x1000
    return flags


def new_emitter():
    e = decode_struct(EMITTER, bytes(EMITTER.size))
    _attach(e, "stateDefs", [])
    _attach(e["fadeCurveDef"], "controlPoints", None)
    return e


def new_state(element_type="PARTICLE_ELEMENT_TYPE_BILLBOARD_SPRITE"):
    s = decode_struct(STATE, bytes(STATE.size))
    s["elementType"] = element_type
    groups = []
    for _ in MODULE_GROUPS:
        g = decode_struct(MODULE_GROUP, bytes(MODULE_GROUP.size))
        _attach(g, "moduleDefs", [])
        groups.append(g)
    _attach(s, "moduleGroupDefs", groups)
    return s


def new_module(module_type):
    mt = MT[module_type] if isinstance(module_type, str) else module_type
    raw = bytearray(MODULE_DEF_SIZE)
    struct.pack_into("<H", raw, 0, mt)
    struct.pack_into("<H", raw, 16, mt)
    m = decode_struct(module_def_struct(mt), bytes(raw))
    member = MODULE_DEFS.get(mt)
    if member:
        data_name, _, _, curves_field, curve_count, ll_path = member
        data = m[data_name]
        if curves_field:
            for c in data[curves_field]:
                _attach(c, "controlPoints", None)
        if ll_path:
            _attach(_path_get(data, ll_path), "assetList", [])
        if mt == MT["PARTICLE_MODULE_INIT_SPAWN_SHAPE_MESH"]:
            _attach(data, "m_meshAssetData", [])
    return m


def new_linked_asset(module_type, **names):
    """e.g. new_linked_asset("PARTICLE_MODULE_INIT_MATERIAL", material="eq/vfx_x")."""
    mt = MT[module_type] if isinstance(module_type, str) else module_type
    spec, slots = LINKED_ASSET_DEFS[mt]
    a = decode_struct(spec, bytes(spec.size))
    for field, _, _ in slots:
        _attach(a, field, names.pop(field, None))
    if names:
        raise ValueError("unknown linked asset fields %s" % sorted(names))
    return a


def module_data(module):
    """The union member dict of a module (e.g. module["colorGraph"])."""
    member = MODULE_DEFS.get(_module_type(module))
    return module[member[0] if member else "moduleBase"]


def new_curve_points(pairs):
    """[(time, value)] -> control points with ZoneTool's invTimeDelta."""
    pts = [{"time": f32(t), "value": f32(v), "invTimeDelta": 0.0, "pad": [0]} for t, v in pairs]
    return recompute_inv_time_delta(pts)


def recompute_inv_time_delta(points):
    """ZoneTool's calculate_inv_time_delta (float32): invTimeDelta[j] = 1 / (t[j] - t[j-1])."""
    prev = 0.0
    for p in points[1:]:
        p["invTimeDelta"] = f32(1.0 / f32(p["time"] - prev))
        prev = p["time"]
    return points


# ---------------------------------------------------------------------------
# Inspection helpers


def iter_modules(model):
    """Yield (emitter index, state index, group name, module dict, module type name)."""
    for ei, e in enumerate(model["system"]["emitterDefs"] or []):
        for si, s in enumerate(e["stateDefs"] or []):
            for gi, g in enumerate(s["moduleGroupDefs"]):
                for m in g["moduleDefs"] or []:
                    mt = m["moduleType"]
                    yield ei, si, MODULE_GROUPS[gi], m, mt if isinstance(mt, str) else "0x%x" % mt


def linked_assets(module):
    """[(field, name)] of a module's linked assets (materials, models, sub-systems...)."""
    member = MODULE_DEFS.get(_module_type(module))
    if not member or not member[5]:
        return []
    ll = _path_get(module[member[0]], member[5])
    out = []
    for a in ll["assetList"] or []:
        for k, v in a.items():
            if k.endswith("@ptr") or k == "_gaps":
                continue
            if v is not None:
                out.append((k, v))
    return out


def summary(model):
    s = model["system"]
    modules = Counter()
    refs = {}
    elements = Counter()
    for e in s["emitterDefs"] or []:
        for st in e["stateDefs"] or []:
            elements[st["elementType"] if isinstance(st["elementType"], str) else str(st["elementType"])] += 1
    for _, _, _, m, name in iter_modules(model):
        modules[name.replace("PARTICLE_MODULE_", "")] += 1
        for field, value in linked_assets(m):
            refs.setdefault(field, [])
            if value not in refs[field]:
                refs[field].append(value)
    return {"name": s["name"], "emitters": len(s["emitterDefs"] or []),
            "elements": {k.replace("PARTICLE_ELEMENT_TYPE_", ""): v for k, v in sorted(elements.items())},
            "modules": dict(sorted(modules.items())), "assets": refs}


def color_samples(model):
    """Per COLOR_GRAPH / COLOR_LERP / INIT_ATTRIBUTES, the RGB values it can produce (for tint screening)."""
    out = []
    for _, _, _, m, name in iter_modules(model):
        if name == "PARTICLE_MODULE_COLOR_GRAPH":
            curves = m["colorGraph"]["m_curves"]
            for base in (0, 4):
                rgb = []
                for c in curves[base:base + 3]:
                    scale = c["scale"] if not isinstance(c["scale"], str) else 1.0
                    vals = [p["value"] * scale for p in (c["controlPoints"] or [])
                            if not isinstance(p["value"], str)]
                    rgb.append(max(vals) if vals else 0.0)
                out.append(rgb)
        elif name == "PARTICLE_MODULE_COLOR_LERP":
            out += [m["colorLerp"]["m_colorBegin"][:3], m["colorLerp"]["m_colorEnd"][:3]]
        elif name == "PARTICLE_MODULE_INIT_ATTRIBUTES":
            out += [m["initAttributes"]["m_colorMin"][:3], m["initAttributes"]["m_colorMax"][:3]]
    return out


# ---------------------------------------------------------------------------
# CLI


def _files(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
                for n in sorted(names):
                    if n.lower().endswith(".iw7vfx"):
                        yield os.path.join(root, n)
        else:
            yield p


def roundtrip_file(path, stats=None):
    """(ok, reason, model): bytes -> model -> JSON text -> model -> bytes must be identical."""
    with open(path, "rb") as f:
        data = f.read()
    try:
        model = decode(data)
        again = encode(json.loads(json.dumps(model)), strict=True, stats=stats)
    except (FormatError, PointerConflict, ValueError, KeyError) as exc:
        return False, "%s: %s" % (type(exc).__name__, exc), None
    if again != data:
        first = next((i for i, (a, b) in enumerate(zip(again, data)) if a != b), min(len(again), len(data)))
        return False, "bytes differ at 0x%x (sizes %d/%d)" % (first, len(again), len(data)), model
    return True, "", model


def cmd_roundtrip(paths, verbose):
    passed, failed = 0, []
    modules, elements, files_with = Counter(), Counter(), Counter()
    offsets = 0
    stats = {}
    for path in _files(paths):
        ok, why, model = roundtrip_file(path, stats)
        if ok:
            passed += 1
            seen = set()
            for _, _, _, _, name in iter_modules(model):
                modules[name] += 1
                seen.add(name)
            for name in seen:
                files_with[name] += 1
            for e in model["system"]["emitterDefs"] or []:
                for s in e["stateDefs"] or []:
                    elements[s["elementType"]] += 1
            offsets += stats["offsets"]
            if verbose:
                print("PASS", path)
        else:
            failed.append((path, why))
            print("FAIL", path, why)
    total = passed + len(failed)
    print("round trip: %d/%d byte-identical, %d failed" % (passed, total, len(failed)))
    print("OFFSET tokens (pointer de-duplication) in passing files: %d" % offsets)
    print("module types (instances, files):")
    for name, n in sorted(modules.items(), key=lambda kv: -kv[1]):
        print("  %-45s %6d %5d" % (name, n, files_with[name]))
    print("element types (states):")
    for name, n in sorted(elements.items(), key=lambda kv: -kv[1]):
        print("  %-45s %6d" % (name, n))
    return 0 if not failed and total else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--to-json", metavar="IW7VFX", help="decode one .iw7VFX to JSON")
    g.add_argument("--from-json", metavar="JSON", help="encode a JSON model to .iw7VFX")
    g.add_argument("--roundtrip", nargs="+", metavar="PATH",
                   help="files or folders: bytes -> JSON -> bytes must be identical; prints pass/fail counts")
    g.add_argument("--summary", nargs="+", metavar="PATH", help="module types and linked assets per system")
    ap.add_argument("-o", "--out", help="output file (default: stdout for JSON/summary)")
    ap.add_argument("--match", help="--summary: only systems whose name matches this regex")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)

    if a.roundtrip:
        return cmd_roundtrip(a.roundtrip, a.verbose)
    if a.to_json:
        with open(a.to_json, "rb") as f:
            text = json.dumps(decode(f.read()), indent=1)
        if a.out:
            with open(a.out, "w", encoding="utf-8") as f:
                f.write(text + "\n")
        else:
            print(text)
        return 0
    if a.from_json:
        if not a.out:
            ap.error("--from-json needs -o")
        with open(a.from_json, encoding="utf-8") as f:
            data = encode(json.load(f))
        with open(a.out, "wb") as f:
            f.write(data)
        return 0
    rows = []
    for path in _files(a.summary):
        with open(path, "rb") as f:
            model = decode(f.read())
        s = summary(model)
        if a.match and not re.search(a.match, s["name"] or ""):
            continue
        s["colors"] = [[round(c, 3) if not isinstance(c, str) else c for c in rgb] for rgb in color_samples(model)]
        rows.append(s)
    text = json.dumps(rows, indent=1)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
