"""Fixed two-function prepatch V2; no engine or fastfile reads at preparation."""
import hashlib
import json
from pathlib import Path
import prepare_prepatch

NAME = 't7-prepatch-reference-v2'
OPTION = '-' + NAME
REPORT = NAME + '.local.json'
HELPER = 'native_prepatch_reference_v2.inc'
API = 'zonetool::t7_prepatch_reference_v2'
SCHEMA = 'iw7.t7-prepatch-reference-observation/2'
BUILD_SCHEMA = 'iw7.t7-prepatch-reference-build/2'
PINS = {
    'native_prepatch_probe.inc': (16281, 'a9f458d2783c845af6958c896bda07fa4b92a5ea23a14c9e5d1201fe234a2018'),
    'prepare_prepatch.py': (3078, '162763ab503a7971bc56753e3aba9fc1c76bf181881f9bddf45718456467e129'),
    HELPER: (15785, '0309b81376d3708cc8de43d297b43fbdfbdd535120e0ad054c157735c2c7457a'),
}
BASE_MAIN = (13160, '55081db20863f291f4f1fea8c1c995995e5e548b56acf043201fbb2e361f3934')
MAIN = (14524, 'e719365c5a7f407218a7218bd9c7090421934042c34a9f163d9a8e3d42ee1e28')
RETAINED_MAIN = (12854, '40de5fda829cec32a5d75359f58e69c84db7d8ee54f198cf6befa2a6ebe6f86e')
RETAINED_PLAN = (292575, '422e79898fa2b16defc8193182fe146e2db5d73aeb4516c2bd2aaf87c409c4de')
RETAINED_RECEIPT = (26199, 'af6beecf7a8892e16266a7641d2799f665f86fa8ad7c40c61561b782534f7897')
RETAINED_PAYLOADS = {
    'zonetool.cpp': (35974, '106ccdb4aec584184132c309c117f778d504ca9e64e8a821d23bfecc83bc8635'),
    'common/xpak.cpp': (8236, 'ab07824efb64d5535fe56a428c9fee316b5141adbcfd87b6999c352f0de8dde8'),
    'common/xpak.hpp': (224, 'd5ae59be9a6a30c9dbc0838fc4909cffe577314b5fa66817787fc3ee910635b7'),
    't7_iw7_resident_model.hpp': (13444, '6d2da3d4f7c3d0686909dc488f3d176ee2dd250e8d43d9a3cd9bcfa701482777'),
    't7_asset_name.hpp': (1945, '171a3834a1e4c2321347850d350d9683eee4dec7715f3fdc95d5cb12c4adee65'),
    'test_t7_asset_name.cpp': (2170, 'b77aee23860f07c9dee92063a1b322d7964da77880990cdd6dc9064f8bb4ddfc'),
}


def require_pin(raw, pin, label):
    if not isinstance(raw, bytes) or (len(raw), hashlib.sha256(raw).hexdigest()) != pin:
        raise ValueError('Exact prepatch V2 ' + label + ' required')


def wire_main(source):
    require_pin(source.encode('utf-8'), BASE_MAIN, 'base main')
    here = Path(__file__).resolve().parent
    for name, pin in PINS.items():
        require_pin((here / name).read_bytes().replace(b'\r\n', b'\n'), pin, name)
    # Reuse all V1 rendezvous/refusal/exit wiring, changing only its fixed API.
    rendered = prepare_prepatch.wire_main(source)
    if rendered.count(prepare_prepatch.API) != 10 or rendered.count(prepare_prepatch.HELPER) != 1:
        raise ValueError('Frozen prepatch V1 wiring differs')
    rendered = rendered.replace(prepare_prepatch.API, API).replace(prepare_prepatch.HELPER, HELPER)
    require_pin(rendered.encode('utf-8'), MAIN, 'wired main')
    return rendered


def marker():
    return {'Schema': BUILD_SCHEMA, 'SourceProfile': NAME,
            'RetainedMainBytes': RETAINED_MAIN[0], 'RetainedMainSHA256': RETAINED_MAIN[1],
            'BaseMainBytes': BASE_MAIN[0], 'BaseMainSHA256': BASE_MAIN[1],
            'MainBytes': MAIN[0], 'MainSHA256': MAIN[1],
            'HelperBytes': PINS[HELPER][0], 'HelperSHA256': PINS[HELPER][1]}


def retained_payloads(plan_raw, receipt_raw, read):
    """Reuse only the six text inputs of the frozen successful C sub-stages."""
    require_pin(plan_raw, RETAINED_PLAN, 'retained C plan')
    require_pin(receipt_raw, RETAINED_RECEIPT, 'retained C receipt')
    prepared = Path(json.loads(plan_raw)['PreparedRoot'])
    payloads = {}
    for name,pin in RETAINED_PAYLOADS.items():
        raw = read(prepared/name,64*1024,pin[1])
        require_pin(raw,pin,'retained '+name)
        payloads['prepared/'+name] = raw
    return payloads
