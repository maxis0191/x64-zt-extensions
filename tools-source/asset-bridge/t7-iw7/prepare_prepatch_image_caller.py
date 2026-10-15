"""One fixed caller, derived only from the unchanged wired V3 main. Source only."""
import json
from pathlib import Path
import prepare_prepatch_reference as base

NAME = 't7-prepatch-image-caller-v1'
OPTION = '-' + NAME
REPORT = NAME + '.local.json'
HELPER = 'native_prepatch_image_caller_v1.inc'
GUARD = 'prepatch_image_caller_range.hpp'
FIXTURE = 'prepatch_image_caller_fixture.cpp'
API = 'zonetool::t7_prepatch_image_caller_v1'
SCHEMA = 'iw7.t7-prepatch-image-caller-observation/1'
BUILD_SCHEMA = 'iw7.t7-prepatch-image-caller-build/1'
PINS = {'native_prepatch_link_v3.inc': (15827, 'cf839e18a68adb4ed3aae82d683ef110ab595fa8c172584e47ca4d11bb8db48d'), 'prepare_prepatch_link_v3.py': (2236, '66f70ca5a979745288232d76496a339e08d639ddf34560aada6e6b63c5bcffa1'), 'native_prepatch_image_caller_v1.inc': (16778, '39fd69039d16285ca574f73a768130e294c618a089ba365bacdf84fd2cfa0019'), 'prepatch_image_caller_range.hpp': (3117, '0a633964ed558de91bae621b51b28d5e8e0eab20ab790fc000b1b3c6978aa38a'), 'prepatch_image_caller_fixture.cpp': (3828, 'a2471c937e91191fca49820a50ac15091832eaa54bb993c639671e490dd9ade4')}
BASE_PLAN = (305621, 'e484cef7415b2697c188b0202f3771af15377ecb56d98a0a85bfc1d2418fe530')
BASE_MAIN = (14469, '84cde2924df0a0553dd2cddb0ca173aed54af43d6874b06718c01d1a6cec4989')
MAIN = (14557, '2ff1c104f8dfc99432179b289a0453aa1a81b8a99703803fcede1869fae61133')
RETAINED_MAIN = base.RETAINED_MAIN


def wire_main(source):
    base.require_pin(source.encode('utf-8'), BASE_MAIN, 'image-caller immutable V3 main')
    here = Path(__file__).resolve().parent
    for name,pin in PINS.items():
        base.require_pin((here/name).read_bytes().replace(b'\r\n',b'\n'),pin,name)
    old_api = 'zonetool::t7_prepatch_link_v3'
    old_helper = 'native_prepatch_link_v3.inc'
    if source.count(old_api) != 10 or source.count(old_helper) != 1:
        raise ValueError('Frozen V3 wiring differs')
    rendered = source.replace(old_api,API).replace(old_helper,HELPER)
    base.require_pin(rendered.encode('utf-8'),MAIN,'image-caller main')
    return rendered


def prepared_main(plan_raw,read):
    base.require_pin(plan_raw,BASE_PLAN,'image-caller base V3 plan')
    path = Path(json.loads(plan_raw)['PreparedRoot'])/'main.cpp'
    raw = read(path,64*1024,BASE_MAIN[1])
    base.require_pin(raw,BASE_MAIN,'image-caller base V3 main')
    return wire_main(raw.decode('utf-8')).encode('utf-8'),path


def marker():
    return {'Schema':BUILD_SCHEMA,'SourceProfile':NAME,
            'RetainedMainBytes':RETAINED_MAIN[0],'RetainedMainSHA256':RETAINED_MAIN[1],
            'BaseMainBytes':BASE_MAIN[0],'BaseMainSHA256':BASE_MAIN[1],
            'MainBytes':MAIN[0],'MainSHA256':MAIN[1],
            'HelperBytes':PINS[HELPER][0],'HelperSHA256':PINS[HELPER][1]}
