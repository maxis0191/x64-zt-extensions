#!/usr/bin/env python3
"""Build-log gate: did the fastfile build finish, and what did the builder silently replace by a default?

    python zt_buildlog_gate.py LOG [--zone NAME] [--baseline FILE] [--write-baseline FILE] [--why TEXT]
        [--stock DIR ...] [--intent FILE_OR_DIR] [--json FILE] [--strict]

ZoneTool does not stop when an image or a material is missing. It writes a default one, prints a WARNING among tens of
thousands of lines, and still ends with "Successfully compiled fastfile". Nobody reads those lines; the player sees a
wrong texture. This gate reads the log of one build and reports facts:

  * the build did not complete, or ZoneTool printed ERROR / FATAL lines (errors);
  * which images and materials were replaced by a default (a warning per family, closed only by fixing the content
    or by a declared decision), or, with a baseline, which replacements are NEW since the last accepted build.

A baseline lists stock asset names, so it is never written inside a git work tree. Standard library only.
"""
import argparse
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 't7-weapons'))
import iw7_audit_common as common  # noqa: E402

TOOL = 'buildlog-gate'
PREFIX = 'LOG'
BASELINE_SCHEMA = 'iw7.buildlog-baseline/1'
NEW_LISTED = 50              # NEW-SUBSTITUTION findings written one by one before the rest is aggregated
SAMPLE_NAMES = 10            # names written into the text of a family warning

LINE = re.compile(r'^\[ (INFO|WARNING|ERROR|FATAL) \]\[ (.*?) \]: ?(.*)$')
COMPILED = re.compile(r'Successfully compiled fastfile "([^"]*)"!')
SOUND_MISSING = re.compile(r'^Could not find sound asset (.+)$')

# family -> (finding code, pattern on the text of a WARNING line, plain wording for the notice and the message)
FAMILIES = (
    ('image-not-found', 'LOG-DEFAULT-IMAGE',
     re.compile(r'^Image "(.+)" not found, it will probably look messed up ingame!$'),
     'images were not found when building',
     'the game shows a placeholder image where they are used'),
    ('material-missing', 'LOG-DEFAULT-MATERIAL',
     re.compile(r'^Missing material "(.+)", using default\.\.\.$'),
     'materials were missing when building',
     'the game draws a default material where they are used'),
    ('material-empty-image', 'LOG-EMPTY-IMAGE',
     re.compile(r'^material (.+) has an empty image, assigning default\.\.\.$'),
     'materials have an empty image',
     'the game shows a default image on them'),
)
FAMILY_NAMES = tuple(f[0] for f in FAMILIES)
STOCK_KIND = {'image-not-found': 'image', 'material-missing': 'material', 'material-empty-image': 'material'}


class Parsed:
    """What one log holds, counted in a single pass."""

    def __init__(self):
        self.lines = 0
        self.unparsed = 0
        self.levels = {}
        self.completed = []                 # zone names of "Successfully compiled fastfile"
        self.names = {f: {} for f in FAMILY_NAMES}      # family -> {name: lines}
        self.problems = {}                  # (level, function, text) -> count, ERROR and FATAL
        self.other_warnings = {}            # function -> [count, first text]


def parse_log(path):
    parsed = Parsed()
    with open(path, encoding='utf-8', errors='replace', newline='') as handle:
        for raw in handle:
            text = raw.rstrip('\r\n')
            parsed.lines += 1
            found = LINE.match(text)
            if not found:
                done = COMPILED.search(text)
                if done and done.group(1) not in parsed.completed:
                    parsed.completed.append(done.group(1))
                parsed.unparsed += 1
                continue
            level, function, body = found.groups()
            body = body.rstrip()
            parsed.levels[level] = parsed.levels.get(level, 0) + 1
            if level == 'INFO':
                done = COMPILED.search(body)
                if done and done.group(1) not in parsed.completed:
                    parsed.completed.append(done.group(1))
            elif level == 'WARNING':
                for family, _, pattern, _, _ in FAMILIES:
                    hit = pattern.match(body)
                    if hit:
                        names = parsed.names[family]
                        names[hit.group(1)] = names.get(hit.group(1), 0) + 1
                        break
                else:
                    entry = parsed.other_warnings.setdefault(function, [0, body])
                    entry[0] += 1
            else:
                key = (level, function, body)
                parsed.problems[key] = parsed.problems.get(key, 0) + 1
    return parsed


# ------------------------------------------------------------------ baseline
def inside_git_work_tree(path):
    """The folder holding a .git entry above (or at) the folder of path, else None."""
    here = os.path.dirname(os.path.abspath(path))
    while True:
        if os.path.exists(os.path.join(here, '.git')):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            return None
        here = parent


def baseline_entries(parsed):
    return sorted([family, name] for family in FAMILY_NAMES for name in parsed.names[family])


def check_baseline_target(path):
    """Text of why this path may not receive a baseline, or None."""
    if os.path.exists(path):
        return '%s exists; a baseline is never overwritten (write a new file name)' % path
    repo = inside_git_work_tree(path)
    if repo:
        return ('%s lies inside the git work tree %s; a baseline lists stock asset names and must not be committed '
                '(write it outside the repository)' % (path, repo))
    return None


