# -*- coding: utf-8 -*-
import irc3
from irc3.plugins.command import command


@irc3.plugin
class Plugin:

    def __init__(self, bot):
        self.bot = bot

    @classmethod
    def reload(cls, old):
        """this method should return a ready to use plugin instance.
        cls is the newly reloaded class. old is the old instance.
        """
        return cls(old.bot)

    @command(permission='admin')
    def reload(self, mask, target, args):
        """reload

            %%reload
            [-reload] to hot reload the plugins
        """
        try:
            self.bot.reload('scores_plugin')
        
        except Exception as e:
            yield e
            return
        
        yield 'Plugin reloaded successfully'
