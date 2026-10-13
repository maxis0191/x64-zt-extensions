"""Prepare original sound source only. Default Plan; --write-source never runs tools."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys

from pcm_source import encode_flac, original_wave, read_wave, require
from read_flac import decode

SURFACES = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SURFACES))
from inspect_content import Inputs, Inspector, SOUND_TABLES, no_links, parse_json

PIN = "fab935826c898806855376662a8a03317b3ad8f1"
ZONE = "sdk_original_sound_v1"
BANK = "community_original_sound_v1.all"
ALIAS = "community_original_chime_v1"
SAMPLE = "community/original_chime_v1"
GLOBALS_SHA = "f3562a2a9beb70ec53cdf91e06bb7c50bea8f7636508d2a5b79b51a4ea5bbb6f"
CAP = 512 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def contract(zt_root):
    spec = parse_json((SURFACES / "source_contract.json").read_bytes())
    require(spec["zonetool"]["revision"] == PIN, "ZoneTool contract pin changed")
    inputs = Inputs(zt_root)
    names = ["src/zonetool/zonetool/iw7/" + name for name in
             ("assets/sound_bank.cpp", "common/sound.hpp", "structs.hpp")]
    hashes = {name: spec["zonetool"]["files"][name] for name in names}
    globals_path = "src/zonetool/zonetool/iw7/assets/sound_globals.hpp"
    hashes[globals_path] = GLOBALS_SHA
    contents = {}
    for name, sha in hashes.items():
        data = inputs.read(name, 2 * 1024 * 1024)
        require(digest(data) == sha, "pinned source changed: " + name)
        contents[name] = data.decode("utf-8-sig")
    bank = contents[names[0]]
    match = re.search(r"SND_ALIAS_FIELDS\[\]\s*=\s*\{(.*?)\};", bank, re.S)
    require(match is not None, "alias field table missing")
    fields = re.findall(r'"([^"\r\n]+)"', match.group(1))
    require(fields == spec["alias_csv_fields"] and len(fields) == 53, "alias positional contract changed")
    require('Wav files are not supported!' in bank, "WAV refusal contract changed")
    # Check every enum name we emit against its actual pinned lookup table.
    enums = {"VOLMODS": "interface", "ENTCHANNELS": "scn_fx_unres_2d",
             "vf_curves_s": "default", "lpf_curves_s": "default", "hpf_curves_s": "default",
             "rvb_curves_s": "default", "speaker_maps_s": "default", "occlusion_shapes_s": "default"}
    for table, value in enums.items():
        found = re.search(r"\b" + table + r"\[\]\s*=\s*\{(.*?)\};", contents[globals_path], re.S)
        require(found is not None and value in re.findall(r'"([^"\r\n]*)"', found.group(1)),
                "unknown pinned enum: " + table + "/" + value)
    for source, table, values in (
            (contents[names[1]], "FALSE_TRUE", ("False", "True")),
            (bank, "LOAD_TYPES", ("loaded",)), (bank, "LOOP_TYPES", ("nonlooping",)),
            (bank, "SHAPES", ("disc",)), (bank, "FULLDRYLEVEL", ("",)),
            (bank, "MUSIC_CONTENT", ("none",)), (bank, "GPAD_OUTPUT", ("none",))):
        found = re.search(r"\b" + table + r"\[\]\s*=\s*\{(.*?)\};", source, re.S)
        require(found is not None, "missing enum: " + table)
        entries = re.findall(r'"([^"\r\n]*)"', found.group(1))
        require(all(value in entries for value in values), "enum spelling/case changed: " + table)
    return fields, hashes


def alias_csv(fields):
    row = {key: "0" for key in fields}
    row.update(Name=ALIAS, SecondaryAliasName="", StopAliasName="", Subtitle="", File=SAMPLE,
               vol_min="0.5", vol_max="0.5", vol_mod="interface", pitch_min="1", pitch_max="1",
               dist_min="1", dist_max="1000", channel="scn_fx_unres_2d", type="loaded",
               loop="nonlooping", Probability="1", volumefalloffcurve="default", lpfcurve="default",
               hpfcurve="default", reverbsendcurve="default", SpeakerMap="default", reverb="",
               shape="disc", ignoreDistanceCheck="False", occlusionshape="default", dopplerpreset="",
               contexttype="", contextvalue="", precached="True", duck="", MusicContent="none",
               GPadOutput="none", ForceSubtitle="False")
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(fields)
    writer.writerow([row[key] for key in fields])
    return stream.getvalue().encode("ascii")


def prepare(zt_root, output, wav=None, attest_original=False, write_source=False):
    output = no_links(Path(output).absolute())
    require(not output.exists(), "fresh absent output directory required")
    fields, pins = contract(zt_root)
    if wav is None:
        require(not attest_original, "--attest-original only applies to --wav")
        wave = original_wave()
        provenance = "generated original integer triangle marker, three faded pulses"
    else:
        require(attest_original, "external WAV requires explicit original-content attestation")
        path = no_links(Path(wav).absolute())
        wave = Inputs(path.parent).read(path.name, 192044)
        provenance = "caller-attested original WAV; rights not inferred from audio bytes"
    pcm = read_wave(wave)
    flac = encode_flac(pcm)
    decoded, readback = decode(flac)
    require(decoded == pcm, "separate decoder PCM differs from original WAV")
    alias_path = "sound/" + BANK + ".aliases.csv"
    bank = dict(name=BANK, zone=ZONE, gameLanguage="all", soundLanguage="all", aliases=[alias_path])
    bank.update({key: [] for key in SOUND_TABLES})
    files = {"original/source.wav": wave, "sound_assets/" + SAMPLE + ".flac": flac,
             alias_path: alias_csv(fields), "soundbank/" + BANK + ".json": encoded(bank),
             "zone_source/" + ZONE + ".csv": ("soundbank," + BANK + "\n").encode("ascii"),
             "pcm-readback.json": encoded(readback)}
    report = {"schema": "iw7.original-sound-source/1", "status": "SourcePrepared" if write_source else "Plan",
              "zonetool_pin": PIN, "pinned_sources": pins, "zone": ZONE, "bank": BANK,
              "alias": ALIAS, "sample": SAMPLE, "provenance": provenance,
              "input_wav_sha256": digest(wave), "pcm_sha256": digest(pcm), "samples": len(pcm) // 2,
              "sample_rate": 48000, "channels": 1, "bits_per_sample": 16,
              "alias_lists": 1, "alias_heads": 1, "load_type": "loaded", "loop": "nonlooping",
              "flac_subset_readback_verified": True, "external_decoder_verified": False,
              "native_sab_built": False, "ff_built": False, "delivered": False,
              "playback_verified": False, "ready": False,
              "expected_native_outputs": [ZONE + ".sabl", ZONE + ".sabs", ZONE + ".ff"],
              "source_files": {name: {"bytes": len(data), "sha256": digest(data)} for name, data in files.items()}}
    # Provenance binds adapter and both separate codec implementations too.
    report["adapter_sources"] = {path.name: digest(path.read_bytes()) for path in sorted(Path(__file__).parent.glob("*.py"))}
    report["source_contract_sha256"] = digest((SURFACES / "source_contract.json").read_bytes())
    require(sum(map(len, files.values())) + len(encoded(report)) <= CAP, "total prepared source exceeds 512 KiB")
    if write_source:
        output.mkdir(parents=True, exist_ok=False)
        # No native invocation, overwrite, stock staging, or cleanup on failure.
        for relative, data in files.items():
            path = output / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(data)
        inspector = Inspector(output, ZONE)
        inspector.soundbank(BANK)
        result = inspector.report()
        require(result["errors"] == 0, "existing content preflight refused prepared source")
        require(len(result["findings"]) == 1 and result["findings"][0]["code"] == "sab_build_and_playback",
                "unexpected content preflight findings")
        inspected = (alias_path, "soundbank/" + BANK + ".json", "sound_assets/" + SAMPLE + ".flac")
        expected_preflight = {name: report["source_files"][name] for name in inspected}
        require(result["files"] == expected_preflight, "preflight bytes differ from prepared inventory")
        preflight = encoded(result)
        report["source_files"]["content-preflight.json"] = {"bytes": len(preflight), "sha256": digest(preflight)}
        manifest = encoded(report)
        require(sum(map(len, files.values())) + len(preflight) + len(manifest) <= CAP,
                "total prepared source exceeds 512 KiB")
        with (output / "content-preflight.json").open("xb") as stream:
            stream.write(preflight)
        # Re-read every prepared file, including those outside the Inspector's
        # dependency subset, before publishing a success manifest. Never rewrite
        # the expected inventory to legitimize a changed file.
        final_inputs = Inputs(output)
        for name, expected in report["source_files"].items():
            actual = final_inputs.read(name, CAP)
            require(len(actual) == expected["bytes"] and digest(actual) == expected["sha256"],
                    "prepared file changed before manifest: " + name)
        # A final manifest is evidence of all source checks completing. A failed
        # partial directory is retained and cannot be overwritten or reused.
        with (output / "sound-source.json").open("xb") as stream:
            stream.write(manifest)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zt-source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--wav", type=Path)
    parser.add_argument("--attest-original", action="store_true")
    parser.add_argument("--write-source", action="store_true")
    args = parser.parse_args()
    print(json.dumps(prepare(args.zt_source, args.output, args.wav, args.attest_original, args.write_source), indent=2))


if __name__ == "__main__":
    main()
