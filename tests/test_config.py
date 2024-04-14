from dataclasses import dataclass
from datetime import datetime
import json
from math import inf
import shutil

import pytest

from fancy_dataclass.config import ConfigDataclass
from fancy_dataclass.json import JSONDataclass


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
    assert MyConfig.get_config() == cfg2
    assert MyConfig.get_config() is not cfg2
    cfg2.y = 'b'
    assert cfg2 != cfg
    with cfg2.configure():
        assert MyConfig.get_config() is cfg2
        # updating instance field affects the global config
        cfg2.y = 'c'
        assert MyConfig.get_config().y == 'c'
    assert MyConfig.get_config() is cfg
    MyConfig.clear_config()
    assert MyConfig.get_config() is None
    with cfg2.configure():
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
    assert OuterConfig.get_config() is outer
    # updating outer does not influence nested class's singleton instance
    assert MyConfig.get_config() is None
    # inner instance can update its own singleton
    outer.inner.update_config()
    assert MyConfig.get_config() is outer.inner
    cfg2.update_config()
    assert MyConfig.get_config() is not outer.inner
    assert MyConfig.get_config() is cfg2
    assert OuterConfig.get_config().inner is outer.inner

def test_json(tmpdir):
    """Tests JSON conversion of ConfigDataclass."""
    dt = datetime.strptime('2024-01-01', '%Y-%m-%d')
    @dataclass
    class JSONConfig1(ConfigDataclass):
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
    assert obj1.to_dict() == d  # defaults not suppressed for ConfigDataclass by default
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
    assert JSONConfig1.get_config() is obj
    # test extension inference
    outfile2 = tmpdir / 'test2'
    shutil.copy(outfile, outfile2)
    with pytest.raises(ValueError, match='has no extension'):
        _ = JSONConfig1.load_config(outfile2)
    outfile2 = tmpdir / 'test2.fake'
    shutil.copy(outfile, outfile2)
    with pytest.raises(ValueError, match="unknown config file extension '.fake'"):
        _ = JSONConfig1.load_config(outfile2)
    outfile2 = tmpdir / 'test2.JSON'
    shutil.copy(outfile, outfile2)
    assert JSONConfig1.load_config(outfile2) == obj1
    # ensure the inner JSON-coerced datetime field gets converted
    @dataclass
    class OuterConfig(ConfigDataclass):
        inner: JSONConfig1
    d_json_outer = {'inner': d_json}
    with open(outfile, 'w') as f:
        json.dump(d_json_outer, f)
    obj = OuterConfig.load_config(outfile)
    assert obj.inner.y == dt
