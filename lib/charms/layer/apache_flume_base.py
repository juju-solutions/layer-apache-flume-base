import os
import re
import signal
from subprocess import Popen, check_output

import jujuresources

from jujubigdata import utils
from charms.templating.jinja2 import render


# Main Flume class for callbacks
class Flume(object):
    """
    This class manages the deployment steps of Flume agent.

    :param DistConfig dist_config: The configuration container object needed.
    :param String user: The username of the user that will start the service.
    """

    def __init__(self, dist_config=None):
        self.dist_config = dist_config or utils.DistConfig()
        self.resources = {
            'flume': 'flume-%s' % utils.cpu_arch(),
        }
        zk_res = 'zookeeper-%s' % utils.cpu_arch()
        if jujuresources.resource_defined(zk_res):
            self.resources['zookeeper'] = zk_res
        self.verify_resources = utils.verify_resources(
            *self.resources.values())

    @property
    def config_file(self):
        return self.dist_config.path('flume_conf') / 'flume.conf'

    def install(self):
        '''
        Create the users and directories.
        This method is to be called only once.

        :param bool force: Force the installation execution even if this
                           is not the first installation attempt.
        '''
        jujuresources.install(self.resources['flume'],
                              destination=self.dist_config.path('flume'),
                              skip_top_level=True)
        if 'zookeeper' in self.resources:
            # apache-flume-kafka needs ZK libs
            jujuresources.install(
                self.resources['zookeeper'],
                destination=self.dist_config.path('zookeeper'),
                skip_top_level=True)
        self.dist_config.add_users()
        self.dist_config.add_dirs()
        self.dist_config.add_packages()
        self.setup_flume_config()

    def setup_flume_config(self):
        '''
        copy the default configuration files to flume_conf property
        defined in dist.yaml
        '''
        default_conf = self.dist_config.path('flume') / 'conf'
        flume_conf = self.dist_config.path('flume_conf')
        flume_conf.rmtree_p()
        default_conf.copytree(flume_conf)
        # Now remove the conf included in the tarball and symlink our real conf
        default_conf.rmtree_p()
        flume_conf.symlink(default_conf)

        flume_env = flume_conf / 'flume-env.sh'
        if not flume_env.exists():
            (flume_conf / 'flume-env.sh.template').copy(flume_env)

        flume_conf_src = flume_conf / 'flume-conf.properties.template'
        flume_conf_dst = flume_conf / 'flume.conf'
        if not flume_conf_dst.exists():
            flume_conf_src.copy(flume_conf_dst)

        flume_log4j = self.dist_config.path('flume_conf') / 'log4j.properties'
        flume_logs = self.dist_config.path('flume_logs')
        utils.re_edit_in_place(flume_log4j, {
            r'^flume.log.dir.*': 'flume.log.dir={}'.format(flume_logs),
        })

    def configure_flume(self, template_data=None):
        '''
        handle configuration of Flume and setup the environment
        '''
        render(
            source='flume.conf.j2',
            target=self.config_file,
            context=dict({
                'dist_config': self.dist_config,
            }, **(template_data or {})),
            filters={
                'agent_list': lambda agents, prefix='': ','.join([
                    '%s%s' % (prefix, a['name']) for a in agents
                ]),
            },
        )

        flume_bin = self.dist_config.path('flume') / 'bin'
        java_symlink = check_output(
            ["readlink", "-f", "/usr/bin/java"]).decode('utf8')
        java_home = re.sub('/bin/java', '', java_symlink).rstrip()
        with utils.environment_edit_in_place('/etc/environment') as env:
            if flume_bin not in env['PATH']:
                env['PATH'] = ':'.join([env['PATH'], flume_bin])
            env['FLUME_CONF_DIR'] = self.dist_config.path('flume_conf')
            env['FLUME_CLASSPATH'] = self.dist_config.path('flume') / 'lib'
            env['FLUME_HOME'] = self.dist_config.path('flume')
            env['JAVA_HOME'] = java_home

    def configure_zookeeper(self):
        flume_env = self.dist_config.path('flume_conf') / 'flume-env.sh'
        zk_path = self.dist_config.path('zookeeper')
        utils.re_edit_in_place(flume_env, {
            r'.*FLUME_CLASSPATH.*': 'FLUME_CLASSPATH={}/*'.format(zk_path),
        })

    def init_hdfs(self):
        utils.run_as('hdfs', 'hdfs', 'dfs', '-mkdir', '-p', '/user/flume')
        utils.run_as('hdfs', 'hdfs', 'dfs', '-chown', 'flume', '/user/flume')

    def run_bg(self, user, output_log, command, *args):
        """
        Run a command as the given user in the background.

        :param str user: User to run flume agent
        :param str command: Command to run
        :param list args: Additional args to pass to the command
        """
        parts = [command] + list(args)
        quoted = ' '.join("'%s'" % p for p in parts)
        e = utils.read_etc_env()
        Popen(['su', user, '-c', '{} &> {} &'.format(quoted, output_log)],
              env=e)

    def restart(self, user='flume'):
        # check for a java process with our flume dir in the classpath
        if utils.jps(r'-cp .*{}'.format(self.dist_config.path('flume'))):
            self.stop()
        self.start(user)

    def start(self, user='flume'):
        self.run_bg(
            user, '/var/log/flume/flume.out',
            self.dist_config.path('flume') / 'bin/flume-ng',
            'agent',
            '-c', self.dist_config.path('flume_conf'),
            '-f', self.dist_config.path('flume_conf') / 'flume.conf',
            '-n', 'a1')

    def stop(self):
        flume_path = self.dist_config.path('flume')
        flume_pids = utils.jps(r'-cp .*{}'.format(flume_path))
        for pid in flume_pids:
            os.kill(int(pid), signal.SIGKILL)

    def cleanup(self):
        self.dist_config.remove_users()
        self.dist_config.remove_dirs()
