"""Verify patch reproducibility/application on one temporary source file only.

No changes in the shared ZoneTool checkout; no compilation or game process.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from blend_bridge import require
from prepare_zonetool_patch import SOURCE, git, prepare


def verify(repo):
    supplied = Path(__file__).with_name("zonetool-fab9358-h1-xsurface.patch").read_bytes()
    with tempfile.TemporaryDirectory(prefix="iw7-h1-patch-") as directory:
        root = Path(directory).resolve()
        patch = root / "generated.patch"
        receipt = prepare(repo, patch)
        require(patch.read_bytes() == supplied, "committed patch differs from generated patch")
        target = root / SOURCE
        target.parent.mkdir(parents=True)
        target.write_bytes(git(repo, "show", "HEAD:" + SOURCE).replace(b"\r\n", b"\n"))
        # Apply actual Git unified diff, not a second string substitution.
        git(root, "apply", "--check", str(patch))
        git(root, "apply", str(patch))
        # Git can apply checkout EOL policy; compare the advertised LF hash.
        applied_lf = target.read_bytes().replace(b"\r\n", b"\n")
        require(hashlib.sha256(applied_lf).hexdigest() == receipt["patched_lf_sha256"],
                "Git-applied source hash differs")
        git(root, "apply", "--reverse", "--check", str(patch))
        receipt.update(patch_reproducible=True, git_apply_and_reverse_check=True,
                       selected_source_bytes=target.stat().st_size, shared_checkout_modified=False)
        return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", type=Path, required=True)
    print(json.dumps(verify(parser.parse_args().source_repo), indent=2))
