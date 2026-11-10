#!/usr/bin/env python3
"""Weapon feel audit: does a weapon handle the way somebody decided, or the way the stock weapon it was cloned from
handles? Raise, drop, reload, sprint, aim, crosshair, spread, ammo, damage, recoil. Stdlib only.

It reads facts from the files of a zonetool source tree and compares them with the stock population read at run time
from a local dump. It never predicts what the engine does with a value: where only the running game can settle a
point, the finding says so and an engine question is added.

Rules (see docs/CONTENT-AUDITS.md for the shared contract):
  F1  template residue of the player-facing groups (shared GroupJudge)
  F2  every timer of the animation package against the length of the animation of its slot
  F3  the moment the ammo arrives against the length of the reload
  F4  where each numeric value sits among the stock weapons (a note, never a warning)
  F6  animation slots that still play the animations only the template weapon owns
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_audit_common as common  # noqa: E402

TOOL = 'weapon-feel-audit'
PREFIX = 'FEEL'
GROUPS = tuple(name for name, _, _ in common.OBSERVABLE if name not in ('sound profile', 'effects'))

# (timer, animation slot, plain words)
TIMER_SLOTS = (
    ('iRaiseTime', 'RAISE', 'raise'),
    ('iFirstRaiseTime', 'FIRST_RAISE', 'first raise'),
    ('iDropTime', 'DROP', 'drop'),
    ('quickRaiseTime', 'QUICK_RAISE', 'quick raise'),
    ('quickDropTime', 'QUICK_DROP', 'quick drop'),
    ('iEmptyRaiseTime', 'EMPTY_RAISE', 'raise with an empty clip'),
    ('iEmptyDropTime', 'EMPTY_DROP', 'drop with an empty clip'),
    ('iReloadTime', 'RELOAD', 'reload'),
    ('iReloadEmptyTime', 'RELOAD_EMPTY', 'empty reload'),
    ('iFastReloadTime', 'FAST_RELOAD', 'fast reload'),
    ('iFastReloadEmptyTime', 'FAST_RELOAD_EMPTY', 'fast empty reload'),
    ('sprintInTime', 'SPRINT_IN', 'sprint start'),
    ('sprintOutTime', 'SPRINT_OUT', 'sprint end'),
    ('sprintLoopTime', 'SPRINT_LOOP', 'sprint loop'),
    ('iReloadStartTime', 'RELOAD_START', 'reload start'),
    ('iReloadEndTime', 'RELOAD_END', 'reload end'),
    ('iAltRaiseTime', 'ALT_RAISE', 'alternate raise'),
    ('iAltDropTime', 'ALT_DROP', 'alternate drop'),
)
# (arrival time, total time, plain words)
ADD_PAIRS = (
    ('iReloadAddTime', 'iReloadTime', 'reload'),
    ('iReloadEmptyAddTime', 'iReloadEmptyTime', 'empty reload'),
    ('iFastReloadAddTime', 'iFastReloadTime', 'fast reload'),
    ('iFastReloadEmptyAddTime', 'iFastReloadEmptyTime', 'fast empty reload'),
)
MIN_POPULATION = 20       # stock ratios a pair needs before its band means anything
MIN_WEAPON_POP = 5        # stock weapons a value needs before "outside stock" means anything
LATE_STOCK_SHARE = 0.01   # an ammo arrival after the end of the reload is a warning when stock does it less often
RESIDUE_SHARE = 0.05      # an animation used by this share of stock packages or fewer belongs to a few weapons
LISTED = 8


def slot_key(slot):
    return 'WEAP_ANIM_' + slot


def usable(value):
    """A timer that means something: a number, above zero, not the 'unused' marker."""
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and value > 0 and value != common.UNSET_TIMER)


def clean(value):
    return value if isinstance(value, str) and value else ''


class Anims:
    """Animation lengths by name, from the tree first and then from stock; one header read per file."""

    def __init__(self, zone_dir, stock, cache=None):
        self.zone_dir, self.stock = zone_dir, stock
        self.cache = cache if cache is not None else {}
        self.names = {}

    def path(self, name):
        if self.zone_dir:
            mine = os.path.join(self.zone_dir, 'xanim', name.replace('/', os.sep) + '.xab')
            if os.path.isfile(mine):
                return mine
        return self.stock.find('xanim', name, '.xab') if self.stock else None

    def lookup(self, name):
        """(found, length in ms or None when the file is there but unreadable)."""
        if name not in self.names:
            path = self.path(name)
            if path is None:
                self.names[name] = (False, None)
            else:
                if path not in self.cache:
                    try:
                        self.cache[path] = common.xab_info(path)['ms']
                    except (ValueError, OSError):
                        self.cache[path] = None
                self.names[name] = (True, self.cache[path])
        return self.names[name]


class StockFeel:
    """What stock animation packages and weapons do, computed once per run."""

    def __init__(self, stock, anims):
        self.packages = 0
        self.ratios = {timer: [] for timer, _, _ in TIMER_SLOTS}
        self.slot_filled, self.slot_anim, self.used = {}, {}, set()
        self.add_total = {pair[0]: 0 for pair in ADD_PAIRS}
        self.add_late = {pair[0]: 0 for pair in ADD_PAIRS}
        for _, _, doc in stock.docs('animpkg'):
            slots, timers = doc.get('anims'), doc.get('timers')
            if not isinstance(slots, dict) or not isinstance(timers, dict):
                continue
            self.packages += 1
            for key, name in slots.items():
                if clean(name):
                    self.slot_filled[key] = self.slot_filled.get(key, 0) + 1
                    self.slot_anim[(key, name)] = self.slot_anim.get((key, name), 0) + 1
                    self.used.add(name)
            for timer, slot, _ in TIMER_SLOTS:
                value, name = timers.get(timer), clean(slots.get(slot_key(slot)))
                if usable(value) and name:
                    found, ms = anims.lookup(name)
                    if found and ms:
                        self.ratios[timer].append(value / ms)
            for add, total, _ in ADD_PAIRS:
                if usable(timers.get(add)) and usable(timers.get(total)):
                    self.add_total[add] += 1
                    if timers[add] > timers[total]:
                        self.add_late[add] += 1
        self.pops = {timer: common.Population(values) for timer, values in self.ratios.items()}
        self._weapons = None
        self.stock = stock

    def weapon_population(self, paths):
        """{path: Population} over the stock weapon files for the wanted leaf paths."""
        if self._weapons is None:
            self._weapons = {}
        missing = [p for p in paths if p not in self._weapons]
        if missing:
            wanted = {p: [] for p in missing}
            for _, _, doc in self.stock.docs('weapons'):
                for path, value in common.leaves(doc).items():
                    if path in wanted and isinstance(value, (int, float)) and not isinstance(value, bool):
                        wanted[path].append(value)
            for path, values in wanted.items():
                self._weapons[path] = common.Population(values)
        return {p: self._weapons[p] for p in paths}


def percent(ratio):
    return int(round(100.0 * ratio))


def times_text(ratio):
    if ratio <= 0:
        return 'much'
    factor = 1.0 / ratio if ratio < 1 else ratio
    return '%.1f times' % factor


def closed_by_decision(finding, intent, item, key, value):
    """A timer somebody declared (and the file matches) closes the warning on it: it carries the reason."""
    if finding['severity'] != 'warn':
        return
    if intent.judge(item, key, value) in ('match', 'keep'):
        finding['severity'] = 'info'
        finding['answered'] = intent.decision(item, key)['why'].strip()


def check_timers(report, item, package, template, anims, sf, intent):
    timers, slots = package.get('timers') or {}, package.get('anims') or {}
    t_timers = (template or {}).get('timers') or {}
    t_slots = (template or {}).get('anims') or {}
    unknown, missing = [], []
    for key, name in slots.items():
        if clean(name) and not anims.lookup(name)[0]:
            (unknown if (sf is None or name in sf.used) else missing).append((key, name))
    if sf is None:
        if unknown:
            report.add('info', PREFIX + '-ANIM-MISSING', item,
                       '%d animation slots name an animation that is not in the tree (no stock dump to compare): %s' % (
                           len(unknown), ', '.join('%s=%s' % (k[10:], n) for k, n in unknown[:LISTED])),
                       notice='those animations may be missing in the game, the tree alone cannot tell',
                       source='source', slots=[k for k, _ in unknown])
        return
    for key, name in missing:
        # a warning, not an error: the dump given may not hold every zone the game loads, so files cannot prove it
        report.add('warn', PREFIX + '-ANIM-MISSING', item,
                   '%s names animation %s, which is neither in the tree nor named by any stock package of the dump '
                   'given' % (key[10:], name),
                   notice='if no loaded zone holds that animation, the weapon plays nothing (or the load fails) in '
                          'that state',
                   proof='engine', source='stock', slot=key, animation=name)
        report.ask('see', item, 'does the weapon move in the state %s?' % key[10:],
                   'its animation %s was found in no file given to the audit' % name, slot=key, animation=name)
    if unknown:
        report.add('info', PREFIX + '-ANIM-NOT-IN-DUMP', item,
                   '%d animation slots use animations stock packages use, but their files are not in the given '
                   'stock zones: %s' % (len(unknown), ', '.join('%s=%s' % (k[10:], n) for k, n in unknown[:LISTED])),
                   source='stock', slots=[k for k, _ in unknown])
    for timer, slot, words in TIMER_SLOTS:
        value, name = timers.get(timer), clean(slots.get(slot_key(slot)))
        if not (usable(value) and name):
            continue
        found, ms = anims.lookup(name)
        if not (found and ms):
            continue
        pop = sf.pops[timer]
        if pop.n < MIN_POPULATION:
            continue
        ratio = value / float(ms)
        position = pop.position(ratio)
        if position is None or position == 'central':
            continue
        lo, hi = pop.percentile(common.CENTRAL[0]), pop.percentile(common.CENTRAL[1])
        message = '%s lasts %s ms but its animation %s is %d ms (plays %d %%); stock middle %d %% (%d..%d %% for 9 in 10, n=%d)' % (
            words, common.fmt(value), name, ms, percent(ratio), percent(pop.median), percent(lo), percent(hi), pop.n)
        if ratio < 1:
            notice = 'the %s runs about %s faster than its animation was drawn: the end of the movement is cut' % (
                words, times_text(ratio))
        else:
            notice = 'the %s runs about %s slower than its animation was drawn: the weapon freezes at the end' % (
                words, times_text(ratio))
        evidence = dict(timer=value, animation=name, length_ms=ms, ratio=round(ratio, 4), stock_p5=round(lo, 4),
                        stock_p95=round(hi, 4), stock_min=round(pop.min, 4), stock_max=round(pop.max, 4), n=pop.n,
                        key='animpkg:timers.' + timer)
        from_template = (template is not None and common.same(t_timers.get(timer), value)
                         and clean(t_slots.get(slot_key(slot))) != name)
        if from_template:
            finding = report.add('warn', PREFIX + '-TIMER-FROM-TEMPLATE', item, message, notice=notice,
                                 proof='engine', source='stock', template_timer=t_timers.get(timer), **evidence)
            why = 'the %s timer was kept from the template while its animation was replaced' % words
        elif position in ('below-all', 'above-all'):
            finding = report.add('warn', PREFIX + '-TIMER-ANIM-EXTREME', item, message, notice=notice,
                                 proof='engine', source='stock', **evidence)
            why = 'the %s timer is outside everything stock does for its animation' % words
        else:
            report.add('info', PREFIX + '-TIMER-ANIM-UNUSUAL', item, message, source='stock', **evidence)
            continue
        closed_by_decision(finding, intent, item, 'animpkg:timers.' + timer, value)
        report.ask('see', item, 'does the %s of %s look finished and natural (not cut short, not frozen)?' % (words, item),
                   why, timer=timer, animation=name, timer_ms=value, length_ms=ms)


def check_ammo(report, item, package, template, sf, intent):
    timers = package.get('timers') or {}
    t_timers = (template or {}).get('timers') or {}
    for add, total, words in ADD_PAIRS:
        a, t = timers.get(add), timers.get(total)
        if not (usable(a) and usable(t)):
            continue
        key = 'animpkg:timers.' + add
        if a > t:
            seen, late = sf.add_total[add], sf.add_late[add]
            share = late / float(seen) if seen else 0.0
            severity = 'warn' if seen and share < LATE_STOCK_SHARE else 'info'
            finding = report.add(
                severity, PREFIX + '-RELOAD-ADD-LATE', item,
                '%s ammo arrives at %s ms but the %s ends at %s ms; %d of %d stock packages do that' % (
                    words, common.fmt(a), words, common.fmt(t), late, seen),
                notice='the ammo counter refills after the reload has already ended', source='stock',
                add=a, total=t, stock_late=late, stock_n=seen, key=key)
            closed_by_decision(finding, intent, item, key, a)
        if template is not None and usable(t_timers.get(add)) and usable(t_timers.get(total)):
            if common.same(t_timers[add], a) and not common.same(t_timers[total], t):
                finding = report.add(
                    'warn', PREFIX + '-RELOAD-ADD-TEMPLATE', item,
                    '%s ammo arrives at %s ms, exactly as in the template, but the %s now lasts %s ms (template %s ms)' % (
                        words, common.fmt(a), words, common.fmt(t), common.fmt(t_timers[total])),
                    notice='the moment the ammo arrives was not adapted to the new reload animation',
                    proof='engine', source='stock', add=a, total=t, template_total=t_timers[total], key=key)
                closed_by_decision(finding, intent, item, key, a)
                report.ask('time', item, 'does the ammo counter change while the magazine goes in during the %s?' % words,
                           'the arrival time is the template value, the reload animation is new', add_ms=a, total_ms=t)


def check_outside(report, item, weapon, sf):
    own = {}
    for path, value in common.leaves(weapon).items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            hit = common.observable_group('weapon:' + path)
            if hit and hit[0] in GROUPS:
                own[path] = value
    pops = sf.weapon_population(sorted(own))
    out = []
    for path in sorted(own):
        pop = pops[path]
        if pop.n >= MIN_WEAPON_POP and (own[path] < pop.min or own[path] > pop.max):
            out.append((path, own[path], pop))
    if out:
        shown = ', '.join('%s=%s (stock %s..%s)' % (p.replace('weapDef.', ''), common.fmt(v), common.fmt(pp.min),
                                                    common.fmt(pp.max)) for p, v, pp in out[:LISTED])
        more = '' if len(out) <= LISTED else ' and %d more' % (len(out) - LISTED)
        report.add('info', PREFIX + '-OUTSIDE-STOCK', item,
                   '%d values are outside everything stock weapons have: %s%s' % (len(out), shown, more),
                   source='stock', values={p: v for p, v, _ in out})


def check_template_anims(report, item, package, template, template_name, sf):
    slots, t_slots = package.get('anims') or {}, (template or {}).get('anims') or {}
    left = []
    for key in sorted(slots):
        name = clean(slots[key])
        if not name or clean(t_slots.get(key)) != name:
            continue
        filled = sf.slot_filled.get(key, 0)
        used = sf.slot_anim.get((key, name), 0)
        if filled and used / float(filled) <= RESIDUE_SHARE:
            left.append((key[10:], name, used, filled))
    if left:
        shown = ', '.join('%s=%s (used by %d of %d stock packages)' % item_ for item_ in left[:LISTED])
        more = '' if len(left) <= LISTED else ', and %d more' % (len(left) - LISTED)
        report.add('warn', PREFIX + '-TEMPLATE-ANIMS', item,
                   '%d animation slots still play the template weapon\'s own animations: %s%s' % (
                       len(left), shown, more),
                   notice='the weapon plays a movement that belongs to %s in those states' % (template_name or 'another weapon'),
                   proof='engine', source='stock', slots=[{'slot': s, 'animation': n, 'used': u, 'filled': f}
                                                           for s, n, u, f in left], template=template_name)
        report.ask('see', item, 'does the weapon play the right movement in %s?' % ', '.join(s for s, _, _, _ in left[:LISTED]),
                   'those slots hold animations used by few stock weapons, taken from %s' % (template_name or 'the template'))


def write_skeleton(directory, item, judge, templates, report):
    path = os.path.join(directory, item + '.intent.json')
    if os.path.exists(path):
        report.add('info', PREFIX + '-SKELETON-EXISTS', item, 'not written: %s already exists' % path)
        return None
    declared = {kind: t['name'] for kind, t in templates.items()
                if t['name'] and t['how'] in ('declared', 'weapon-template', 'nearest')}
    # every group, not only the ones this audit owns: one intent file per weapon serves the three audits
    doc = judge.skeleton(template=declared or None, source='')
    os.makedirs(directory, exist_ok=True)
    with open(path, 'x', encoding='utf-8', newline='\n') as handle:
        json.dump(doc, handle, indent=1, sort_keys=True)
        handle.write('\n')
    return path


def audit(zone_dir, stock, intent, items=None, skeleton_dir=None, **options):
    """Return a common.Report for the tree. No printing, no exit."""
    report = common.Report(TOOL, zone_dir)
    intent.report_problems(report)
    facts, written = {}, []
    anims = Anims(zone_dir, stock)
    sf = None
    if stock:
        sf = StockFeel(stock, Anims(None, stock, anims.cache))
        report.facts['stock'] = {'animation packages': sf.packages,
                                 'pairs with a population': sum(1 for p in sf.pops.values() if p.n >= MIN_POPULATION)}
    else:
        report.add('info', PREFIX + '-NO-STOCK', os.path.basename(zone_dir),
                   'no stock dump given: template residue, timer bands, ammo arrival and stock positions are not '
                   'checked; only declared decisions and missing animations are', source='stock')
    for item in (items or common.weapon_names(zone_dir)):
        try:
            judge, documents, templates = common.judge_weapon(zone_dir, item, intent, stock)
        except (OSError, ValueError) as error:
            report.add('error', PREFIX + '-UNREADABLE', item, 'cannot read the weapon files: %s' % error)
            continue
        facts[item] = common.template_facts(templates)
        # a stock asset audited as itself has no template (how = 'self', doc None): the template rules stay silent
        judge.report(report, PREFIX, only=GROUPS)
        package, tpl = documents.get('animpkg'), templates['animpkg']
        if isinstance(package, dict):
            tdoc = tpl['doc'] if isinstance(tpl['doc'], dict) else None
            check_timers(report, item, package, tdoc, anims, sf, intent)
            if sf is not None:
                check_ammo(report, item, package, tdoc, sf, intent)
                if tdoc is not None:
                    check_template_anims(report, item, package, tdoc, tpl['name'], sf)
        if sf is not None and isinstance(documents.get('weapon'), dict):
            check_outside(report, item, documents['weapon'], sf)
        if skeleton_dir:
            path = write_skeleton(skeleton_dir, item, judge, templates, report)
            if path:
                written.append(path)
    report.facts['templates'] = facts
    if skeleton_dir:
        report.facts['skeleton files'] = written
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description='Does each weapon handle the way somebody decided, or the way the '
                                             'stock weapon it was cloned from handles?')
    ap.add_argument('tree', help='zonetool source tree of the mod (folder holding weapons/, sound/, ...)')
    ap.add_argument('--item', action='append', default=[], help='only this weapon (repeatable)')
    ap.add_argument('--write-intent-skeleton', metavar='DIR',
                    help='write DIR/<weapon>.intent.json listing every value still equal to the template (handling, '
                         'sound profile and effects), each with an empty reason; it decides nothing until the '
                         'reasons are written (never overwrites a file)')
    common.add_common_args(ap)
    args = ap.parse_args(argv)
    try:
        zone_dir = common.locate_zone_dir(args.tree)
    except ValueError as error:
        ap.error(str(error))
    stock = common.stock_from_args(args)
    intent = common.Intent.load(args.intent) if args.intent else common.Intent()
    report = audit(zone_dir, stock, intent, items=args.item or None, skeleton_dir=args.write_intent_skeleton)
    return common.finish(report, args, intent=intent)


if __name__ == '__main__':
    sys.exit(main())
