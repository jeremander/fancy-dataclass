<!-- markdownlint-disable MD052 -->

The [`ConfigDataclass`][fancy_dataclass.config.ConfigDataclass] mixin provides a mechanism for storing a global configuration object that can be used anywhere within your program.

It can also load configurations from a file. The file types currently supported are [JSON](https://en.wikipedia.org/wiki/JSON) and [TOML](https://en.wikipedia.org/wiki/TOML).

## Usage Example

Define a `ConfigDataclass` representing a website configuration. This will include several nested dataclasses for distinct sections of the configuration.

```python
from dataclasses import dataclass

from fancy_dataclass import ConfigDataclass


@dataclass
class ServerConfig:
    hostname: str
    port: int

@dataclass
class DatabaseConfig:
    username: str
    password: str

@dataclass
class WebsiteConfig(ConfigDataclass):
    title: str
    author: str
    description: str
    server: ServerConfig
    database: DatabaseConfig
```

Now suppose you have a configuration file you want to load from, `website_config.toml`, whose schema matches the `WebsiteConfig` class:

```toml
# Website Configuration

title = "My Awesome Website"
author = "Webby McWebface"
description = "A simple example of a TOML configuration file for a website."

[server]
hostname = "localhost"
port = 8080

[database]
username = "admin"
password = "password123"
```

You can load the config file to initialize the configurations as a globally accessible object:

```python
# load from file (only need to do this once)
WebsiteConfig.load_config('website_config.toml')
```

Then, at any point in your program, you can fetch the configs like so:

```python
>>> cfg = WebsiteConfig.get_config()

# then do stuff with the configs...
>>> print(cfg.title)
My Awesome Website
```

The advantage of this is that you don't have to pass the configuration object around as a parameter or store it as a global variable.

You can also update the configurations:

```python
def print_current_username():
    """Helper function to print out current database username."""
    global_cfg = WebsiteConfig.get_config()
    print(global_cfg.database.username)
```

```python
>>> print_current_username()
admin

# update the config by mutating a local reference
>>> cfg.database.username = 'test1'
>>> print_current_username()
test1

# update the config with another object
>>> from copy import deepcopy
>>> cfg2 = deepcopy(cfg)
>>> cfg2.database.username = 'test2'
>>> cfg2.update_config()

# update the global config
>>> cfg2.update_config()
>>> print_current_username()
test2
```

Sometimes it is useful to modify the configs temporarily:

```python
>>> print_current_username()
test2
>>> cfg.database.username = 'temporary'

# temporarily update global config with the local version
>>> with cfg.as_config():
        print_current_username()
temporary

# global config reverts back to its value before 'as_config' was called
>>> print_current_username()
test2
```

## Details

For configurations with a specified schema, create a subclass of [`ConfigDataclass`][fancy_dataclass.config.ConfigDataclass] instantiating your schema.

The following methods can then be used:

- [`load_config`][fancy_dataclass.config.FileConfig.load_config]: load configs from a JSON or TOML file
- [`get_config`][fancy_dataclass.config.Config.get_config]: get the global config object
- [`clear_config`][fancy_dataclass.config.Config.clear_config]: set the global config to `None`
- [`update_config`][fancy_dataclass.config.Config.update_config]: set the global config to a particular object
- [`as_config`][fancy_dataclass.config.Config.as_config]: context manager to temporarily change the global config to a particular object

For configurations _without_ a specified schema, you can use [`DictConfig`][fancy_dataclass.config.DictConfig] instead. This has the same interface as `ConfigDataclass`, except you do not need to subclass it or specify a dataclass schema. Instead, it can load the contents of a JSON or TOML file into a regular Python dict, which you can access with `get_config`.

By default, `ConfigDataclass` and `DictConfig` cannot write config files, only read them. To write, you can subclass [`JSONDataclass`](json.md) or [`TOMLDataclass`](toml.md).

<style>
.md-sidebar--secondary {
    display: none !important;
}

.md-main__inner .md-content {
    max-width: 45rem;
}
</style>
