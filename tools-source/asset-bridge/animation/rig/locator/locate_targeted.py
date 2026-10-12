"""One seeded static route and explicit continuations; separate reviewed GO required."""
import argparse
from bisect import bisect_right
from collections import deque
import hashlib
import json
from pathlib import Path
import struct
import time

from capstone import (Cs, CS_ARCH_X86, CS_MODE_64, CS_OP_IMM, CS_OP_MEM,
                      CS_AC_WRITE, CS_GRP_CALL, CS_GRP_JUMP, CS_GRP_RET,
                      CS_GRP_IRET, CS_GRP_INT, CS_GRP_BRANCH_RELATIVE)

IMAGE, TEXT, ENTRY = 0x140000000, 0x140001000, 0x140a17970
LIMITS = {"root_entries": 1, "fragments": 8, "fragment_bytes": 2048,
          "decoded_bytes": 8192, "instructions": 2048, "control_edges": 64,
          "seconds": 10, "text_scans": 0, "external_callees_followed": 0}
REFERENCES = {
    "text": (21135360, "5f2953f04a8d5f2a53d1e5a5e076de8f29d5b5303ca652f2420fec8d2a6a9138"),
    "rdata": (3194880, "28b66189c1f35442d3e32ea5077e785e7cb8fbf45ed420094dc6b2795afd04e5"),
    "pdata": (832608, "8ff97607018c0c531a9d6851282701074a50b141729060f9f23ae728c9fad41e"),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bounded(condition, message):
    if not condition:
        raise RuntimeError(message)


class TargetedLocator:
    def __init__(self, code, pdata, base=TEXT, image=IMAGE, limits=None):
        self.started = time.monotonic()
        self.limits = dict(LIMITS if limits is None else limits)
        require(len(code) <= REFERENCES["text"][0], "text bound")
        require(len(pdata) % 12 == 0 and len(pdata) <= REFERENCES["pdata"][0], "pdata bound")
        self.code, self.base = code, base
        self.ranges = sorted((image + a, image + b, u) for a, b, u in struct.iter_unpack("<III", pdata) if a < b)
        self.starts = [a for a, _, _ in self.ranges]
        self.prefix_ends, maximum = [], 0
        for _, end, _ in self.ranges:
            maximum = max(maximum, end)
            self.prefix_ends.append(maximum)
        self.fragments, self.instructions, self.reached = {}, {}, set()
        self.edges, self.calls, self.unresolved = [], [], []
        self.decoded_bytes, self.decoded = 0, 0
        self.disassembler = Cs(CS_ARCH_X86, CS_MODE_64)
        self.disassembler.detail = True
        self.check()

    def check(self):
        bounded(time.monotonic() - self.started < self.limits["seconds"], "targeted analysis deadline")

    def intersections(self, start, end):
        result, index = [], bisect_right(self.starts, end - 1) - 1
        while index >= 0 and self.prefix_ends[index] > start:
            self.check()
            row = self.ranges[index]
            if row[0] < end and row[1] > start:
                result.append(row)
            index -= 1
        return result

    def fragment(self, address):
        owners = self.intersections(address, address + 1)
        require(len(owners) == 1, "absent or ambiguous pdata ownership")
        start, end, unwind = owners[0]
        require(self.base <= start < end <= self.base + len(self.code), "pdata range outside retained text")
        require(len(self.intersections(start, end)) == 1, "selected pdata range overlaps another entry")
        if start not in self.fragments:
            bounded(len(self.fragments) < self.limits["fragments"], "fragment count bound")
            bounded(end - start <= self.limits["fragment_bytes"], "fragment byte bound")
            bounded(self.decoded_bytes + end - start <= self.limits["decoded_bytes"], "decoded byte bound")
            payload = self.code[start - self.base:end - self.base]
            self.decoded_bytes += len(payload)
            row = {"start": start, "end": end, "unwind_rva": unwind,
                   "sha256": hashlib.sha256(payload).hexdigest(), "instructions": []}
            self.fragments[start] = row
            cursor = start
            for ins in self.disassembler.disasm(payload, start):
                self.check()
                require(ins.address == cursor, "instruction gap")
                bounded(self.decoded < self.limits["instructions"], "instruction bound")
                self.decoded += 1
                row["instructions"].append(ins)
                self.instructions[ins.address] = (start, ins)
                cursor += ins.size
            require(cursor == end, "incomplete pdata fragment decode")
        require(address in self.instructions, "continuation is not a decoded instruction boundary")
        return self.fragments[start], self.instructions[address][1]

    def control_edge(self, source, target, kind):
        bounded(len(self.edges) < self.limits["control_edges"], "control edge bound")
        self.edges.append({"source": hex(source), "target": None if target is None else hex(target), "kind": kind})

    def analyze(self, entry):
        pending = deque([entry])
        while pending:
            self.check()
            address = pending.popleft()
            if address in self.reached:
                continue
            fragment, ins = self.fragment(address)
            self.reached.add(address)
            groups = set(ins.groups)
            direct = len(ins.operands) == 1 and ins.operands[0].type == CS_OP_IMM
            target = ins.operands[0].imm if direct else None
            following = ins.address + ins.size
            if CS_GRP_CALL in groups:
                self.control_edge(address, target, "call-not-followed")
                self.calls.append({"at": hex(address), "target": None if target is None else hex(target),
                                   "operands": ins.op_str, "followed": False,
                                   "returning_fallthrough_assumed": True})
            elif groups.intersection({CS_GRP_RET, CS_GRP_IRET, CS_GRP_INT}) or ins.mnemonic in ("ud2", "hlt"):
                continue
            elif groups.intersection({CS_GRP_JUMP, CS_GRP_BRANCH_RELATIVE}):
                self.control_edge(address, target, "direct-branch" if direct else "indirect-branch-unresolved")
                if direct:
                    pending.append(target)
                else:
                    self.unresolved.append({"at": hex(address), "reason": "indirect control target not followed"})
                if ins.mnemonic in ("jmp", "ljmp"):
                    continue
            if following == fragment["end"]:
                self.control_edge(address, following, "boundary-fallthrough")
            pending.append(following)
        self.check()
        return self.report(entry)

    def report(self, entry):
        fragments = []
        for start, fragment in sorted(self.fragments.items()):
            rows, candidates, references = [], [], []
            for ins in fragment["instructions"]:
                reached = ins.address in self.reached
                row = {"va": hex(ins.address), "mnemonic": ins.mnemonic,
                       "operands": ins.op_str, "reachable_in_static_walk": reached}
                rows.append(row)
                for index, operand in enumerate(ins.operands):
                    if (reached and operand.type == CS_OP_MEM and
                            operand.mem.disp <= 0x58 < operand.mem.disp + operand.size):
                        # Pinned Capstone 5.0.7 labels MOVUPS memory destinations
                        # read-only. Keep every overlap reference, and supplement
                        # access metadata only for explicit MOV-family destinations.
                        mov_destination = index == 0 and ins.mnemonic.startswith(("mov", "vmov"))
                        classification = ("decoder-write-operand" if operand.access & CS_AC_WRITE else
                                          "mov-family-memory-destination" if mov_destination else
                                          "memory-reference-only")
                        reference = {**row, "operand_index": index, "operand_bytes": operand.size,
                                     "decoder_access": operand.access, "classification": classification,
                                     "displacement": operand.mem.disp, "surface_base_traced": False,
                                     "writer_proved": False}
                        references.append(reference)
                        if operand.access & CS_AC_WRITE or mov_destination:
                            candidates.append(reference)
            fragments.append({"start": hex(start), "end": hex(fragment["end"]),
                              "bytes": fragment["end"] - start, "sha256": fragment["sha256"],
                              "unwind_rva": hex(fragment["unwind_rva"]), "instructions": rows,
                              "offset_58_overlap_references": references,
                              "offset_58_overlap_candidates": candidates})
        return {"entry": hex(entry), "fragments": fragments, "control_edges": self.edges,
                "calls_not_followed": self.calls, "unresolved": self.unresolved,
                "fragment_count": len(fragments), "decoded_bytes": self.decoded_bytes,
                "decoded_instructions": self.decoded, "reachable_instructions": len(self.reached),
                "control_edge_count": len(self.edges), "text_scans": 0, "linear_opcode_search_bytes": 0,
                "external_callees_followed": 0, "root_entries": 1,
                "elapsed_seconds": round(time.monotonic() - self.started, 6),
                "complete_logical_function_established": False,
                "continuation_same_function_established": False,
                "actual_first_writer_established": False, "live_breakpoint_established": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in REFERENCES:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--entry", required=True)
    parser.add_argument("--max-output-bytes", type=int, default=3 * 1024 * 1024)
    args = parser.parse_args()
    require(args.entry == hex(ENTRY), "reviewed unique seed required")
    require(1 <= args.max_output_bytes <= 3 * 1024 * 1024, "report byte ceiling")
    require(args.output.is_absolute() and not args.output.exists() and args.output.parent.is_dir(), "fresh absolute existing-parent output")
    data, read_count = {}, 0
    for name, (size, digest) in REFERENCES.items():
        path = getattr(args, name)
        require(path.is_absolute() and path.is_file() and not path.is_symlink() and path.stat().st_size == size, "exact reference metadata")
        with path.open("rb") as source:
            payload = source.read(size + 1)
        require(len(payload) == size and hashlib.sha256(payload).hexdigest() == digest, "reference content hash mismatch")
        read_count += len(payload)
        require(read_count <= 25162848, "cumulative file IO bound")
        data[name] = payload
    locator = TargetedLocator(data["text"], data["pdata"])
    result = {"schema": "iw7.rig-targeted-static/1", "limits": LIMITS,
              "report_limit_bytes": args.max_output_bytes, "reference_hashes_verified": True,
              "file_read_bytes": read_count, "reference_live_provenance": False,
              "process_attached": False, "game_or_zonetool_launched": False, "acceptance_changed": False}
    try:
        result.update(locator.analyze(ENTRY))
        result["status"], code = "candidate-route-requires-review", 0
    except (ValueError, RuntimeError) as error:
        result.update(locator.report(ENTRY))
        result.update(status="bounded-refusal", error=str(error))
        code = 2
    payload = (json.dumps(result, indent=2, allow_nan=False) + "\n").encode()
    require(len(payload) <= args.max_output_bytes, "output byte bound")
    with args.output.open("xb") as target:
        target.write(payload)
    print(json.dumps({"status": result["status"], "output_bytes": len(payload),
                      "sha256": hashlib.sha256(payload).hexdigest(), "first_writer_established": False}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
