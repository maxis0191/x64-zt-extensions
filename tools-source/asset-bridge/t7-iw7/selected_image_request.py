"""Pure closed-report selection for the existing one-object reader; never execute IO."""
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
import re
import stat

import image_metadata_consumer as provenance
from resident_image import CompleteImageObject, object_layout, object_to_dds

PIN = "fab935826c898806855376662a8a03317b3ad8f1"
PROFILE = PIN + ":T7.GfxImage/264"
SCHEMA = "iw7.t7-selected-image-metadata/1"
OUTER = set("schema source_profile native_source_commit zone model model_default lod slot binding_index binding_hash_u32 image_header_bytes header_copies body_observed association_rechecked header_rechecked name_rechecked refused failure_stage reason image provenance allocation_retained atomic_snapshot_proven pixels_copied payload_bytes_read runtime_abi_proven lifetime_proven ready".split())
FALSES = "model_default refused allocation_retained atomic_snapshot_proven pixels_copied runtime_abi_proven lifetime_proven ready".split()
TRUES = "body_observed association_rechecked header_rechecked name_rechecked".split()
IMAGE = set("schema source_profile header_bytes image_name image_name_observed width height depth width1 height1 level_count level_count1 map_type format_namespace format_namespace_attestation dxgi_format total_size flags streaming streamed_part_count use_fallback fallback_level fallback_size fallback_pointer_present delay_load_pixels source_semantic parts pixel_payload_bytes_read allocation_retained atomic_snapshot_proven runtime_abi_proven lifetime_proven ready".split())
PART = {"index", "active", "width", "height", "packed_size_raw", "key_hex"}


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def uint(value, maximum=2**32-1):
    need(type(value) is int and 0 <= value <= maximum, "typed bounded unsigned metadata required")
    return value


def local_path(value, suffix):
    need(type(value) is str and len(value) <= 32767 and "\0" not in value and
         re.match(r"[A-Za-z]:\\", value) and ":" not in value[2:], "ordinary local absolute path required")
    path = PureWindowsPath(value)
    need(str(path) == value and not path.is_reserved() and path.suffix == suffix and
         all(part not in (".", "..") for part in value[3:].split("\\")), "explicit ordinary path/suffix required")
    return path


@dataclass(frozen=True)
class Provider:
    path: str
    identity: str
    bytes: int


