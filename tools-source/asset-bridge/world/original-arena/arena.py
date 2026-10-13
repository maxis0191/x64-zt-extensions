"""Original seven-box scene and reference swept-AABB queries, not Havok data."""
import copy
import math
from pathlib import Path
import re
import sys

WORLD = Path(__file__).resolve().parent.parent
REPO = WORLD.parents[2]
sys.path.insert(0, str(WORLD))
from trigger_bridge import fields, parse, require, vector, convert
sys.path.insert(0, str(REPO / 'ops/model-lab'))
from geometry import original_cube

NAME = 'paris_original_arena'
SCHEMA = 'iw7.original-arena-source/1'
EPSILON = 1e-7


def original_scene():
    return {
        'schema': SCHEMA, 'name': NAME, 'units': 'IW7 model units; physics scale unqualified',
        'solids': [
            {'name': 'floor', 'minimum': [-256, -192, -16], 'maximum': [256, 192, 0]},
            {'name': 'west', 'minimum': [-272, -192, 0], 'maximum': [-256, 192, 96]},
            {'name': 'east', 'minimum': [256, -192, 0], 'maximum': [272, 192, 96]},
            {'name': 'north', 'minimum': [-272, 192, 0], 'maximum': [272, 208, 96]},
            {'name': 'south_left', 'minimum': [-272, -208, 0], 'maximum': [-48, -192, 96]},
            {'name': 'south_right', 'minimum': [48, -208, 0], 'maximum': [272, -192, 96]},
            {'name': 'obstacle', 'minimum': [16, -32, 0], 'maximum': [48, 32, 32]},
        ],
        'goal': {'minimum': [112, 80, 0], 'maximum': [192, 144, 80]},
        'actor_half_size': [15, 15, 36],
        'route_centers': [[-128, -96, 36], [-128, 96, 36], [152, 112, 36]],
        'material_reference': None, 'physics_serialized': False, 'runtime_verified': False,
    }


def box(value, label, named=False):
    fields(value, ('name', 'minimum', 'maximum') if named else ('minimum', 'maximum'), label)
    if named:
        require(type(value['name']) is str and re.fullmatch(r'[a-z][a-z0-9_]{0,31}', value['name']), 'Portable solid name required')
    lo, hi = vector(value['minimum'], label), vector(value['maximum'], label)
    require(all(-4096 <= a < b <= 4096 and b-a >= 0.25 for a, b in zip(lo, hi)), 'Positive bounded box dimensions required')
    return dict(value, minimum=lo, maximum=hi)


def validate(scene):
    fields(scene, ('schema', 'name', 'units', 'solids', 'goal', 'actor_half_size', 'route_centers',
                   'material_reference', 'physics_serialized', 'runtime_verified'), 'arena')
    require(scene['schema'] == SCHEMA and scene['name'] == NAME, 'Exact original arena identity required')
    require(scene['units'] == original_scene()['units'], 'Explicit unqualified physics scale required')
    require(scene['material_reference'] is None and scene['physics_serialized'] is False and scene['runtime_verified'] is False,
            'Source geometry must not claim material, physics or runtime qualification')
    require(type(scene['solids']) is list and 1 <= len(scene['solids']) <= 8, 'One to eight original boxes required')
    out = copy.deepcopy(scene)
    out['solids'] = [box(s, 'solid', True) for s in scene['solids']]
    require(len({s['name'] for s in out['solids']}) == len(out['solids']), 'Duplicate solid name refused')
    out['goal'] = box(scene['goal'], 'goal')
    out['actor_half_size'] = vector(scene['actor_half_size'], 'actor', True)
    require(all(0 < h <= 128 for h in out['actor_half_size']), 'Positive bounded actor extents required')
    route = scene['route_centers']
    require(type(route) is list and 2 <= len(route) <= 16, 'Bounded route required')
    out['route_centers'] = [vector(p, 'route') for p in route]
    require(all(abs(v) <= 4096 for p in out['route_centers'] for v in p), 'Route coordinates outside source envelope')
    return out


def geometry(scene):
    scene = validate(scene)
    cube = original_cube()['surfaces'][0]
    vertices, triangles = [], []
    for solid in scene['solids']:
        offset = len(vertices)
        midpoint = [(a+b)/2 for a, b in zip(solid['minimum'], solid['maximum'])]
        half = [(b-a)/2 for a, b in zip(solid['minimum'], solid['maximum'])]
        for v in cube['vertices']:
            item = copy.deepcopy(v)
            item['position'] = [midpoint[i]+v['position'][i]*half[i]/8 for i in range(3)]
            vertices.append(item)
        triangles.extend([[offset+i for i in t] for t in cube['triangles']])
    lo = [min(s['minimum'][i] for s in scene['solids']) for i in range(3)]
    hi = [max(s['maximum'][i] for s in scene['solids']) for i in range(3)]
    return {'schema': 'iw7.original-mesh-source/1', 'name': NAME,
            'bones': original_cube()['bones'], 'lods': 1,
            'bounds': {'midpoint': [(a+b)/2 for a,b in zip(lo, hi)], 'half_size': [(b-a)/2 for a,b in zip(lo, hi)]},
            'surfaces': [{'material_reference': None, 'vertices': vertices, 'triangles': triangles}],
            'iw7_serialized': False, 'ready': False}