def write_baseline(path, parsed, zone, why):
    refusal = check_baseline_target(path)
    if refusal:
        raise ValueError(refusal)
    doc = {'schema': BASELINE_SCHEMA, 'zone': zone or '', 'why': why, 'entries': baseline_entries(parsed)}
    with open(path, 'x', encoding='utf-8', newline='\n') as handle:
        json.dump(doc, handle, indent=1)
        handle.write('\n')
    return doc


def load_baseline(path):
    """(set of (family, name), zone, problem text or None)."""
    try:
        doc = common.load_json(path)
    except (OSError, ValueError) as error:
        return set(), '', 'does not parse: %s' % error
    if not isinstance(doc, dict) or doc.get('schema') != BASELINE_SCHEMA:
        return set(), '', 'schema is not %s' % BASELINE_SCHEMA
    entries = doc.get('entries')
    if not isinstance(entries, list) or not all(isinstance(e, list) and len(e) == 2 for e in entries):
        return set(), '', 'entries must be a list of [family, name]'
    return {(e[0], e[1]) for e in entries}, doc.get('zone') or '', None


# ------------------------------------------------------------------ stock
def stock_names(stock):
    """{'image': set, 'material': set} of the names the stock zone lists (the dump csv rows; a leading comma marks
    a row the dumper wrote no file for and is not part of the name)."""
    out = {'image': set(), 'material': set()}
    for zone, root in stock.zones.items():
        path = os.path.join(root, zone + '.csv')
        if not os.path.isfile(path):
            continue
        with open(path, encoding='utf-8', errors='replace') as handle:
            for line in handle:
                kind, _, rest = line.rstrip('\r\n').partition(',')
                if kind in out:
                    out[kind].add(rest[1:] if rest.startswith(',') else rest)
    return out


def in_stock(stock, listed, family, name):
    kind = STOCK_KIND[family]
    if name in listed[kind]:
        return True
    return kind == 'image' and stock.find('images', name, '.iw7Image') is not None


# ------------------------------------------------------------------ audit
def audit(log_path, stock, intent, zone=None, baseline=None):
    """Return a common.Report for one build log. baseline = path of an iw7.buildlog-baseline/1 file, or None."""
    report = common.Report(TOOL, log_path)
    intent.report_problems(report)
    parsed = parse_log(log_path)
    label = zone or (parsed.completed[0] if parsed.completed else os.path.basename(log_path))
    report.facts['lines'] = parsed.lines
    report.facts['unparsed'] = parsed.unparsed
    report.facts['levels'] = dict(sorted(parsed.levels.items()))
    report.facts['families'] = {f: sum(parsed.names[f].values()) for f in FAMILY_NAMES}
    report.facts['distinct'] = {f: len(parsed.names[f]) for f in FAMILY_NAMES}
    report.facts['zones'] = list(parsed.completed)

    done = (zone in parsed.completed) if zone else bool(parsed.completed)
    report.facts['zone'] = zone if zone else (parsed.completed[-1] if parsed.completed else None)
    if not done:
        wanted = 'zone "%s"' % zone if zone else 'any zone'
        report.add('error', 'LOG-NOT-COMPLETED', label,
                   'no line "Successfully compiled fastfile" for %s (zones that finished: %s)' % (
                       wanted, ', '.join(parsed.completed) or 'none'),
                   notice='the build did not finish: there is no usable fastfile from this run')

    for (level, function, body), count in sorted(parsed.problems.items(), key=lambda kv: (kv[0][1], kv[0][2])):
        sound = SOUND_MISSING.match(body)
        if sound:
            report.add('error', 'LOG-SOUND-MISSING', sound.group(1).strip(),
                       'ZoneTool could not find this sound file (%s, %s)' % (level, function),
                       notice='the builder reported an error and did not put this audio file into the build: the sound is silent '
                           'unless a stock bank already holds it',
                       count=count, function=function)
        else:
            report.add('error', 'LOG-' + level, function, '%s: %s' % (level, body),
                       notice='the builder reported a failure; what it affects depends on the message',
                       count=count, function=function, text=body)

    if baseline:
        known, base_zone, problem = load_baseline(baseline)
        if problem:
            report.add('error', 'LOG-BASELINE-FILE', os.path.basename(baseline), problem)
        else:
            report.facts['baseline'] = {'zone': base_zone, 'entries': len(known)}
            _against_baseline(report, parsed, known, label)
    else:
        _without_baseline(report, parsed, stock, label)

    for function, (count, sample) in sorted(parsed.other_warnings.items()):
        report.add('info', 'LOG-OTHER-WARNINGS', function,
                   '%d other warning line(s) from %s, for example: %s' % (count, function, sample[:200]),
                   count=count, sample=sample)
    report.facts['other_warnings'] = {f: v[0] for f, v in sorted(parsed.other_warnings.items())}
    return report


