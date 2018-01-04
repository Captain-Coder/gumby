from gumby.experiment import experiment_callback

from gumby.modules.experiment_module import static_module
from gumby.modules.community_experiment_module import CommunityExperimentModule

from Tribler.community.triblerchain.community import TriblerChainCommunity

@static_module
class TriblerchainModule(CommunityExperimentModule):
    def __init__(self, experiment):
        super(TriblerchainModule, self).__init__(experiment, TriblerChainCommunity)

    def on_id_received(self):
        super(TriblerchainModule, self).on_id_received()
        self.session_config.set_trustchain_enabled(True)

    @experiment_callback
    def set_triblerchain_score_cache_timeout(self, value):
        TriblerChainCommunity.SCORE_REFRESH_INTERVAL = long(value)
