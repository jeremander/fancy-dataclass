from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import json
from math import inf
from pathlib import Path
from typing import Optional

import pytest
import tomlkit

from fancy_dataclass.config import ConfigDataclass, DictConfig
from fancy_dataclass.json import JSONDataclass
from fancy_dataclass.toml import TOMLDataclass


def test_config_dataclass():
    """Tests behavior of ConfigDataclass."""
    @dataclass
    class MyConfig(ConfigDataclass):
        x: int = 1
        y: str = 'a'
    assert MyConfig.get_config() is None
    cfg = MyConfig()
    assert MyConfig.get_config() is None
    cfg.update_config()
    assert MyConfig.get_config() is cfg
    cfg2 = MyConfig()
    assert MyConfig.get_config() is not cfg2
    assert MyConfig.get_config() == cfg2
    cfg2.y = 'b'
    assert cfg2 != cfg
    with cfg2.as_config():
        assert MyConfig.get_config() is cfg2
        # updating instance field affects the global config
        cfg2.y = 'c'
        assert MyConfig.get_config().y == 'c'
    assert MyConfig.get_config() == cfg
    MyConfig.clear_config()
    assert MyConfig.get_config() is None
    with cfg2.as_config():
        assert MyConfig.get_config() is cfg2
    assert MyConfig.get_config() is None
    @dataclass
    class OuterConfig(ConfigDataclass):
        inner: MyConfig
        z: float = 3.14
    outer = OuterConfig(cfg)
    assert outer.inner is cfg
    assert OuterConfig.get_config() is None
    outer.update_config()
    assert OuterConfig.get_config() == outer
    # updating outer does not influence nested class's singleton instance
    assert MyConfig.get_config() is None
    # inner instance can update its own singleton
    outer.inner.update_config()
    assert MyConfig.get_config() is outer.inner
    cfg2.update_config()
    assert MyConfig.get_config() != outer.inner
    assert MyConfig.get_config() is cfg2
    assert OuterConfig.get_config().inner == outer.inner

def test_inner_plain(tmpdir):
    """Tests nested dataclass where the inner dataclass is a regular dataclass, not a ConfigDataclass."""
    @dataclass
    class Inner:
        x: int = 1
    @dataclass
    class Outer(ConfigDataclass):
        inner: Inner
        y: str = 'a'
    assert Outer.get_config() is None
    cfg = Outer(Inner())
    cfg.update_config()
    assert Outer.get_config() is cfg
    cfg.inner.x = 2
    assert Outer.get_config().inner.x == 2
    inner = cfg.inner
    inner.x = 3
    assert Outer.get_config().inner.x == 3
    inner_copy = deepcopy(inner)
    inner_copy.x = 4
    assert Outer.get_config().inner.x == 3
    cfg.inner = inner_copy
    assert Outer.get_config().inner.x == 4
    with Outer(Inner(x=5)).as_config():
        assert Outer.get_config().inner.x == 5
    assert Outer.get_config().inner.x == 4
    toml_str = 'y = "a"\n[inner]\nx = 1\n'
    cfg_path = tmpdir / 'test.toml'
    Path(cfg_path).write_text(toml_str)
    Outer.load_config(cfg_path)
    assert Outer.get_config() == Outer(Inner())

def test_dict_config():
    """Tests behavior of DictConfig."""
    assert DictConfig.get_config() is None
    class MyConfig(DictConfig):
        ...
    assert MyConfig.get_config() is None
    cfg = MyConfig()
    assert MyConfig.get_config() is None
    cfg.update_config()
    assert MyConfig.get_config() is cfg
    cfg['a'] = 1
    assert MyConfig.get_config()['a'] == 1
    cfg2 = MyConfig()
    with cfg2.as_config():
        assert MyConfig.get_config() is cfg2
        assert MyConfig.get_config() == {}
    assert MyConfig.get_config() is cfg
    cfg2.update_config()
    assert MyConfig.get_config() is cfg2

