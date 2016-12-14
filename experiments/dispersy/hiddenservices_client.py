#!/usr/bin/env python2
# bartercast_client.py ---
#
# Filename: hiddenservices_client.py
# Description:
# Author: Rob Ruigrok
# Maintainer:
# Created: Wed Apr 22 11:44:23 2015 (+0200)

# Commentary:
#
#
#
#

# Change Log:
#
#
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street, Fifth
# Floor, Boston, MA 02110-1301, USA.
#
#

# Code:

import random
from os import path

from gumby.experiments.dispersymulticlient import MultiDispersyExperimentScriptClient, main, BASE_DIR
import logging
from twisted.python.log import msg
from twisted.internet import reactor
from posix import environ


class HiddenServicesClient(MultiDispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from Tribler.community.tunnel.hidden_community import HiddenTunnelCommunity
        super(HiddenServicesClient, self).__init__(*argv, **kwargs)
        self.set_community(HiddenTunnelCommunity, name="tunnel")
        self.speed_download = {'download': 0}
        self.speed_upload = {'upload': 0}
        self.progress = {'progress': 0}
        self.download = None
        self.seeders = {}
        self.testfilesize = 100 * 1024 * 1024
        self.security_limiters = False
        self.min_circuits = 3
        self.max_circuits = 5

    def configure_tunnel_community(self, become_exitnode=None, no_crypto=None):
        become_exitnode = become_exitnode == 'exit'
        no_crypto = no_crypto == 'no_crypto'

        from Tribler.community.tunnel.tunnel_community import TunnelSettings
        tunnel_settings = TunnelSettings()

        tunnel_settings.become_exitnode = become_exitnode
        msg("This peer is exit node: %s" % ('Yes' if become_exitnode else 'No'))

        tunnel_settings.socks_listen_ports = [27000 + (10 * self.scenario_runner._peernumber) + i for i in range(5)]

        if not self.security_limiters:
            tunnel_settings.max_traffic = 1024 * 1024 * 1024 * 1024

        tunnel_settings.min_circuits = self.min_circuits
        tunnel_settings.max_circuits = self.max_circuits

        logging.debug("My wan address is %s" % repr(self._dispersy._wan_address[0]))

        msg("Crypto on tunnels: %s" % ('Disabled' if no_crypto else 'Enabled'))
        if no_crypto:
            from Tribler.community.tunnel.crypto.tunnelcrypto import NoTunnelCrypto
            tunnel_settings.crypto = NoTunnelCrypto()

        self.set_community_kwarg('tribler_session', self.session, name="tunnel")
        self.set_community_kwarg('settings', tunnel_settings, name="tunnel")

    @property
    def tunnel_community(self):
        return self.experiment_communities["tunnel"].community

    @property
    def my_member_key_curve(self):
        return u"curve25519"

    def modify_config(self, config):
        # We want to create our own community
        config.set_tunnel_community_enabled(False)
        config.set_anon_listen_port(27000 + self.scenario_runner._peernumber * 10)
        return config

    def setup_session_config(self):
        config = super(HiddenServicesClient, self).setup_session_config()
        config.set_tunnel_community_enabled(False)
        return config

    def update_seed_peers(self):
        if self.download:
            for seeder, port in self.seeders.iteritems():
                addr = (seeder.sock_addr[0], port)
                logging.critical("ADDING PEER TO DOWNLOAD: " + str(addr))
                self.download.add_peer(addr)

    def seeder_registered(self, value_dict):
        self.seeders = value_dict
        self.update_seed_peers()

    def get_my_member(self):
        keypair = self.session.multichain_keypair
        return self._dispersy.get_member(private_key=keypair.key_to_bin())

    def log_progress_stats(self, ds):
        new_speed_download = {'download': ds.get_current_speed('down')}
        self.speed_download = self.print_on_change("speed-download",
                                                   self.speed_download,
                                                   new_speed_download)

        new_progress = {'progress': ds.get_progress() * 100}
        self.progress = self.print_on_change("progress-percentage",
                                             self.progress,
                                             new_progress)

        new_speed_upload = {'upload': ds.get_current_speed('up')}
        self.speed_upload = self.print_on_change("speed-upload",
                                                 self.speed_upload,
                                                 new_speed_upload)

    def start_download(self, filename, hops=1):
        hops = int(hops)

        def cb_start_download():
            from Tribler.Core.simpledefs import dlstatus_strings
            self.annotate('start downloading %s with %d hop(s)' % (filename, hops))

            def cb(ds):
                logging.error('Download infohash=%s, hops=%d, down=%s, up=%d, progress=%s, status=%s, peers=%s, cand=%d' %
                              (tdef.get_infohash().encode('hex')[:5],
                               hops,
                               ds.get_current_speed('down'),
                               ds.get_current_speed('up'),
                               ds.get_progress(),
                               dlstatus_strings[ds.get_status()],
                               sum(ds.get_num_seeds_peers()),
                               sum(1 for _ in self._community.dispersy_yield_verified_candidates())))

                self.log_progress_stats(ds)

                return 1.0, False

            tdef = self.create_test_torrent(filename)

            from Tribler.Core.DownloadConfig import DefaultDownloadStartupConfig
            defaultDLConfig = DefaultDownloadStartupConfig.getInstance()
            dscfg = defaultDLConfig.copy()
            dscfg.set_hops(hops)
            dscfg.set_dest_dir(
            path.join(BASE_DIR, 'tribler', 'download-%s-%d' % (self.session.get_dispersy_port(), hops)))

            self.download = self.session.start_download_from_tdef(tdef, dscfg)
            self.download.set_state_callback(cb)
            self.update_seed_peers()

        reactor.callInThread(cb_start_download)

    def introduce_candidates(self):
        # We are letting dispersy deal with addins the community's candidate to itself.
        from Tribler.dispersy.candidate import Candidate
        for i in range(len(self.all_vars)):
            port = 21000 + i + 1
            if self.dispersy_port != port:
                print "Introducing..."
                self.tunnel_community.add_discovered_candidate(Candidate(("127.0.0.1", port),
                                                                   tunnel=False))
                print "Tunnel Community now has " + str(sum(1 for _ in self.tunnel_community.dispersy_yield_candidates())) + " candidates"

    def set_security_limiters(self, value):
        self.security_limiters = value == 'True'

    def create_test_torrent(self, filename=''):
        logging.error("Create %s download" % filename)
        filename = path.join(BASE_DIR, "tribler", str(self.scenario_file) + str(filename))
        logging.info("Creating torrent...")
        if not path.isfile(filename):
            rnd_kb = "".join([chr(random.randint(0, 255))] * 1024)
            with open(filename, 'wb') as fp:
                for _ in xrange(self.testfilesize / 1024):
                    fp.write(rnd_kb)

        from Tribler.Core.TorrentDef import TorrentDef
        tdef_file = path.join(BASE_DIR, "output", "gen.torrent")
        if path.isfile(tdef_file):
            f_tdef = TorrentDef.load(tdef_file)
            from Tribler.Core.TorrentDef import TorrentDefNoMetainfo
            tdef = TorrentDefNoMetainfo(f_tdef.get_infohash(), filename)
        else:
            tdef = TorrentDef()
            tdef.add_content(filename)
            tdef.set_tracker("http://fake.net/announce")
            tdef.finalize()
            tdef.save(tdef_file)
        return tdef

    def start_seeder(self, filename, hops=0):
        hops = int(hops)

        def cb_seeder_download():
            tdef = self.create_test_torrent(filename)

            self.annotate('start seeding %s with %d hop(s)' % (filename, hops))
            logging.info('start seeding %s with %d hop(s)' % (filename, hops))

            from Tribler.Core.DownloadConfig import DefaultDownloadStartupConfig
            defaultDLConfig = DefaultDownloadStartupConfig.getInstance()
            dscfg = defaultDLConfig.copy()
            dscfg.set_dest_dir(path.join(BASE_DIR, "tribler"))
            dscfg.set_hops(hops)

            def cb(ds):
                from Tribler.Core.simpledefs import dlstatus_strings
                msg('Seed infohash=%s, hops=%d, down=%d, up=%d, progress=%s, status=%s, peers=%s, cand=%d' %
                              (tdef.get_infohash().encode('hex')[:5],
                               hops,
                               ds.get_current_speed('down'),
                               ds.get_current_speed('up'),
                               ds.get_progress(),
                               dlstatus_strings[ds.get_status()],
                               sum(ds.get_num_seeds_peers()),
                               sum(1 for _ in self.tunnel_community.dispersy_yield_verified_candidates())))
                self.log_progress_stats(ds)

                return 1.0, False

            download = self.session.start_download_from_tdef(tdef, dscfg)
            download.set_state_callback(cb)

            seeding_port = download.ltmgr.get_session().listen_port()
            logging.critical("SEEDING ON PORT: " + str(seeding_port))

        logging.error("Call to cb_seeder_download")
        reactor.callInThread(cb_seeder_download)

    def registerCallbacks(self):
        super(HiddenServicesClient, self).registerCallbacks()
        self.scenario_runner.register(self.start_seeder, 'start_seeder')
        self.scenario_runner.register(self.start_download, 'start_download')
        self.scenario_runner.register(self.configure_tunnel_community, 'configure_tunnel_community')
        self.scenario_runner.register(self.set_security_limiters, 'set_security_limiters')
        self.scenario_runner.register(self.introduce_candidates, 'introduce_candidates')

if __name__ == '__main__':
    HiddenServicesClient.scenario_file = environ.get('SCENARIO_FILE', 'hiddenservices-1-hop-seeder.scenario')
    main(HiddenServicesClient)
