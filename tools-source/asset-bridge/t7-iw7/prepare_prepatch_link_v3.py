"""Fixed DB link/lookup V3, derived only from the immutable wired V2 main."""
import json
from pathlib import Path
import prepare_prepatch_reference as base

NAME = 't7-prepatch-link-v3'
OPTION = '-' + NAME
REPORT = NAME + '.local.json'
HELPER = 'native_prepatch_link_v3.inc'
API = 'zonetool::t7_prepatch_link_v3'
SCHEMA = 'iw7.t7-prepatch-link-observation/3'
BUILD_SCHEMA = 'iw7.t7-prepatch-link-build/3'
PINS = {
    base.HELPER: (15785, '0309b81376d3708cc8de43d297b43fbdfbdd535120e0ad054c157735c2c7457a'),
    'prepare_prepatch_reference.py': (3665, '89f3f26699f1240400c4bd96f2987963374658e55a8501cab7dc2543a84ceace'),
    HELPER: (15827, 'cf839e18a68adb4ed3aae82d683ef110ab595fa8c172584e47ca4d11bb8db48d'),
}
BASE_PLAN = (303783, '0aca63cb09e8ecfc96dee34e1fdf94f8cb66e400f8a190ffdefd38bec3a2c549')
BASE_MAIN = (14524, 'e719365c5a7f407218a7218bd9c7090421934042c34a9f163d9a8e3d42ee1e28')
MAIN = (14469, '84cde2924df0a0553dd2cddb0ca173aed54af43d6874b06718c01d1a6cec4989')
RETAINED_MAIN = base.RETAINED_MAIN


def wire_main(source):
    base.require_pin(source.encode('utf-8'), BASE_MAIN, 'V3 immutable wired V2 main')
    here = Path(__file__).resolve().parent
    for name,pin in PINS.items():
        base.require_pin((here/name).read_bytes().replace(b'\r\n',b'\n'),pin,name)
    if source.count(base.API) != 10 or source.count(base.HELPER) != 1:
        raise ValueError('Frozen V2 wiring differs')
    rendered = source.replace(base.API,API).replace(base.HELPER,HELPER)
    base.require_pin(rendered.encode('utf-8'),MAIN,'V3 main')
    return rendered


def prepared_main(plan_raw,read):
    base.require_pin(plan_raw,BASE_PLAN,'V3 base V2 plan')
    path = Path(json.loads(plan_raw)['PreparedRoot'])/'main.cpp'
    raw = read(path,64*1024,BASE_MAIN[1])
    base.require_pin(raw,BASE_MAIN,'V3 base V2 main')
    return wire_main(raw.decode('utf-8')).encode('utf-8'),path


def marker():
    return {'Schema':BUILD_SCHEMA,'SourceProfile':NAME,
            'RetainedMainBytes':RETAINED_MAIN[0],'RetainedMainSHA256':RETAINED_MAIN[1],
            'BaseMainBytes':BASE_MAIN[0],'BaseMainSHA256':BASE_MAIN[1],
            'MainBytes':MAIN[0],'MainSHA256':MAIN[1],
            'HelperBytes':PINS[HELPER][0],'HelperSHA256':PINS[HELPER][1]}
