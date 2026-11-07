"""Drive GrayWolf (offline Call of Duty asset extractor) from scripts, stdlib only.

GrayWolf has no command line; ``GrayWolf.exe mcp`` serves the Model Context
Protocol over stdio (one JSON-RPC message per line). This client starts it,
initialises the session and calls its tools, so a port pipeline can export
models with materials and images, sound aliases with audio, anims or
decompiled scripts without a person or an agent clicking anything.

  python graywolf_mcp.py --exe <GrayWolf.exe> call graywolf_find_assets '{"game": "bo3", "names": ["x"]}'
  python graywolf_mcp.py --exe <GrayWolf.exe> tools
"""
import argparse
import json
import subprocess
import sys

PROTOCOL = "2025-06-18"


class GrayWolfError(RuntimeError):
    pass


class GrayWolf:
    def __init__(self, exe, timeout=None):
        self.proc = subprocess.Popen([exe, "mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        self.next_id = 0
        self.timeout = timeout
        init = self._rpc("initialize", {"protocolVersion": PROTOCOL, "capabilities": {},
                                        "clientInfo": {"name": "t7-port", "version": "1"}})
        self.server = init.get("serverInfo", {})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(self, message):
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def _rpc(self, method, params):
        self.next_id += 1
        mid = self.next_id
        self._send({"jsonrpc": "2.0", "id": mid, "method": method, "params": params})
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise GrayWolfError("GrayWolf exited during %s" % method)
            message = json.loads(line)
            if message.get("id") != mid:
                continue                       # notifications (progress, logs)
            if "error" in message:
                raise GrayWolfError("%s: %s" % (method, message["error"]))
            return message["result"]

    def tools(self):
        return self._rpc("tools/list", {})["tools"]

    def call(self, tool, arguments):
        """Call a tool; returns its JSON payload (GrayWolf answers with one JSON text block)."""
        result = self._rpc("tools/call", {"name": tool, "arguments": arguments})
        texts = [c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"]
        if result.get("isError"):
            raise GrayWolfError("%s: %s" % (tool, " ".join(texts)))
        if result.get("structuredContent") is not None:
            return result["structuredContent"]
        joined = "\n".join(texts)
        try:
            return json.loads(joined)
        except ValueError:
            return {"text": joined}

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exe", required=True, help="GrayWolf.exe")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tools")
    c = sub.add_parser("call")
    c.add_argument("tool")
    c.add_argument("arguments", help="JSON object")
    args = ap.parse_args(argv)
    with GrayWolf(args.exe) as gw:
        if args.cmd == "tools":
            out = [{"name": t["name"], "arguments": sorted(t["inputSchema"].get("properties", {}))} for t in gw.tools()]
        else:
            out = gw.call(args.tool, json.loads(args.arguments))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