def goal_trigger(scene):
    goal = validate(scene)['goal']
    midpoint = [(a+b)/2 for a,b in zip(goal['minimum'], goal['maximum'])]
    half = [(b-a)/2 for a,b in zip(goal['minimum'], goal['maximum'])]
    source = {'schema': 'iw7.asset-bridge.h1-client-triggers/1', 'triggerType': [1],
              'trigger': {'count': 1, 'models': [{'contents': 1, 'hullCount': 1, 'firstHull': 0}],
                          'hullCount': 1, 'hulls': [{'bounds': {'midPoint': midpoint, 'halfSize': half},
                                                   'contents': 1, 'slabCount': 3, 'firstSlab': 0}],
                          'slabCount': 3, 'slabs': [{'dir': [int(i == j) for j in range(3)],
                                                   'midPoint': midpoint[i], 'halfSize': half[i]} for i in range(3)]}}
    return source, convert(source)


def swept_box(solid, start, end, half_size):
    """Slab intersection with a Minkowski-expanded box; tangency is not blocking.

    Positions are the query box CENTER, not a player foot/origin. This oracle
    is deliberately an AABB sweep, not a Havok capsule/convex-margin simulation.
    """
    solid = box(solid, 'query solid', 'name' in solid)
    start, end = vector(start, 'start'), vector(end, 'end')
    half = vector(half_size, 'query half size', True)
    lo = [solid['minimum'][i]-half[i] for i in range(3)]
    hi = [solid['maximum'][i]+half[i] for i in range(3)]
    delta = [end[i]-start[i] for i in range(3)]
    if all(lo[i]+EPSILON < start[i] < hi[i]-EPSILON for i in range(3)):
        return {'hit': True, 'start_solid': True, 'fraction': 0.0, 'normal': [0, 0, 0]}
    enter, leave, normal = 0.0, 1.0, [0, 0, 0]
    entered_face = False
    for i in range(3):
        if abs(delta[i]) <= EPSILON:
            if start[i] <= lo[i]+EPSILON or start[i] >= hi[i]-EPSILON:
                return {'hit': False, 'start_solid': False, 'fraction': 1.0, 'normal': [0, 0, 0]}
            continue
        near, far = (lo[i]-start[i])/delta[i], (hi[i]-start[i])/delta[i]
        sign = -1 if delta[i] > 0 else 1
        if near > far:
            near, far = far, near
        if near >= enter-EPSILON:
            enter = max(enter, near)
            normal = [sign if j == i else 0 for j in range(3)]
            entered_face = True
        leave = min(leave, far)
        if enter > leave+EPSILON:
            return {'hit': False, 'start_solid': False, 'fraction': 1.0, 'normal': [0, 0, 0]}
    if not entered_face or enter < 0 or enter > 1 or leave < 0:
        return {'hit': False, 'start_solid': False, 'fraction': 1.0, 'normal': [0, 0, 0]}
    return {'hit': True, 'start_solid': False, 'fraction': enter, 'normal': normal}


def trace(scene, start, end, half_size=(0, 0, 0)):
    hits = [(s['name'], swept_box(s, start, end, list(half_size))) for s in validate(scene)['solids']]
    hits = [(name, h) for name, h in hits if h['hit']]
    if not hits:
        return {'solid': None, 'hit': False, 'start_solid': False, 'fraction': 1.0, 'normal': [0, 0, 0]}
    name, hit = min(hits, key=lambda pair: pair[1]['fraction'])
    return dict(hit, solid=name)


def route_check(scene):
    scene = validate(scene)
    segments = [trace(scene, a, b, scene['actor_half_size']) for a,b in zip(scene['route_centers'], scene['route_centers'][1:])]
    goal, endpoint = scene['goal'], scene['route_centers'][-1]
    return {'schema': 'iw7.original-arena-reference-route/1', 'segments': segments,
            'clear': all(not s['hit'] for s in segments),
            'goal_reached': all(a <= v <= b for a,v,b in zip(goal['minimum'], endpoint, goal['maximum'])),
            'native_collision_verified': False}
