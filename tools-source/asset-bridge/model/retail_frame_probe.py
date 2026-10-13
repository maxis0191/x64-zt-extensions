"""Read retained IW7 XMB metadata and prepare a selective console probe.

Source profile: x64-zt fab9358, xmodel::dump and assetmanager::dumper.
No tool/game launch, extraction, asset mutation or whole-XMB validation.
"""
import argparse
import json
from pathlib import Path
import re
import struct

from packed_frame_audit import PrefixReader, read_bounded, require, sha


class ModelPrefixReader(PrefixReader):
    def __init__(self, data):
        super().__init__(data)
        self.entries = []

    def field(self, kind, width=1, count=1):
        tag = self.take(1)[0]
        if tag == 9:
            index, offset = struct.unpack('<II', self.take(8))
            require(index < len(self.entries), 'Forward/invalid alias')
            old_kind, old_width, value = self.entries[index]
            require(old_kind == kind and old_width == width, 'Cross-type alias unsupported')
            if kind == 8:
                require((offset+count)*width <= len(value), 'Alias outside source array')
                return value[offset*width:(offset+count)*width]
            require(offset == 0, 'Interior name alias unsupported')
            return value
        require(tag == kind, 'Unexpected field tag')
        present = self.take(1)[0]
        require(present in (0, 1), 'Invalid presence byte')
        if not present:
            return None
        if kind == 8:
            actual = struct.unpack('<I', self.take(4))[0]
            require(actual == count and 0 < actual <= 4096, 'Unexpected bounded array count')
            value = self.take(width*actual)
        else:
            end = self.data.find(b'\0', self.offset, self.offset+513)
            require(end >= self.offset, 'Unterminated bounded name')
            value = self.take(end-self.offset+1)[:-1].decode('ascii')
            require(re.fullmatch(r'[A-Za-z0-9_./\\, +\-]+', value) is not None, 'Unsafe asset name')
        self.entries.append((kind, width, value))
        return value


def model_metadata(path):
    data = read_bounded(path)
    r = ModelPrefixReader(data)
    header = r.field(8, 736)
    require(header is not None, 'Missing XModel header')
    name = r.field(6)
    require(name is not None, 'Missing XModel name')
    nb, roots, reactive = header[20:23]
    clients, surfaces = struct.unpack_from('<HH', header, 24)
    collisions = struct.unpack_from('<H', header, 32)[0]
    bones = nb+clients
    require(0 <= roots <= bones <= 4096 and 0 < surfaces <= 4096 and header[11] <= 6,
            'Invalid model dimensions')
    for _ in range(bones):
        r.field(6)
    for width, count in ((1,bones-roots),(8,bones-roots),(12,bones-roots),
                         (1,nb),(32,bones),(16,reactive),(16,1),(36,collisions),
                         (28,bones),(2,surfaces),(8,surfaces)):
        r.field(8, width, count)
    materials = [r.field(7) for _ in range(surfaces)]
    lods = []
    for index in range(6):
        ref = r.field(7)
        num, first = struct.unpack_from('<HH', header, 224+64*index+4)
        require(first+num <= surfaces, 'LOD material range outside model')
        if ref is not None:
            require(index < header[11], 'Surface reference outside active LOD range')
            lods.append({'index':index, 'xmodelsurfs':ref, 'surfaces':num,
                         'first_material':first, 'materials':materials[first:first+num]})
    return {'bytes':len(data), 'sha256':sha(data), 'name':name, 'num_lods':header[11],
            'bones':bones, 'material_slots':surfaces, 'lods':lods,
            'prefix_bytes':r.offset, 'remaining_bytes_not_audited':len(data)-r.offset}


def plan(model, material):
    result = model_metadata(model)
    material_data = read_bounded(material)
    metadata = json.loads(material_data)
    techset = metadata['techniqueSet->name']
    require(re.fullmatch(r'[A-Za-z0-9_]+', techset) is not None, 'Unsafe techset name')
    # The source file is the retained material named in these exact model slots.
    material_name = material.parent.name+'/'+material.stem
    require(material.suffix == '.json' and material_name == 'mopw/character_park_clown_zombie_shoes',
            'Only the retained shoes material is in this probe profile')
    matches = [lod for lod in result['lods'] if material_name in lod['materials']]
    require(matches, 'Requested material is not present in parsed LOD slots')
    # Lowest retained LOD with this material: smallest likely vertex payload;
    # actual XSB size is unknown until selective extraction and is not asserted.
    selected = max(matches, key=lambda lod: lod['index'])
    require(re.fullmatch(r'[A-Za-z0-9_]+', selected['xmodelsurfs']) is not None,
            'Unsafe console surface name')
    return {'schema':'iw7.retail-packed-frame-probe-plan/1', 'executed':False,
            'source_pin':'fab935826c898806855376662a8a03317b3ad8f1',
            'xmodel':result,
            'material':{'name':material_name, 'bytes':len(material_data), 'sha256':sha(material_data),
                        'techset':techset},
            'selected_lod':selected['index'],
            'first_console_command_after_zone_load':'dumpasset techset '+techset,
            'optional_console_surface_command':'dumpasset xmodelsurfs '+selected['xmodelsurfs'],
            'shader_name_known':False,
            'next_shader_step':'Read the dumped technique/pass and vertex declaration; resolve its exact vertexshader name before any selective shader extraction.',
            'post_registration_shader_program_available':None,
            'retail_decoder_verified':False, 'whole_xmb_validated':False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True, type=Path)
    parser.add_argument('--material', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(plan(args.model, args.material), indent=2))
