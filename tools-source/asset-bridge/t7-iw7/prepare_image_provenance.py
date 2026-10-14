"""Source-only, opt-in renderer over the exact retained E5 pair; no build/run."""
import hashlib
import json
from pathlib import Path
import prepare_cli
import prepare_material_parts as parts

HERE = Path(__file__).resolve().parent
NAME = "t7-image-provenance-v1"
OPTION = "-t7-iw7-image-provenance-v1"
SCHEMA = "iw7.t7-selected-image-provenance/1"
FLAG = 'utils::flags::has_flag("t7-iw7-image-provenance-v1")'
HELPER = "selected_image_provenance.hpp"
ENTRY = "native_image_provenance.inc"
FIXTURE = "selected_image_provenance_fixture.cpp"
CONTRACT = "image-provenance-source-contract.json"


def pin(raw):
    return len(raw), hashlib.sha256(raw).hexdigest()


def wire(main, cli, observer, helper, entry):
    # Reject another epoch before rendering; these are source strings, not assets.
    parts.require_pin(main.encode(), parts.BASE_MAIN, "provenance base main")
    parts.require_pin(cli.encode(), parts.BASE_CLI, "provenance base CLI")
    parts.require_pin(observer, parts.BASE_OBSERVER, "provenance G2 reader")
    parts.require(type(helper) is bytes and 0 < len(helper) <= 16*1024 and
                  type(entry) is bytes and 0 < len(entry) <= 8*1024, "Bounded provenance source required")
    once = prepare_cli.helper.once
    base = observer.decode().replace('#pragma once\n', '').replace(
        '#include "resident_image_copy.hpp"\n', '')
    parts.require(cli.count(base) == 1, "One exact shared reader required")
    addition = once(helper.decode(), '#pragma once\n', '')
    addition = once(addition, '#include "selected_material_observation.hpp"\n', '')
    context = (
        "\nnamespace zonetool::t7 {\n"
        "using image_provenance_observer = selected_image_provenance::observer<\n"
        "    decltype(&resident_iw7::detail::readable), decltype(&selected_image_provenance::query_memory_state)>;\n"
        "static image_provenance_observer selected_image_provenance_context{\n"
        "    &resident_iw7::detail::readable, &selected_image_provenance::query_memory_state};\n}\n")
    cli = once(cli, base, base + "\n\n" + addition + context)
    original = "\t\treturn db_add_xasset_hook.invoke<XAssetHeader>(type, header);"
    cli = once(cli, original,
        "\t\treturn selected_image_provenance_context.original_add_and_observe(type, header,\n"
        "\t\t\t[](XAssetType original_type, XAssetHeader original_header) {\n"
        "\t\t\t\treturn db_add_xasset_hook.invoke<XAssetHeader>(original_type, original_header);\n"
        "\t\t\t});")
    parts.require(main.count(parts.ANCHOR_FLAG) == 2 and cli.count(parts.ANCHOR_FLAG) == 1,
                  "Exact provenance main/CLI guard inventory required")
    main = main.replace(parts.ANCHOR_FLAG, "(" + parts.ANCHOR_FLAG + " || " + FLAG + ")")
    cli = cli.replace(parts.ANCHOR_FLAG, "(" + parts.ANCHOR_FLAG + " || " + FLAG + ")")
    cli = once(cli, "\tvoid handle_params()\n",
        "\n".join("\t" + line if line else "" for line in entry.decode().splitlines()) +
        "\n\n\tvoid handle_params()\n")
    catalog = '\t\t\t\tconst bool catalog = args.size() == 3 && args[1] == "-t7-iw7-catalog";'
    guard = '\t\t\t\tconst bool provenance = args.size() == 5 && args[1] == "' + OPTION + '";\n'
    guard += '\t\t\t\tif ((' + FLAG + ' && !provenance) || (provenance && (\n'
    for index, option in enumerate(("t7-iw7-model", "t7-iw7-model-v2", "t7-iw7-model-streamed-v1",
                                   "t7-iw7-model-streamed-v2", "t7-iw7-catalog", "t7-prepatch-probe",
                                   "t7-prepatch-reference-v2", "t7-prepatch-link-v3", "t7-iw7-material-parts-v1")):
        guard += '\t\t\t\t\tutils::flags::has_flag("' + option + '")' + (
            " ||\n" if index < 8 else "))))\n")
    guard += '\t\t\t\t\tthrow std::runtime_error("Exclusive exact image-provenance arguments required");\n'
    cli = once(cli, catalog, guard + catalog)
    cli = once(cli, "\t\t\t\tif (catalog) catalog_resident_models_iw7(args[2]);",
        "\t\t\t\tif (provenance) observe_selected_image_provenance_iw7(args[2], args[3], args[4]);\n"
        "\t\t\t\telse if (catalog) catalog_resident_models_iw7(args[2]);")
    error = '\t\t\t\tif (utils::flags::has_flag("t7-iw7-model-streamed-v1") || utils::flags::has_flag("t7-iw7-model-streamed-v2"))'
    cli = once(cli, error,
        "\t\t\t\tif (" + FLAG + ")\n"
        '\t\t\t\t\tZONETOOL_ERROR("T7 image provenance refused: %s", error.what());\n'
        "\t\t\t\telse " + error.lstrip())
    parts.require(len(cli.encode()) <= 128*1024, "Provenance CLI exceeds existing source cap")
    return main, cli


def overlay(main, cli, read):
    raw = read(HERE / CONTRACT, 16*1024)
    contract = json.loads(raw)
    parts.require(type(contract) is dict and
                  set(contract) == {"schema", "source_profile", "files", "main", "cli"} and
                  contract["schema"] == "iw7.t7-image-provenance-source/1" and
                  contract["source_profile"] == NAME and
                  set(contract["files"]) == {HELPER, ENTRY, FIXTURE}, "Exact provenance source contract required")
    files = {}
    for name, item in contract["files"].items():
        parts.require(type(item) is dict and set(item) == {"lf_bytes", "lf_sha256"} and
                      type(item["lf_bytes"]) is int and 0 < item["lf_bytes"] <= 16*1024 and
                      type(item["lf_sha256"]) is str and len(item["lf_sha256"]) == 64,
                      "Typed provenance source pin required")
        files[name] = read(HERE/name, 16*1024, item["lf_sha256"]).replace(b"\r\n", b"\n")
        parts.require_pin(files[name], (item["lf_bytes"], item["lf_sha256"]), name)
    observer = read(HERE/"selected_material_observation.hpp", 32*1024, parts.BASE_OBSERVER[1]).replace(b"\r\n", b"\n")
    main, cli = wire(main, cli, observer, files[HELPER], files[ENTRY])
    for role, value in (("main", main), ("cli", cli)):
        item = contract[role]
        parts.require(type(item) is dict and set(item) == {"bytes", "sha256"} and
                      type(item["bytes"]) is int and 0 < item["bytes"] <= 128*1024 and
                      type(item["sha256"]) is str and len(item["sha256"]) == 64,
                      "Typed provenance output pin required")
        parts.require_pin(value.encode(), (item["bytes"], item["sha256"]), role)
    return main, cli, {"Schema": "iw7.t7-image-provenance-build/1", "SourceProfile": NAME,
        "MainBytes": len(main.encode()), "MainSHA256": pin(main.encode())[1],
        "CLIBytes": len(cli.encode()), "CLISHA256": pin(cli.encode())[1]}
