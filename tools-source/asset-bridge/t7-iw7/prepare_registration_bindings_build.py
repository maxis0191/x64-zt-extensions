"""Finite CPP39 -> seven-binding build-source/RSP transition. No native execution."""
import hashlib
import json
from pathlib import Path
import prepare_cli
import prepare_material_parts as parts
import prepare_image_registration_metadata as registration
import prepare_incoming_image_metadata as incoming
import prepare_registration_material_bindings as producer

HERE = Path(__file__).resolve().parent
CONTRACT = 'registration-bindings-build-source-contract.json'
BASELINE = 'bindings_registration_baseline_fixture.cpp'
COMBINED = 'registration_bindings_combined_fixture.cpp'
VALIDATOR = 'RegistrationBindingsBuild.Source.ps1'
STAGE_NAMES = ['registration-fixture-compile','registration-fixture-test','main','zonetool11','link']
SOURCE_PINS = {
    'prepare_incoming_image_metadata.py': (10046,'3daefdb75f16ecc951a467df91e5b4b5b51c54916f2f2e9c2b9f692485b09ed3'),
    producer.CONTRACT: (5391,'d60f0e33d9dddb69656744f6481ba32ced1a7a040d75ff913908192297e3c9a6'),
    'prepare_registration_material_bindings.py': (10618,'87b6e3d033cbb9e68ad9a59b25d2548adce1295b84b0ea9877eef5d68126384b'),
    producer.FIXTURE: (7594,'51ec0ec81c65e7f3a602e00b094ef87c74fda255aa32f54d0331c8fa697f9fd9'),
}


def selected(args):
    value = getattr(args,'image_registration_bindings_v1',False)
    parts.require(type(value) is bool, 'Explicit registration bindings build boolean required')
    parts.require(not value or (getattr(args,'image_registration_metadata_v1',False) is True and
        getattr(args,'image_incoming_header_v1',False) is False),
        'Registration bindings requires its exclusive CPP39 base, not incoming')
    return value


def baseline_source(raw):
    parts.require_pin(raw,incoming.BASE_FIXTURE,'immutable legacy registration fixture39')
    once = prepare_cli.helper.once
    text = once(raw.decode(), '#include "selected_image_registration_observer.hpp"',
                '#include "'+producer.OBSERVER_NAME+'"')
    return once(text,'int main()','int original_registration_fixture_main()')


def combined_source(raw):
    parts.require_pin(raw,SOURCE_PINS[producer.FIXTURE],'immutable bindings fixture41')
    once = prepare_cli.helper.once
    text = once(raw.decode(), '#define main original_material_fixture_main\n'
        '#include "selected_material_observation_fixture.cpp"\n#undef main\n'
        '#include "selected_image_material_bindings_observer.hpp"', '#include "'+BASELINE+'"')
    text = once(text,'namespace provenance = t7::selected_image_provenance;\n'
        'namespace capture = t7::registration_image_header_capture;\n','')
    # Avoid the legacy anonymous-namespace helpers and their overloaded address.
    text = text.replace('setup(', 'setup_bindings(')
    text = once(text,'provenance::memory_state memory(', 'provenance::memory_state bindings_memory(')
    text = text.replace('&memory','&bindings_memory')
    return once(text,'    try\n    {\n', '    try\n    {\n'
        '        if (original_registration_fixture_main() != 0) return 1;\n'
        '        checks = 0; // Separate actual 39 and 41 counts and stdout markers.\n')


def source_contract(read):
    raw = read(HERE/CONTRACT,16*1024)
    c = json.loads(raw)
    keys={'schema','source_profile','native_source_commit','source_only_pending','cpp_qualified','native_observed','ready',
        'legacy_checks','new_checks','total_checks','payload_limit_bytes','fixture_stdout','stage_names','producer','generated','source_pins','validator'}
    parts.require(type(c) is dict and set(c) == keys and c.get('schema') == 'iw7.t7-registration-bindings-build-source/1' and
        c.get('source_profile') == producer.NAME and c.get('native_source_commit') ==
        'fab935826c898806855376662a8a03317b3ad8f1' and c.get('source_only_pending') is True and
        all(c.get(key) is False for key in ('cpp_qualified','native_observed','ready')),
        'Exact pending registration bindings build source contract required')
    for key,value in (('legacy_checks',39),('new_checks',41),('total_checks',80),('payload_limit_bytes',448*1024)):
        parts.require(type(c.get(key)) is int and c[key] == value,'Exact typed bindings fixture scope required')
    parts.require(c.get('fixture_stdout') ==
        'IW7_T7_REGISTRATION_HEADER_CHECKS=39\nIW7_T7_REGISTRATION_BINDINGS_CHECKS=41\n',
        'Exact separate legacy/new fixture markers required')
    parts.require(type(c.get('generated')) is dict and type(c.get('source_pins')) is dict and
        set(c['source_pins']) == set(SOURCE_PINS)|{'prepare_registration_bindings_build.py',producer.MODULE,producer.ENTRY,registration.FIXTURE} and
        type(c.get('producer')) is dict and set(c['producer']) == {'main','cli'} and c.get('stage_names') == STAGE_NAMES,
        'Closed generated source and existing five-stage order required')
    for pin in (*c['source_pins'].values(),c['validator'],*c['producer'].values(),*c['generated'].values()):
        parts.require(type(pin) is dict and set(pin) == {'bytes','sha256'} and type(pin['bytes']) is int and
            0 < pin['bytes'] <= 192*1024 and type(pin['sha256']) is str and len(pin['sha256']) == 64,
            'Required typed Source sub-pin cannot be NULL or coerced')
    return c


