# -----------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# -----------------------------------------------------------------------------

import traceback

from knack.log import get_logger
from knack.util import CLIError

from azdev.utilities import call, cmd
from azdev.utilities import display


logger = get_logger(__name__)


class ProfileContext:
    def __init__(self, profile_name=None):
        self.target_profile = profile_name

        self.origin_profile = current_profile()

    def __enter__(self):
        if self.target_profile is None or self.target_profile == self.origin_profile:
            display(
                f'The tests are set to run against current profile "{self.origin_profile}"'
            )
        else:
            result = cmd(
                f'az cloud update --profile {self.target_profile}',
                f'Switching to target profile "{self.target_profile}"...',
            )
            if result.exit_code != 0:
                raise CLIError(result.error.output.decode('utf-8'))

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.target_profile is not None and self.target_profile != self.origin_profile:
            display(f'Switching back to origin profile "{self.origin_profile}"...')
            call(f'az cloud update --profile {self.origin_profile}')

        if exc_tb:
            display('')
            traceback.print_exception(exc_type, exc_val, exc_tb)


def current_profile():
    return cmd('az cloud show --query profile -otsv', show_stderr=False).result
