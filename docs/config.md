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

🚧 **Under construction** 🚧

<!--
- By default ConfigDataclass cannot write config files, only read them. To write, subclass JSONDataclass or TOMLDataclass.
- Structured vs. unstructured configs
 -->

<style>
.md-sidebar--secondary {
    display: none !important;
}

.md-main__inner .md-content {
    max-width: 45rem;
}
</style>
