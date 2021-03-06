"""
This file is part of nucypher.

nucypher is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

nucypher is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with nucypher.  If not, see <https://www.gnu.org/licenses/>.
"""


import os
from collections import deque

import click
import maya
from twisted.internet import reactor
from twisted.internet.protocol import connectionDone
from twisted.protocols.basic import LineReceiver

from nucypher.cli.painting import build_fleet_state_status


class UrsulaCommandProtocol(LineReceiver):

    encoding = 'utf-8'
    delimiter = os.linesep.encode(encoding=encoding)

    def __init__(self, ursula):
        super().__init__()

        self.ursula = ursula
        self.start_time = maya.now()

        self.__history = deque(maxlen=10)
        self.prompt = bytes('Ursula({}) >>> '.format(self.ursula.checksum_public_address[:9]), encoding='utf-8')

        # Expose Ursula functional entry points
        self.__commands = {

             # Help
            '?': self.paintHelp,
            'help': self.paintHelp,

            # Status
            'status': self.paintStatus,
            'known_nodes': self.paintKnownNodes,
            'fleet_state': self.paintFleetState,

            # Learning Control
            'cycle_teacher': self.cycle_teacher,
            'start_learning': self.start_learning,
            'stop_learning': self.stop_learning,

            # Process Control
            'stop': self.stop,

        }

    @property
    def commands(self):
        return self.__commands.keys()

    def paintHelp(self):
        """
        Display this help message.
        """
        click.secho("\nUrsula Command Help\n===================\n")
        for command, func in self.__commands.items():
            if '?' not in command:
                try:
                    click.secho(f'{command}\n{"-"*len(command)}\n{func.__doc__.lstrip()}')
                except AttributeError:
                    raise AttributeError("Ursula Command method is missing a docstring,"
                                         " which is required for generating help text.")

    def paintKnownNodes(self):
        """
        Display a list of all known nucypher peers.
        """
        from nucypher.cli.painting import paint_known_nodes
        paint_known_nodes(ursula=self.ursula)

    def paintStatus(self):
        """
        Display the current status of the attached Ursula node.
        """
        from nucypher.cli.painting import paint_node_status
        paint_node_status(ursula=self.ursula, start_time=self.start_time)

    def paintFleetState(self):
        """
        Display information about the network-wide fleet state as the attached Ursula node sees it.
        """
        line = '{}'.format(build_fleet_state_status(ursula=self.ursula))
        click.secho(line)

    def connectionMade(self):

        message = 'Attached {}@{}'.format(
                   self.ursula.checksum_public_address,
                   self.ursula.rest_url())

        click.secho(message, fg='green')
        click.secho('{} | {}'.format(self.ursula.nickname_icon, self.ursula.nickname), fg='blue', bold=True)

        click.secho("\nType 'help' or '?' for help")
        self.transport.write(self.prompt)

    def connectionLost(self, reason=connectionDone) -> None:
        self.ursula.stop_learning_loop(reason=reason)

    def lineReceived(self, line):
        """Ursula Console REPL"""

        # Read
        raw_line = line.decode(encoding=self.encoding)
        line = raw_line.strip().lower()

        # Evaluate
        try:
            self.__commands[line]()

        # Print
        except KeyError:
            if line:  # allow for empty string
                click.secho("Invalid input. Options are {}".format(', '.join(self.__commands.keys())))

        else:
            self.__history.append(raw_line)

        # Loop
        self.transport.write(self.prompt)

    def cycle_teacher(self):
        """
        Manually direct the attached Ursula node to start learning from a different teacher.
        """
        return self.ursula.cycle_teacher_node()

    def start_learning(self):
        """
        Manually start the attached Ursula's node learning protocol.
        """
        return self.ursula.start_learning_loop()

    def stop_learning(self):
        """
        Manually stop the attached Ursula's node learning protocol.
        """
        return self.ursula.stop_learning_loop()

    def stop(self):
        """
        Shutdown the attached running Ursula node.
        """
        return reactor.stop()
