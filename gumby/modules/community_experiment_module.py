from time import time

from Tribler.pyipv8.ipv8.peer import Peer

from gumby.experiment import experiment_callback
from gumby.modules.base_dispersy_module import BaseDispersyModule
from gumby.modules.experiment_module import ExperimentModule

from Tribler.Core import permid
from Tribler.dispersy.candidate import WalkCandidate
from Tribler.dispersy.crypto import M2CryptoPK


class DispersyCommunityExperimentModule(ExperimentModule):
    """
    Base class for experiment modules that provide gumby scenario control over a single dispersy community.
    """

    def __init__(self, experiment, community_class):
        super(DispersyCommunityExperimentModule, self).__init__(experiment)
        self.community_class = community_class

        # To be sure that the module loading happens in the right order, this next line serves the dual purpose of
        # triggering the check for a loaded dispersy provider
        self.dispersy_provider.dispersy_available.addCallback(self.on_dispersy_available)

    @property
    def dispersy_provider(self):
        """
        Gets an experiment module from the loaded experiment modules that inherits from BaseDispersyModule. It can be
        used as the source for the dispersy instance, session, session config and custom community loader.
        :return: An instance of BaseDispersyModule that was loaded into the experiment.
        """
        ret = BaseDispersyModule.get_dispery_provider(self.experiment)
        if ret:
            return ret

        raise Exception("No dispersy provider module loaded. Load an implementation of BaseDispersyModule ("
                        "DispersyModule or TriblerModule) before loading the %s module", self.__class__.__name__)

    @property
    def dispersy(self):
        return self.dispersy_provider.dispersy

    @property
    def session(self):
        return self.dispersy_provider.session

    @property
    def tribler_config(self):
        # The tribler config only exists after on_id_received, up to session start. The session start copy constructs
        # all settings so writing to the original tribler_config after this will not do anything. So on any access to
        # the tribler_config after the session has launched, return the session. It acts as a tribler_config as well and
        # alerts the user if some setting cannot be changed at runtime.
        if self.dispersy_provider.tribler_config is None:
            return self.session
        else:
            return self.dispersy_provider.tribler_config

    @property
    def dispersy_community_loader(self):
        return self.dispersy_provider.custom_dispersy_community_loader

    @property
    def dispersy_community_launcher(self):
        return self.dispersy_community_loader.get_launcher(self.community_class.__name__)

    @property
    def community(self):
        #TODO: implement MultiCommunityExperimentModule.
        # If there are multiple instances of a community class there are basically 2 approaches to solving this. One
        # is to derive from CommunityExperimentModule and override this community property, then each instance of the
        # community class can get accessed by index or some such. All @experiment_callbacks in this case would require a
        # number/name argument to indicate what community to work on. An alternative approach would be to instance a
        # CommunityExperimentModule for each instance of the community_class. However it would be difficult to separate
        # the scenario usage of its @experiment_callbacks, they would have to be dynamically named/generated.
        for community in self.dispersy.get_communities():
            if isinstance(community, self.community_class):
                return community
        return None

    @experiment_callback
    def introduce_peers(self):
        # bootstrap the peer introduction, ensuring everybody knows everybody to start off with.
        for candidate_id in self.all_vars.iterkeys():
            if int(candidate_id) != self.my_id:
                self.get_candidate(candidate_id)

    def get_candidate(self, candidate_id):
        target = self.all_vars[candidate_id]
        address = (str(target['host']), target['port'])
        candidate = self.community.get_candidate(address, replace=False)
        if candidate is None:
            candidate = WalkCandidate(address, False, address, ("0.0.0.0", 0), u"unknown")
            # Pretend we "walked" into this candidate.
            candidate.walk_response(time())
        if not candidate.get_member():
            member = self.community.get_member(public_key=self.get_candidate_public_key(candidate_id).decode("base64"))
            member.add_identity(self.community)
            candidate.associate(member)
        self.community.add_candidate(candidate)
        return candidate

    def get_candidate_public_key(self, candidate_id):
        return self.all_vars[candidate_id]['public_key']

    def on_id_received(self):
        # Since the dispersy source module is loaded before any community module, the dispersy on_id_received has
        # already completed. This means that the tribler_config is now available. So any configuration should happen in
        # overrides of this function. (Be sure to call this super though!)
        super(DispersyCommunityExperimentModule, self).on_id_received()

        # We need the dispersy / member key at this point. However, the configured session is not started yet. So we
        # generate the keys here and place them in the correct place. When the session starts it will load these keys.
        keypair = permid.generate_keypair()
        pairfilename = self.tribler_config.get_permid_keypair_filename()
        permid.save_keypair(keypair, pairfilename)
        permid.save_pub_key(keypair, "%s.pub" % pairfilename)

        m2c_pk = M2CryptoPK(ec_pub=keypair.pub())
        self.vars['public_key'] = str(m2c_pk.key_to_bin()).encode("base64")

    def on_dispersy_available(self, dispersy):
        # The dispersy object is now available. This means that the tribler_config has been copy constructed into the
        # session object. Using the tribler_config object after this is useless. The community is also guaranteed to be
        # available.
        pass