def transition(main,cli,registration_observer,registration_args,read,prepared):
    """Same five-stage build, replacing only its fixture token and owned sources."""
    old_fixture = str(HERE/registration.FIXTURE)
    parts.require(type(registration_args) is list and all(type(x) is str for x in registration_args) and
        registration_args.count(old_fixture) == 1,'Exact one typed legacy fixture compiler token required')
    read(HERE/'prepare_registration_bindings_build.py',32*1024)
    c = source_contract(read)
    validator = c['validator']
    parts.require(type(validator) is dict and set(validator) == {'bytes','sha256'} and
        type(validator['bytes']) is int and 0 < validator['bytes'] <= 32*1024 and
        type(validator['sha256']) is str and len(validator['sha256']) == 64,'Bounded Source validator pin required')
    raw = read(HERE/VALIDATOR,32*1024,validator['sha256']).replace(b'\r\n',b'\n')
    parts.require_pin(raw,(validator['bytes'],validator['sha256']),VALIDATOR)
    for name,pin in SOURCE_PINS.items():
        raw = read(HERE/name,32*1024,pin[1]).replace(b'\r\n',b'\n')
        parts.require_pin(raw,pin,'frozen producer '+name)
    parts.require_pin(registration_observer,incoming.BASE_OBSERVER,'exact CPP39 observer input')
    base_main,base_cli = main,cli
    main,cli = producer.overlay(main,cli,read)
    _,files,observer,capture,members = producer.inputs(read)
    parts.require(observer == registration_observer,'Supplied registration observer differs')
    old = read(HERE/registration.FIXTURE,32*1024,incoming.BASE_FIXTURE[1]).replace(b'\r\n',b'\n')
    generated = {
        'prepared/'+producer.CAPTURE_NAME: producer.capture_source(capture,members).encode(),
        'prepared/'+producer.OBSERVER_NAME: producer.observer_source(observer).encode(),
        'prepared/'+BASELINE: baseline_source(old).encode(),
        'prepared/'+COMBINED: combined_source(files[producer.FIXTURE]).encode(),
    }
    for relative,value in generated.items():
        pin = c['generated'].get(relative)
        parts.require(type(pin) is dict and set(pin) == {'bytes','sha256'} and
            type(pin['bytes']) is int and 0 < pin['bytes'] <= 32*1024 and
            type(pin['sha256']) is str and len(pin['sha256']) == 64,
            'Typed bounded generated bindings source pin required')
        parts.require_pin(value,(pin['bytes'],pin['sha256']),relative)
    parts.require(set(c['generated']) == set(generated),'Closed generated bindings source set required')
    args = registration_args.copy()
    args[args.index(old_fixture)] = str(prepared/COMBINED)
    marker = {'Schema':'iw7.t7-registration-bindings-build/1','SourceProfile':producer.NAME,
        'SourceOnlyPending':True,'CPPQualified':False,'NativeObserved':False,'Ready':False,
        'LegacyFixtureChecks':39,'BindingsFixtureChecks':41,'TotalFixtureChecks':80,
        'ExpectedFixtureStdout':c['fixture_stdout']}
    for prefix,values in (('Base',(base_main,base_cli)),('',(main,cli))):
        for role,value in zip(('Main','CLI'),values):
            marker[prefix+role+'Bytes'] = len(value.encode())
            marker[prefix+role+'SHA256'] = hashlib.sha256(value.encode()).hexdigest()
    return main,cli,marker,generated,args


def extend_profile(profile,prepared,pin):
    """Use the caller's existing exact input bindings; never open an artifact."""
    parts.require(type(profile.get('SourceOnlyPending')) is bool,'Preserve explicit base H-proof status')
    profile.update(Name=producer.NAME,Option=producer.OPTION,ObservationSchema=producer.SCHEMA,
        BindingsSchema=producer.SCHEMA,BindingsCPPQualified=False,
        BindingsLegacyChecks=39,BindingsFixtureChecks=41,BindingsTotalChecks=80)
    paths = {'BindingsBuildWiring':HERE/'prepare_registration_bindings_build.py',
        'BindingsIncomingWiring':HERE/'prepare_incoming_image_metadata.py',
        'BindingsBuildValidator':HERE/VALIDATOR,
        'BindingsBuildContract':HERE/CONTRACT,'BindingsWiring':HERE/'prepare_registration_material_bindings.py',
        'BindingsContract':HERE/producer.CONTRACT,'BindingsModule':HERE/producer.MODULE,
        'BindingsEntry':HERE/producer.ENTRY,'BindingsFixture':HERE/producer.FIXTURE,
        'BindingsLegacyFixture':HERE/registration.FIXTURE,'BindingsCapture':prepared/producer.CAPTURE_NAME,
        'BindingsObserver':prepared/producer.OBSERVER_NAME,'BindingsBaselineFixture':prepared/BASELINE,
        'BindingsCombinedFixture':prepared/COMBINED,'BindingsResponse':prepared.parent/'registration-fixture.rsp'}
    for role,path in paths.items(): profile[role] = pin(path)