def _without_baseline(report, parsed, stock, label):
    listed = stock_names(stock) if stock else None
    for family, code, _, what, effect in FAMILIES:
        counts = parsed.names[family]
        if not counts:
            continue
        names = sorted(counts)
        evidence = {'count': len(names), 'lines': sum(counts.values()), 'names': names}
        if listed is not None:
            inside = sum(1 for n in names if in_stock(stock, listed, family, n))
            evidence.update(in_stock=inside, not_in_stock=len(names) - inside)
        sample = ', '.join(names[:SAMPLE_NAMES]) + (' and %d more' % (len(names) - SAMPLE_NAMES)
                                                    if len(names) > SAMPLE_NAMES else '')
        report.add('warn', code, label, '%d %s (%d log lines): %s' % (len(names), what, evidence['lines'], sample),
                   notice='%d %s: %s' % (len(names), what, effect), proof='engine', source='source', **evidence)
        report.ask('see', label, 'does the placeholder show where these %s are used, and is that acceptable?' % what.split(' ')[0],
                   'the build replaced %d name(s) by a default and went on' % len(names), family=family,
                   first=names[:SAMPLE_NAMES])
    if listed is None and any(parsed.names[f] for f in FAMILY_NAMES):
        report.add('info', 'LOG-NO-STOCK', label,
                   'no stock dump given: the names are not sorted into "in stock" and "not in stock"')


def _against_baseline(report, parsed, known, label):
    current = {(f, n) for f in FAMILY_NAMES for n in parsed.names[f]}
    accepted = sorted(current & known)
    new = sorted(current - known)
    gone = known - current
    per_family = {f: sum(1 for fam, _ in accepted if fam == f) for f in FAMILY_NAMES}
    if accepted:
        report.add('info', 'LOG-KNOWN-SUBSTITUTIONS', label,
                   '%d substitution(s) are in the baseline: %s' % (
                       len(accepted), ', '.join('%s %d' % (f, c) for f, c in per_family.items() if c)),
                   **{f.replace('-', '_'): c for f, c in per_family.items()})
    wording = {f[0]: (f[3], f[4]) for f in FAMILIES}
    for family, name in new[:NEW_LISTED]:
        report.add('error', 'LOG-NEW-SUBSTITUTION', name,
                   '%s "%s": replaced by a default in this build, not in the baseline' % (family, name),
                   notice='a new placeholder: ' + wording[family][1], family=family, name=name)
    rest = new[NEW_LISTED:]
    if rest:
        per_rest = {}
        for family, _ in rest:
            per_rest[family] = per_rest.get(family, 0) + 1
        report.add('error', 'LOG-NEW-SUBSTITUTION', '(%d more)' % len(rest),
                   '%d more new substitution(s) not listed one by one: %s' % (
                       len(rest), ', '.join('%s %d' % kv for kv in sorted(per_rest.items()))),
                   notice='more new placeholders: the game shows a default where they are used',
                   count=len(rest), names=[n for _, n in rest])
    if gone:
        report.add('info', 'LOG-FIXED-SINCE-BASELINE', label,
                   '%d substitution(s) of the baseline no longer appear in this build' % len(gone), count=len(gone))


def main(argv=None):
    ap = argparse.ArgumentParser(description='Gate a ZoneTool build log: completed? what was replaced by a default?')
    ap.add_argument('log', help='ZoneTool output of the build (build.stdout.log or zt-*.out.log)')
    ap.add_argument('--zone', help='the zone that must have compiled (default: any zone)')
    ap.add_argument('--baseline', metavar='FILE', help='accepted substitutions (iw7.buildlog-baseline/1)')
    ap.add_argument('--write-baseline', metavar='FILE',
                    help='write the substitutions of this log as a baseline; never overwrites, never inside a repository')
    ap.add_argument('--why', help='reason text stored in the baseline written by --write-baseline')
    common.add_common_args(ap)
    args = ap.parse_args(argv)
    if not os.path.isfile(args.log):
        sys.stderr.write('%s: no such log\n' % args.log)
        return 2
    if args.write_baseline:
        refusal = check_baseline_target(args.write_baseline)
        if refusal:
            sys.stderr.write('baseline not written: %s\n' % refusal)
            return 2
    stock = common.stock_from_args(args)
    intent = common.Intent.load(args.intent) if args.intent else common.Intent()
    report = audit(args.log, stock, intent, zone=args.zone, baseline=args.baseline)
    if args.write_baseline:
        if not report.facts.get('zones') or (args.zone and args.zone not in report.facts['zones']):
            sys.stderr.write('baseline not written: the build in this log did not complete\n')
            return common.finish(report, args, intent=intent) or 2
        parsed = parse_log(args.log)
        why = args.why or 'substitutions accepted from %s on %s' % (
            os.path.basename(args.log), datetime.date.today().isoformat())
        write_baseline(args.write_baseline, parsed, args.zone or report.facts.get('zone'), why)
        sys.stdout.write('baseline written: %s (%d entries)\n' % (args.write_baseline, len(baseline_entries(parsed))))
    return common.finish(report, args, intent=intent)


if __name__ == '__main__':
    sys.exit(main())
