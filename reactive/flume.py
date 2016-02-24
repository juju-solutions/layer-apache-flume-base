from charms.reactive import when_not
from charms.reactive import set_state

from charmhelpers.core import hookenv

from jujubigdata.utils import DistConfig

from charms.layer.flume_base import Flume


@when_not('flume-base.installed')
def install_flume():
    flume = Flume(DistConfig())
    if flume.verify_resources():
        hookenv.status_set('maintenance', 'Installing Flume')
        flume.install()
        set_state('flume-base.installed')