def test_json(tmpdir):
    """Tests JSON conversion of ConfigDataclass."""
    dt = datetime.now()
    @dataclass
    class JSONConfig1(ConfigDataclass):  # defaults not suppressed, by default
        x: float = inf
        y: datetime = dt
    @dataclass
    class JSONConfig2(JSONConfig1, suppress_defaults=True):
        ...
    @dataclass
    class JSONConfig3(JSONConfig1, JSONDataclass):
        ...
    JSONConfig4 = JSONDataclass.wrap_dataclass(JSONConfig1)
    outfile = tmpdir / 'test.json'
    obj1 = JSONConfig1()
    obj2 = JSONConfig2()
    obj3 = JSONConfig3()
    obj4 = JSONConfig4()
    d = {'x': inf, 'y': dt}
    d_json = {'x': inf, 'y': dt.isoformat()}
    assert obj1.to_dict() == d
    assert obj2.to_dict() == {}
    assert obj3.to_dict() == d
    assert obj4.to_dict() == d
    with open(outfile, 'w') as f:
        obj4.to_json(f)
    with open(outfile) as f:
        assert json.load(f) == d_json
    for obj in [obj1, obj2, obj3, obj4]:
        assert obj.y == dt
        assert type(obj).load_config(outfile) == obj
    for obj in [obj3, obj4]:
        with open(outfile) as f:
            assert type(obj).from_json(f) == obj
    # test that loading config sets it globally
    JSONConfig1.clear_config()
    assert JSONConfig1.get_config() is None
    obj = JSONConfig1.load_config(outfile)
    assert JSONConfig1.get_config() == obj
    # ensure the inner JSON-coerced datetime field gets converted
    @dataclass
    class OuterConfig(ConfigDataclass):
        inner: JSONConfig1
    d_json_outer = {'inner': d_json}
    with open(outfile, 'w') as f:
        json.dump(d_json_outer, f)
    obj = OuterConfig.load_config(outfile)
    assert obj.inner.y == dt

def test_toml(tmpdir):
    """Tests TOML conversion of ConfigDataclass."""
    dt = datetime.now()
    @dataclass
    class TOMLConfig1(ConfigDataclass):
        x: float = inf
        y: datetime = dt
        z: Optional[str] = None
    @dataclass
    class TOMLConfig2(TOMLConfig1, TOMLDataclass):
        ...
    outfile = tmpdir / 'test.toml'
    obj1 = TOMLConfig1()
    obj2 = TOMLConfig2()
    d = {'x': inf, 'y': dt, 'z': None}
    assert obj1.to_dict() == d
    assert obj2.to_dict() == d
    with open(outfile, 'w') as f:
        obj2.to_toml(f)
    with open(outfile) as f:
        # null value is not stored in the TOML
        assert tomlkit.load(f) == {'x': inf, 'y': dt}
    assert TOMLConfig1.load_config(outfile) == obj1
    assert TOMLConfig2.load_config(outfile) == obj2
    with open(outfile) as f:
        assert TOMLConfig2.from_toml(f) == obj2

def test_load_config(tmpdir):
    """Tests config file loading."""
    @dataclass
    class MyConfig(ConfigDataclass):
        ...
    cfg = MyConfig()
    outfile = tmpdir / 'test'
    with pytest.raises(ValueError, match='has no extension'):
        _ = MyConfig.load_config(outfile)
    outfile = tmpdir / 'test.fake'
    with pytest.raises(ValueError, match="unknown config file extension '.fake'"):
        _ = MyConfig.load_config(outfile)
    outfile = tmpdir / 'test.json'
    with pytest.raises(FileNotFoundError, match='No such file or directory'):
        _ = MyConfig.load_config(outfile)
    Path(outfile).touch()
    # empty file is invalid JSON
    with pytest.raises(json.JSONDecodeError, match='Expecting value'):
        _ = MyConfig.load_config(outfile)
    assert MyConfig.get_config() is None
    with open(outfile, 'w') as f:
        json.dump({}, f)
    assert MyConfig.load_config(outfile) == cfg
    assert MyConfig.get_config() == cfg
    with open(outfile, 'w') as f:
        json.dump({'x': 5}, f)
    # extra keys are ignored when loading
    assert MyConfig.load_config(outfile) == cfg
    outfile = tmpdir / 'test.toml'
    Path(outfile).touch()
    # empty file is valid TOML
    assert MyConfig.load_config(outfile) == cfg
    with open(outfile, 'w') as f:
        f.write('x = 5')
    assert MyConfig.load_config(outfile) == cfg
