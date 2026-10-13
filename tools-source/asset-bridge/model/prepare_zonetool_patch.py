"""Generate the narrow converter patch from an unchanged pinned owner fork.

Read-only on the source repo. No fetch, native build, extraction or SDK copying.
The emitted patch changes only H1 -> IW7 assets/xsurface.cpp.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

from blend_bridge import PIN, read_bounded, require, unlinked

SOURCE = "src/zonetool/zonetool/h1/converter/iw7/assets/xsurface.cpp"
VALIDATOR = """
            // Validate before allocation/emission. The pinned IW7 conversion
            // defines only groups 1..4; never retain counts for skipped groups.
            // Native XSurface does not carry the allocation length or XModel
            // bone count: those still need caller/dump-boundary validation.
            void ValidateH1BlendVerts(const zonetool::h1::XSurface* surf)
            {
                if (!surf)
                    throw std::runtime_error("H1->IW7 blend: null surface");

                unsigned int vertices = 0;
                for (unsigned int group = 0; group < 8; ++group)
                {
                    if (surf->blendVertCounts[group] < 0)
                        throw std::runtime_error("H1->IW7 blend: negative vertex count");
                    if (group >= 4 && surf->blendVertCounts[group] != 0)
                        throw std::runtime_error("H1->IW7 blend: influences 5..8 are unsupported");
                    vertices += static_cast<unsigned int>(surf->blendVertCounts[group]);
                }
                if (vertices > surf->vertCount)
                    throw std::runtime_error("H1->IW7 blend: counts exceed surface vertices");
                if (vertices && !surf->blendVerts)
                    throw std::runtime_error("H1->IW7 blend: nonempty counts with null data");

                const auto* in = reinterpret_cast<const unsigned short*>(surf->blendVerts);
                unsigned int cursor = 0;
                for (unsigned int group = 0; group < 4; ++group)
                {
                    for (int vertex = 0; vertex < surf->blendVertCounts[group]; ++vertex)
                    {
                        for (unsigned int influence = 0; influence <= group; ++influence)
                        {
                            const auto word = cursor + (influence == 0 ? 0 : 2 * influence - 1);
                            if (in[word] % 64 != 0)
                                throw std::runtime_error("H1->IW7 blend: bone offset is not a multiple of 64");
                        }
                        cursor += 2 * group + 1;
                    }
                }
            }

""".replace("    ", "\t").lstrip("\n")


def git(repo, *arguments):
    return subprocess.check_output(["git", "-C", str(repo), *arguments], stderr=subprocess.PIPE)


def transform(source):
    require(source.count("// past weights4 are not handled by the iw7->h1 mate we mirror that and skip them") == 1,
            "pinned weights comment differs")
    source = source.replace("// past weights4 are not handled by the iw7->h1 mate we mirror that and skip them",
                            "// Groups 5..8 are rejected until their IW7 layout is independently proven.")
    signature = "\t\t\tvoid PackIW7BlendVerts("
    require(source.count(signature) == 1, "pinned blend function differs")
    source = source.replace(signature, VALIDATOR + signature, 1)
    anchor = "\t\t\t\tconst unsigned int iw7_short_count ="
    require(source.count(anchor) == 1, "pinned allocation anchor differs")
    source = source.replace(anchor, "\t\t\t\tValidateH1BlendVerts(h1surf);\n\n" + anchor, 1)
    require(source.count("if (new_surf->subdivLevelCount)") == 1, "pinned subdivision branch differs")
    return source.replace("if (new_surf->subdivLevelCount)", "if (surf->subdivLevelCount)", 1)


def prepare(repo, output):
    unlinked(repo)
    require(git(repo, "rev-parse", "HEAD").decode().strip() == PIN, "exact ZoneTool pin required")
    original = git(repo, "show", "HEAD:" + SOURCE)
    text = original.decode("utf-8").replace("\r\n", "\n")
    physical = read_bounded(repo / SOURCE, 65536).decode("utf-8").replace("\r\n", "\n")
    require(physical == text, "converter working file differs from pinned blob")
    git(repo, "diff", "--quiet", "HEAD", "--", SOURCE)
    updated = transform(text)
    patch = "".join(difflib.unified_diff(text.splitlines(True), updated.splitlines(True),
                                       "a/" + SOURCE, "b/" + SOURCE))
    unlinked(output)
    require(output.parent.is_dir(), "existing patch destination required")
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(patch)
    return {"schema": "iw7.asset-bridge.zonetool-patch/1", "base_commit": PIN, "file": SOURCE,
            "base_lf_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "patched_lf_sha256": hashlib.sha256(updated.encode()).hexdigest(),
            "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
            "native_compiled": False, "native_behavior_executed": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source_repo, args.output), indent=2))
