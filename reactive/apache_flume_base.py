from charms.reactive import when_not
from charms.reactive import set_state

from charmhelpers.core import hookenv

from charms.layer.apache_flume_base import Flume


@when_not('flume-base.installed')
def install_flume():
    flume = Flume()
    if flume.verify_resources():
        hookenv.status_set('maintenance', 'Installing Flume')
        flume.install()
        hookenv.status_set('waiting', 'Waiting for Flume to become Ready')
        set_state('flume-base.installed')
