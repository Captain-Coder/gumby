#!/usr/bin/env python2
import os
import re
import sys


class TunnelStatisticsParser(object):
    """
    This class is responsible for parsing statistics of the tunnels
    """

    def __init__(self, node_directory):
        self.node_directory = node_directory

    def yield_files(self, file_to_check='market_stats.log'):
        pattern = re.compile('[0-9]+')

        # TODO: this only contains support for a localhost structure
        for peer in os.listdir(self.node_directory):
            peerdir = os.path.join(self.node_directory, peer)
            if os.path.isdir(peerdir) and pattern.match(peer):
                peer_nr = int(peer)

                filename = os.path.join(self.node_directory, peer, file_to_check)
                if os.path.exists(filename) and os.stat(filename).st_size > 0:
                    yield peer_nr, filename, peerdir

    def aggregate_introduction_points(self):
        with open('introduction_points.csv', 'w', 0) as ips_file:
            ips_file.write("peer,infohash\n")
            for peer_nr, filename, dir in self.yield_files(file_to_check='introduction_points.txt'):
                with open(filename) as ip_file:
                    ips_file.write(ip_file.read())

    def aggregate_rendezvous_points(self):
        with open('rendezvous_points.csv', 'w', 0) as rps_file:
            rps_file.write("peer,cookie\n")
            for peer_nr, filename, dir in self.yield_files(file_to_check='rendezvous_points.txt'):
                with open(filename) as rp_file:
                    rps_file.write(rp_file.read())

    def aggregate_downloads_history(self):
        with open('downloads_history.csv', 'w', 0) as downloads_file:
            downloads_file.write('peer,time,infohash,progress,status,total_up,total_down,speed_up,speed_down\n')
            for peer_nr, filename, dir in self.yield_files(file_to_check='downloads_history.txt'):
                with open(filename) as individual_downloads_file:
                    lines = individual_downloads_file.readlines()
                    for line in lines:
                        downloads_file.write('%s,%s' % (peer_nr, line))

    def run(self):
        self.aggregate_introduction_points()
        self.aggregate_rendezvous_points()
        self.aggregate_downloads_history()


# cd to the output directory
os.chdir(os.environ['OUTPUT_DIR'])

parser = TunnelStatisticsParser(sys.argv[1])
parser.run()