class IPv8OverlayExperimentModule(ExperimentModule):
    """
    Base class for experiment modules that provide gumby scenario control over a single IPv8 overlay.
    """

    def __init__(self, experiment, community_class):
        super(IPv8OverlayExperimentModule, self).__init__(experiment)
        self.community_class = community_class

        # To be sure that the module loading happens in the right order, this next line serves the dual purpose of
        # triggering the check for a loaded dispersy provider
        self.dispersy_provider.dispersy_available.addCallback(self.on_dispersy_available)

    @property
    def dispersy_provider(self):
        """
        Gets an experiment module from the loaded experiment modules that inherits from BaseDispersyModule. It can be
        used as the source for the dispersy instance, session, session config and custom community loader.
        :return: An instance of BaseDispersyModule that was loaded into the experiment.
        """
        ret = BaseDispersyModule.get_dispery_provider(self.experiment)
        if ret:
            return ret

        raise Exception("No dispersy provider module loaded. Load an implementation of BaseDispersyModule ("
                        "DispersyModule or TriblerModule) before loading the %s module", self.__class__.__name__)

    @property
    def ipv8(self):
        return self.dispersy_provider.ipv8

    @property
    def session(self):
        return self.dispersy_provider.session

    @property
    def tribler_config(self):
        # The tribler config only exists after on_id_received, up to session start. The session start copy constructs
        # all settings so writing to the original tribler_config after this will not do anything. So on any access to
        # the tribler_config after the session has launched, return the session. It acts as a tribler_config as well and
        # alerts the user if some setting cannot be changed at runtime.
        if self.dispersy_provider.tribler_config is None:
            return self.session

        return self.dispersy_provider.tribler_config

    @property
    def ipv8_community_loader(self):
        return self.dispersy_provider.custom_ipv8_community_loader

    @property
    def ipv8_community_launcher(self):
        return self.ipv8_community_loader.get_launcher(self.community_class.__name__)

    @property
    def overlay(self):
        #TODO: implement MultiCommunityExperimentModule.
        # If there are multiple instances of a community class there are basically 2 approaches to solving this. One
        # is to derive from CommunityExperimentModule and override this community property, then each instance of the
        # community class can get accessed by index or some such. All @experiment_callbacks in this case would require a
        # number/name argument to indicate what community to work on. An alternative approach would be to instance a
        # CommunityExperimentModule for each instance of the community_class. However it would be difficult to separate
        # the scenario usage of its @experiment_callbacks, they would have to be dynamically named/generated.
        for overlay in self.ipv8.overlays:
            if isinstance(overlay, self.community_class):
                return overlay
        return None

    @experiment_callback
    def introduce_peers(self):
        # bootstrap the peer introduction, ensuring everybody knows everybody to start off with.
        for peer_id in self.all_vars.iterkeys():
            if int(peer_id) != self.my_id:
                self.overlay.walk_to(self.experiment.get_peer_ip_port_by_id(peer_id))

    def get_peer(self, peer_id):
        target = self.all_vars[peer_id]
        address = (str(target['host']), target['port'])
        return Peer(self.get_peer_public_key(peer_id).decode("base64"), address=address)

    def get_peer_public_key(self, peer_id):
        return self.all_vars[peer_id]['public_key']

    def on_id_received(self):
        # Since the dispersy source module is loaded before any community module, the dispersy on_id_received has
        # already completed. This means that the tribler_config is now available. So any configuration should happen in
        # overrides of this function. (Be sure to call this super though!)
        super(IPv8OverlayExperimentModule, self).on_id_received()

        # We need the dispersy / member key at this point. However, the configured session is not started yet. So we
        # generate the keys here and place them in the correct place. When the session starts it will load these keys.
        keypair = permid.generate_keypair()
        pairfilename = self.tribler_config.get_permid_keypair_filename()
        permid.save_keypair(keypair, pairfilename)
        permid.save_pub_key(keypair, "%s.pub" % pairfilename)

        m2c_pk = M2CryptoPK(ec_pub=keypair.pub())
        self.vars['public_key'] = str(m2c_pk.key_to_bin()).encode("base64")

    def on_dispersy_available(self, dispersy):
        # The dispersy object is now available. This means that the tribler_config has been copy constructed into the
        # session object. Using the tribler_config object after this is useless. The community is also guaranteed to be
        # available.
        pass
