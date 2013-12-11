#
# core.py
#
# Copyright (C) 2013 Francois-Xavier Payet <fx.payet@tfdn.org>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2009 Damien Churchill <damoxc@gmail.com>
# Copyright (C) 2010 Pedro Algarvio <pedro@algarvio.me>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
# 	The Free Software Foundation, Inc.,
# 	51 Franklin Street, Fifth Floor
# 	Boston, MA  02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.
#

import logging
from deluge.plugins.pluginbase import CorePluginBase
import deluge.component as component
import deluge.configmanager
from deluge.core.rpcserver import export
from twisted.internet.task import LoopingCall

DEFAULT_PREFS = {
    "default" : {
        "activated" : False,
        "ratio": 0.0,
        "upload_limit": 0
    }
}

log = logging.getLogger(__name__)

class Core(CorePluginBase):
    def enable(self):
        self.config = deluge.configmanager.ConfigManager("uploadratemodifier.conf", DEFAULT_PREFS)
        #We check to see if labels are enabled
        if 'Label' in component.get("CorePluginManager").get_enabled_plugins():
            # Label is enabled, we create an entry for each label
            labelPlugin = component.get("CorePlugin.Label")
            for currentLabel in labelPlugin.get_labels():
                if not currentLabel in self.config:
                    self.add_label_to_config(currentLabel)
            self.config.save()
        
        self.check_torrents_timer = LoopingCall(self.check_torrents)
        self.check_torrents_timer.start(15)
        log.info("UploadRateModifier plugin enabled!")

    def disable(self):
        self.check_torrents_timer.stop()
        log.info("UploadRateModifier plugin disabled")

    def update(self):
        pass
    
    def check_torrents(self):
        for torrent in component.get("Core").torrentmanager.get_torrent_list():
            status_keys = ["is_seed",
                           "paused",
                           "ratio",
                           "name",
                           "label",
                           "max_upload_speed"
            ]
            status = component.get("Core").get_torrent_status(torrent,status_keys)
            if status["is_seed"] and not status["paused"]:
                group = status["label"] or "default"
                ratio = status["ratio"]
                currentUploadSpeed = status["max_upload_speed"]
                if not group in self.config:
                    self.add_label_to_config(group)
                
                if self.config[group]["activated"]:
                    if (ratio > self.config[group]["ratio"]) and (currentUploadSpeed == -1):
                        log.info("Torrent %s meets limits. Limiting upload speed" % status["name"])
                        component.get("Core").set_torrent_max_upload_speed(torrent,self.config[group]["upload_limit"])
                        
    
    def add_label_to_config(self, label):
        log.info("No config for %s yet, creating it" % label)
        self.config[label] = {
                              "activated" : False,
                              "ratio": 0.0,
                              "upload_limit": 0
                              }

    @export
    def set_config(self, config):
        """Sets the config dictionary"""
        for key in config.keys():
            self.config[key] = config[key]
        self.config.save()

    @export
    def get_config(self):
        """Returns the config dictionary"""
        return self.config.config
