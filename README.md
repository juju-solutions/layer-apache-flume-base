# Overview

This is the base layer for the Apache Flume charms.  It will handle installing
the Apache Flume libraries and any dependencies, and provides helpers to
configure Flume.


# Usage

To create a charm layer using this base layer, you need only include it in
a `layer.yaml` file:

```yaml
includes: ['layer:flume-base']
```

This will implicitly include the [reactive base layer][layer-basic], which
you can see for more information on using layers in charms.


# Reactive States

This layer will set the following states:

  * **`flume-base.installed`**  This will be set when the Apache Flume
    libraries are installed.  Once this is set, you can configure Flume
    using the method:

    * `configure_flume(template_data=None)`
      This will render the Flume config from the template file
      `templates/flume.conf.j2` and will pass in the keys and values in the
      `template_data` dict, if given, along with a `config` variable containing
      all of the charm config options.

An example using this layer:

```python
from charmhelpers.core import hookenv
from jujubigdata.utils import DistConfig
from charms.layer.flume_base import Flume

@when('flume-base.installed', 'flume-sink.ready')
def configure(sink):
    flume = Flume(DistConfig())
    flume.configure_flume({
        'agents': sink.agents(),
    })
    flume.start()
    hookenv.status_set('active', 'Ready')
```


# Contact Information

- <bigdata@lists.ubuntu.com>


# Resources

- [Apache Flume home page](http://flume.apache.org/)
- [Apache Flume bug tracker](https://issues.apache.org/jira/browse/flume)
- [Apache Flume mailing lists](https://flume.apache.org/mailinglists.html)
- `#juju` on `irc.freenode.net`

[layer-basic]: https://github.com/juju-solutions/layer-basic
