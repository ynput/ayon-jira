import os

from ayon_core.addon import AYONAddon, IPluginPaths

from .version import __version__


JIRA_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class JiraAddon(AYONAddon, IPluginPaths):
    name = "jira"
    version = __version__

    def initialize(self, module_settings):
        self.enabled = True

    def get_plugin_paths(self):
        return {
            "publish": os.path.join(JIRA_ROOT_DIR, "plugins", "publish")
        }

