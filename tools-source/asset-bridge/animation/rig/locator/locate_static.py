"""Bounded offline retail-code locator. Requires external admission and GO.

Reads existing references only. Never launches or attaches to a process. Results
are untrusted candidate addresses until independently matched to a live image.
"""
import argparse
from bisect import bisect_right
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import time

from capstone import (Cs, CS_ARCH_X86, CS_MODE_64, CS_OP_IMM, CS_OP_MEM, CS_OP_REG,
                      CS_GRP_JUMP, CS_GRP_CALL, CS_GRP_RET, CS_GRP_IRET,
                      CS_GRP_INT, CS_GRP_BRANCH_RELATIVE)
from capstone.x86_const import X86_REG_ECX, X86_REG_RCX

IMAGE = 0x140000000
TEXT = IMAGE + 0x1000
REGISTER = 0x140A76520
LIMITS = {"input_bytes": 25162848, "edge_candidates": 128, "functions": 16,
          "function_bytes": 8192, "instructions": 128000, "seconds": 60,
          "output_bytes": 4194304, "reverse_depth": 3, "forward_callees": 4}
REFERENCES = {
    "text": (21135360, "5f2953f04a8d5f2a53d1e5a5e076de8f29d5b5303ca652f2420fec8d2a6a9138"),
    "rdata": (3194880, "28b66189c1f35442d3e32ea5077e785e7cb8fbf45ed420094dc6b2795afd04e5"),
    "pdata": (832608, "8ff97607018c0c531a9d6851282701074a50b141729060f9f23ae728c9fad41e"),
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def bounded(ok, message):
    if not ok:
        raise RuntimeError(message)


class Locator:
    def __init__(self, code, pdata, base=TEXT, image=IMAGE):
        require(len(code) <= REFERENCES["text"][0], "text bound")
        require(len(pdata) % 12 == 0 and len(pdata) <= REFERENCES["pdata"][0], "pdata bound")
        self.code, self.base, self.image = code, base, image
        self.started, self.decoded, self.scans, self.search_bytes = time.monotonic(), 0, 0, 0
        self.functions, self.rejected = {}, []
        self.ranges = sorted((image + a, image + b, u) for a, b, u in struct.iter_unpack("<III", pdata) if a < b)
        self.starts = [a for a, _, _ in self.ranges]
        self.prefix_ends = []
        maximum = 0
        for _, end, _ in self.ranges:
            maximum = max(maximum, end)
            self.prefix_ends.append(maximum)
        self.disassembler = Cs(CS_ARCH_X86, CS_MODE_64)
        self.disassembler.detail = True

    def check(self):
        bounded(time.monotonic() - self.started <= LIMITS["seconds"], "analysis deadline")
        bounded(self.decoded <= LIMITS["instructions"], "instruction bound")

    def owner(self, address):
        i, hits = bisect_right(self.starts, address) - 1, []
        while i >= 0 and self.prefix_ends[i] > address:
            start, end, unwind = self.ranges[i]
            if start <= address < end:
                hits.append((start, end, unwind))
            i -= 1
        require(len(hits) == 1, "absent or ambiguous unwind ownership")
        start, end, _ = hits[0]
        require(self.base <= start < end <= self.base + len(self.code), "unwind range outside retained text")
        bounded(end - start <= LIMITS["function_bytes"], "function window bound")
        return hits[0]

    def direct_edges(self, target):
        self.scans += 1
        bounded(self.scans <= 1 + LIMITS["functions"], "text scan count bound")
        self.search_bytes += len(self.code)
        found = []
        # One linear opcode search, not separate full E8 and E9 passes.
        for match in re.finditer(b"[\xe8\xe9]", self.code):
            position = match.start()
            self.check()
            if position + 5 <= len(self.code):
                relative = struct.unpack_from("<i", self.code, position + 1)[0]
                if self.base + position + 5 + relative == target:
                    found.append(self.base + position)
                    bounded(len(found) <= LIMITS["edge_candidates"], "direct edge bound")
        return sorted(found)

    def function(self, address):
        start, end, _ = self.owner(address)
        if start not in self.functions:
            bounded(len(self.functions) < LIMITS["functions"], "function count bound")
            payload = self.code[start - self.base:end - self.base]
            instructions = []
            next_address = start
            for ins in self.disassembler.disasm(payload, start):
                self.check()
                require(ins.address == next_address, "instruction gap")
                bounded(self.decoded < LIMITS["instructions"], "instruction bound")
                instructions.append(ins)
                self.decoded += 1
                next_address += ins.size
            # A partial decode cannot establish a later edge boundary.
            self.functions[start] = (end, payload, instructions)
        return start, self.functions[start]

    def edge(self, address, target):
        start, (_, _, instructions) = self.function(address)
        matching = [ins for ins in instructions if ins.address == address]
        require(len(matching) == 1, "byte edge is not a decoded instruction boundary")
        ins = matching[0]
        require(ins.mnemonic in ("call", "jmp") and len(ins.operands) == 1 and
                ins.operands[0].type == CS_OP_IMM and ins.operands[0].imm == target,
                "direct edge decode differs")
        return start, instructions

    @staticmethod
    def type_seven(instructions, edge_address):
        control_groups = {CS_GRP_JUMP, CS_GRP_CALL, CS_GRP_RET, CS_GRP_IRET,
                          CS_GRP_INT, CS_GRP_BRANCH_RELATIVE}
        evidence = None
        for ins in instructions:
            if ins.address == edge_address:
                if evidence is not None and any(
                    (CS_GRP_JUMP in other.groups or CS_GRP_BRANCH_RELATIVE in other.groups) and
                    (not other.operands or other.operands[0].type != CS_OP_IMM or
                     evidence < other.operands[0].imm <= edge_address)
                    for other in instructions):
                    return None
                return evidence
            if control_groups.intersection(ins.groups):
                evidence = None
            _, writes = ins.regs_access()
            if any(ins.reg_name(reg) in ("rcx", "ecx", "cx", "cl", "ch") for reg in writes):
                evidence = None
            if (ins.mnemonic == "mov" and len(ins.operands) == 2 and
                    ins.operands[0].type == CS_OP_REG and ins.operands[0].reg in (X86_REG_ECX, X86_REG_RCX) and
                    ins.operands[1].type == CS_OP_IMM and ins.operands[1].imm == 7):
                evidence = ins.address
        return None

    def analyze(self, registration=REGISTER):
        edges = self.direct_edges(registration)
        registered = []
        for address in edges:
            # Cheap candidate filter only. The instruction decoder and register
            # dataflow below must independently establish the real ECX argument.
            offset = address - self.base
            if b"\xb9\x07\x00\x00\x00" not in self.code[max(0, offset - 128):offset]:
                continue
            try:
                owner, instructions = self.edge(address, registration)
                value_at = self.type_seven(instructions, address)
                if value_at is not None:
                    registered.append({"edge": hex(address), "owner": hex(owner), "type_seven_set_at": hex(value_at)})
            except ValueError as error:
                self.rejected.append({"edge": hex(address), "reason": str(error)})
        require(len(registered) == 1, "exactly one evidenced type-7 registration wrapper required")
        frontier, visited, routes = {int(registered[0]["owner"], 16)}, set(), []
        for depth in range(1, LIMITS["reverse_depth"] + 1):
            following = set()
            for target in sorted(frontier - visited):
                visited.add(target)
                for address in self.direct_edges(target):
                    try:
                        owner, _ = self.edge(address, target)
                        routes.append({"depth": depth, "edge": hex(address), "target": hex(target), "owner": hex(owner)})
                        following.add(owner)
                    except ValueError as error:
                        self.rejected.append({"edge": hex(address), "reason": str(error)})
            frontier = following
        # Retain bounded call sites for review. Do not guess four forward
        # callees or create live breakpoint commands without inspecting evidence.
        return {"registration_raw_edges": len(edges), "registration": registered,
                "reverse_routes": routes, "functions": self.report_functions(), "rejected": self.rejected,
                "decoded_instructions": self.decoded, "text_scans": self.scans,
                "linear_opcode_search_bytes": self.search_bytes,
                "elapsed_seconds": round(time.monotonic() - self.started, 6),
                "actual_first_writer_established": False, "live_breakpoint_established": False}

    def report_functions(self):
        result = []
        for start, (end, payload, instructions) in sorted(self.functions.items()):
            rows, stores = [], []
            for ins in instructions:
                row = {"va": hex(ins.address), "mnemonic": ins.mnemonic, "operands": ins.op_str}
                rows.append(row)
                if (ins.operands and ins.operands[0].type == CS_OP_MEM and ins.operands[0].mem.disp == 0x58 and
                        ins.mnemonic not in ("cmp", "test", "lea")):
                    stores.append({**row, "surface_base_traced": False, "writer_proved": False})
            result.append({"start": hex(start), "end": hex(end), "bytes": len(payload),
                           "sha256": hashlib.sha256(payload).hexdigest(), "instructions": rows,
                           "offset_58_candidates": stores})
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in REFERENCES:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(args.output.is_absolute() and not args.output.exists() and args.output.parent.is_dir(), "fresh absolute existing-parent output")
    data, read_count = {}, 0
    for name, (size, digest) in REFERENCES.items():
        path = getattr(args, name)
        require(path.is_absolute() and path.is_file() and not path.is_symlink() and path.stat().st_size == size, "exact reference metadata")
        with path.open("rb") as source:
            payload = source.read(size + 1)
        require(len(payload) == size and hashlib.sha256(payload).hexdigest() == digest, "reference content hash mismatch")
        read_count += len(payload)
        require(read_count <= LIMITS["input_bytes"], "cumulative file IO bound")
        data[name] = payload
    locator = Locator(data["text"], data["pdata"])
    result = {"schema": "iw7.rig-first-write-static/1", "limits": LIMITS,
              "reference_hashes_verified": True, "file_read_bytes": read_count,
              "reference_live_provenance": False, "process_attached": False,
              "game_or_zonetool_launched": False, "acceptance_changed": False}
    try:
        result.update(locator.analyze())
        result["status"] = "candidate-route-requires-review"
        code = 0
    except (ValueError, RuntimeError) as error:
        result.update(status="bounded-refusal", error=str(error), functions=locator.report_functions(),
                      decoded_instructions=locator.decoded, text_scans=locator.scans,
                      linear_opcode_search_bytes=locator.search_bytes,
                      actual_first_writer_established=False, live_breakpoint_established=False)
        code = 2
    payload = (json.dumps(result, indent=2, allow_nan=False) + "\n").encode()
    require(len(payload) <= LIMITS["output_bytes"], "output byte bound")
    with args.output.open("xb") as target:
        target.write(payload)
    print(json.dumps({"status": result["status"], "output_bytes": len(payload),
                      "sha256": hashlib.sha256(payload).hexdigest(), "first_writer_established": False}))
    return code


if __name__ == "__main__":
    sys.exit(main())
