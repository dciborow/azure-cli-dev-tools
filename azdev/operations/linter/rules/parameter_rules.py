# -----------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# -----------------------------------------------------------------------------

from knack.deprecation import Deprecated

from ..rule_decorators import ParameterRule
from ..linter import RuleError, LinterSeverity


@ParameterRule(LinterSeverity.HIGH)
def missing_parameter_help(linter, command_name, parameter_name):
    if not linter.get_parameter_help(command_name, parameter_name) and not linter.command_expired(command_name):
        raise RuleError('Missing help')


@ParameterRule(LinterSeverity.HIGH)
def expired_parameter(linter, command_name, parameter_name):
    if linter.parameter_expired(command_name, parameter_name):
        raise RuleError('Deprecated parameter is expired and should be removed.')


@ParameterRule(LinterSeverity.HIGH)
def expired_option(linter, command_name, parameter_name):
    if expired_options := linter.option_expired(command_name, parameter_name):
        raise RuleError(
            f"Deprecated options '{', '.join(expired_options)}' are expired and should be removed."
        )


@ParameterRule(LinterSeverity.HIGH)
def bad_short_option(linter, command_name, parameter_name):
    bad_options = []
    for option in linter.get_parameter_options(command_name, parameter_name):
        if isinstance(option, Deprecated):
            # we don't care if deprecated options are "bad options" since this is the
            # mechanism by which we get rid of them
            continue
        if not option.startswith('--') and len(option) != 2:
            bad_options.append(option)

    if bad_options:
        raise RuleError(
            f"Found multi-character short options: {' | '.join(bad_options)}. Use a single character or convert to a long-option."
        )


@ParameterRule(LinterSeverity.MEDIUM)
def parameter_should_not_end_in_resource_group(linter, command_name, parameter_name):
    options_list = linter.get_parameter_options(command_name, parameter_name)
    bad_options = []

    for opt in options_list:
        if isinstance(opt, Deprecated):
            # we don't care if deprecated options are "bad options" since this is the
            # mechanism by which we get rid of them
            continue

        bad_opts = [opt.endswith('resource-group'), opt.endswith('resourcegroup'), opt.endswith("resource-group-name")]
        if any(bad_opts) and opt != "--resource-group":
            bad_options.append(opt)

    if bad_options:
        bad_options_str = ' | '.join(bad_options)
        raise RuleError(
            f"A command should only have '--resource-group' as its resource group parameter. However options '{bad_options_str}' in command '{command_name}' end with 'resource-group' or similar."
        )


@ParameterRule(LinterSeverity.HIGH)
def no_positional_parameters(linter, command_name, parameter_name):
    options_list = linter.get_parameter_options(command_name, parameter_name)

    if not options_list:
        raise RuleError(
            f"CLI commands should have optional parameters instead of positional parameters. However parameter '{parameter_name}' in command '{command_name}' is a positional."
        )


@ParameterRule(LinterSeverity.HIGH)
def no_parameter_defaults_for_update_commands(linter, command_name, parameter_name):
    is_update_command = command_name.split()[-1].lower() == "update"
    default_val = linter.get_parameter_settings(command_name, parameter_name).get('default')

    if is_update_command and default_val:
        raise RuleError(
            f"Update commands should not have parameters with default values. '{parameter_name}' in '{command_name}' has a default value of '{default_val}'"
        )


@ParameterRule(LinterSeverity.MEDIUM)
def no_required_location_param(linter, command_name, parameter_name):
    # Location parameters should typically not be required.
    # If there is a resource group, one can default to the its location.

    has_resource_group = "resource_group_name" in linter.get_command_parameters(command_name)
    is_location_param = (parameter_name.lower() == "location" or parameter_name.endswith("location"))

    if has_resource_group and is_location_param:
        parameter = linter.get_parameter_settings(command_name, parameter_name)
        if is_required := parameter.get('required'):
            location_params = linter.get_parameter_options(command_name, parameter_name)
            location_params = location_params or f"'{parameter_name}'"

            raise RuleError(
                f"Location parameters should not be required. However, {location_params} in '{command_name}' should is required. Please make it optional and default to the location of the resource group."
            )


@ParameterRule(LinterSeverity.LOW)
def id_params_only_for_guid(linter, command_name, parameter_name):
    # Check if the parameter is an id param, except for '--ids'. If so, attempt to figure out if
    # it is a resource id parametere. This check can lead to false positives, which is why it is a low severity check.
    # Its aim is to guide reviewers and developers.

    def _help_contains_queries(help_str, queries):
        a_query_is_in_a_str = next((True for query in queries if query.lower() in help_str.lower()), False)
        return a_query_is_in_a_str

    options_list = linter.get_parameter_options(command_name, parameter_name) or []
    queries = ["resource id", "arm id"]
    is_id_param = False

    # first find out if an option ends with id.
    for opt in options_list:
        if isinstance(opt, Deprecated):
            return

        id_opts = [opt.endswith('-id'), opt.endswith('-ids')]

        if any(id_opts) and opt != "--ids":
            is_id_param = True

    # if an option is an id param, check if the help text makes reference to 'resource id' etc. This could lead to fa
    if is_id_param:
        param_help = linter.get_parameter_help(command_name, parameter_name)

        if param_help and _help_contains_queries(param_help, queries):
            raise RuleError("An option {} ends with '-id'. Arguments ending with '-id' "
                            "must be guids/uuids and not resource ids.".format(options_list))


@ParameterRule(LinterSeverity.HIGH)
def option_length_too_long(linter, command_name, parameter_name):
    min_length = None
    length_threshold = 22  # only 5% argument's length exceed this value.
    options_list = linter.get_parameter_options(command_name, parameter_name) or []
    for option in options_list:
        if isinstance(option, Deprecated) or option.startswith('--__'):
            return
        option_len = len(option)
        if option.startswith('--'):
            option_len -= 2
        elif option.startswith('-'):
            option_len -= 1
        min_length = min(min_length, option_len) if min_length else option_len
    if min_length and min_length > length_threshold:
        raise RuleError(
            f"The lengths of all options {options_list} are longer than threshold {length_threshold}. Argument {parameter_name} must have a short abbreviation."
        )


@ParameterRule(LinterSeverity.HIGH)
def option_should_not_contain_under_score(linter, command_name, parameter_name):
    options_list = linter.get_parameter_options(command_name, parameter_name) or []
    for option in options_list:
        if isinstance(option, Deprecated) or option.startswith('--__'):
            return
        if '_' in option:
            raise RuleError(
                f"Argument's option {option} contains '_' which should be '-' instead."
            )
