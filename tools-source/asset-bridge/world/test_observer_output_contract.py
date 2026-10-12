"""Source-derived passing-output envelope; does not compile or execute C++."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent


class OutputContractChecks(unittest.TestCase):
    def test_passing_cpp_stdout_envelope(self):
        source = (ROOT / 'test_world_clipmap_observer.cpp').read_text()
        header = (ROOT / 'world_clipmap_observer.hpp').read_text()
        profile = (ROOT / 'ObserverStages.Profile.ps1').read_text()
        self.assertRegex(header, r'output_limit\s*=\s*4096;')
        self.assertIn('records == 24 && largest <= w::output_limit', source)
        self.assertIn('available > 0 && available <= w::output_limit', source)
        printf = re.search(r'std::printf\((.*?)\s*records,', source, re.S).group(1)
        template = ''.join(json.loads(s) for s in re.findall(r'"(?:[^"\\]|\\.)*"', printf))
        summary = template.replace('%u', '24').replace('%llu', '4096').encode()
        maximum = 24 * 4096 + len(summary)
        self.assertEqual(len(summary), 204)
        self.assertEqual(maximum, 98508)
        self.assertIn(f'FixtureStdoutExpectedMaximumBytes={maximum}', profile)
        self.assertLess(maximum, 128 * 1024)
        # Replay uses binary mode; the calculation is not a CRLF estimate.
        self.assertIn('_setmode(saved_, _O_BINARY)', source)

    def test_passing_stderr_marker_is_expected_output(self):
        source = (ROOT / 'test_world_clipmap_observer.cpp').read_text()
        marker = re.search(r'if \(!result\) std::fputs\(("(?:[^"\\]|\\.)*")', source).group(1)
        message = json.loads(marker)
        self.assertEqual(len(message.encode()), 62)
        profile = (ROOT / 'ObserverStages.Profile.ps1').read_text()
        self.assertIn("FixtureSuccessStderr='" + message.rstrip('\n') + "'", profile)
        self.assertLess(len(message.replace('\n', '\r\n').encode()), 128)


if __name__ == '__main__':
    unittest.main()