@dataclass(frozen=True)
class SelectedImageRequest:
    image_name: str
    part_index: int
    key_hex: str
    expected_bytes: int
    image: CompleteImageObject
    raw_packed_size: int

    def publish_dds(self, pixels, output):
        """Publish already owned bytes only; no pixel path/retail input is opened."""
        target = local_path(output, ".dds")
        need(len(target.name) <= 64, "private DDS basename exceeds 64 characters")
        need(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", target.name), "portable DDS basename required")
        path = Path(output)
        for parent in path.parents:
            info = parent.lstat()
            need(stat.S_ISDIR(info.st_mode) and not (getattr(info,"st_file_attributes",0) & 0x400),
                 "DDS parent must be an existing ordinary directory")
        payload = object_to_dds(self.image, pixels)
        with path.open("xb") as stream:
            stream.write(payload)
        return {"dds_bytes":len(payload), "pixel_bytes":self.expected_bytes,
                "dxgi_format":self.image.dxgi_format, "pixel_bytes_unchanged":True,
                "material_verified":False, "rendered_verified":False, "ready":False}

    def argv(self, providers, output):
        """Return arguments only; actual reader/identity/admission checks remain required."""
        target = local_path(output, ".bin")
        need(len(target.name) <= 64, "reader output basename exceeds 64 characters")
        need(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", target.name), "portable reader output basename required")
        need(type(providers) in (list, tuple) and 1 <= len(providers) <= 8, "explicit 1..8 providers required")
        args = ["--key", self.key_hex, "--expected-bytes", str(self.expected_bytes), "--out", output]
        paths, identities = set(), set()
        for provider in providers:
            need(type(provider) is Provider, "typed provider required")
            source = local_path(provider.path, ".xpak")
            need(type(provider.identity) is str and re.fullmatch(r"[0-9A-F]{8}:[0-9A-F]{16}", provider.identity), "observed Win32 provider identity required")
            need(120 <= uint(provider.bytes, 16*1024**3), "provider byte range differs from existing reader")
            key = str(source).casefold()
            need(key not in paths and provider.identity not in identities, "provider paths/identities must be distinct")
            need(target != source and source.parent not in target.parents and source.parent.parent not in target.parents,
                 "private output must be outside provider stock tree")
            paths.add(key); identities.add(provider.identity)
            args.extend(("--package", provider.path, provider.identity, str(provider.bytes)))
        need(sum(len(arg) for arg in args) <= 32767, "reader command line bound exceeded")
        return args


def select_image(report, *, part_index, native_exit_code, qualified_object_mip_count):
    """Select one entire object from observed/rechecked metadata, not from F2 alone.

    qualified_object_mip_count is a separately reviewed actual layout fact. Never
    supply it from the unqualified packed low4 or byte equality alone. This pure
    function grants no extraction/engine GO and performs no provider discovery.
    """
    need(type(native_exit_code) is int and native_exit_code == 0, "successful original native exit required")
    need(type(report) is dict and set(report) == OUTER, "exact closed body report required; F2 alone has no image body")
    need(report["schema"] == SCHEMA and report["source_profile"] == "t7-image-metadata-v1" and
         report["native_source_commit"] == PIN and report["zone"] == "mp_freerun_04" and
         report["model"] == provenance.MODEL, "exact observed source/selector required")
    for name in FALSES:
        need(report[name] is False, "refused/default/proof promotion cannot select an object")
    for name in TRUES:
        need(report[name] is True, "body/association/header/name must be observed and rechecked")
    for name, value in (("lod",0), ("slot",0), ("binding_index",4), ("binding_hash_u32",provenance.HASH),
                        ("image_header_bytes",264), ("header_copies",2), ("payload_bytes_read",0)):
        need(uint(report[name]) == value, "exact rechecked selector/header scope required")
    need(report["failure_stage"] == "" and report["reason"] == "", "native refusal diagnostic cannot select an object")
    observed = provenance.consume(report["provenance"])
    need(observed["observation_status"] == "complete", "same-pass F2 association incomplete")
    image = report["image"]
    need(type(image) is dict and set(image) == IMAGE, "exact copied-header DTO required")
    need(image["schema"] == "iw7.t7-selected-image-header-metadata/1" and image["source_profile"] == PROFILE and
         uint(image["header_bytes"]) == 264 and image["format_namespace"] == "DXGI_FORMAT" and
         image["format_namespace_attestation"] == "source-layout-member", "attested source layout/format namespace required")
    for name in ("allocation_retained", "atomic_snapshot_proven", "runtime_abi_proven", "lifetime_proven", "ready"):
        need(image[name] is False, "copied DTO cannot promote runtime/retention proof")
    need(uint(image["pixel_payload_bytes_read"]) == 0, "metadata must contain no payload read")
    need(image["image_name_observed"] is True and type(image["image_name"]) is str and
         0 < len(image["image_name"].encode("utf-8")) <= 255 and "\0" not in image["image_name"], "owned observed image name required")
    for name in ("width", "height", "depth", "width1", "height1"):
        uint(image[name], 65535)
    for name in ("level_count", "level_count1", "map_type", "streaming", "streamed_part_count", "use_fallback", "fallback_level"):
        uint(image[name], 255)
    for name in ("dxgi_format", "total_size", "flags", "fallback_size"):
        uint(image[name])
    need(type(image["source_semantic"]) is int and -128 <= image["source_semantic"] <= 127, "raw signed source semantic required")
    for name in ("fallback_pointer_present", "delay_load_pixels"):
        need(type(image[name]) is bool, "raw typed copied-header flag required")
    count = image["streamed_part_count"]
    need(1 <= count <= 4 and image["streaming"] != 0, "an observed streamed part is required")
    need(uint(part_index, 3) < count, "exact active part index required")
    need(type(qualified_object_mip_count) is int and qualified_object_mip_count == 1,
         "separately qualified whole-object single-mip layout required")
    parts = image["parts"]
    need(type(parts) is list and len(parts) == 4, "four physical part descriptors required")
    previous, delta = 0, None
    for index, part in enumerate(parts):
        need(type(part) is dict and set(part) == PART and uint(part["index"],3) == index and
             type(part["active"]) is bool and part["active"] == (index < count), "exact physical part/index/activity required")
        uint(part["width"],65535); uint(part["height"],65535)
        packed = uint(part["packed_size_raw"])
        need(type(part["key_hex"]) is str and re.fullmatch(r"[0-9a-f]{16}", part["key_hex"]), "observed lower-case key64 required")
        if index < count:
            cumulative = packed >> 4
            need(cumulative > previous, "active cumulative sizes must increase")
            if index == part_index:
                delta = cumulative - previous
            previous = cumulative
    selected = parts[part_index]
    need(selected["key_hex"] != "0000000000000000" and 0 < delta <= 262144, "nonzero selected key/whole-object size within existing reader cap required")
    view = CompleteImageObject(selected["width"], selected["height"], image["depth"], image["map_type"],
                               qualified_object_mip_count, image["dxgi_format"], delta, image["format_namespace"])
    object_layout(view)  # Whole delta only. Never slice, change format or clear native flags.
    return SelectedImageRequest(image["image_name"], part_index, selected["key_hex"], delta, view, selected["packed_size_raw"])
