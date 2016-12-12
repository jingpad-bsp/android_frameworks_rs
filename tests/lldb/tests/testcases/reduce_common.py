# Copyright (C) 2016 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re

REDUCE_ITERATIONS = 128  # This is in MainActivity.java
REDUCE_STARTVAL = 10 # This is in MainActivity.java
REDUCE_AUTO_COMB_SCRIPT = "reduce_common.rsh"
REDUCE_SCRIPT = "reduce_common.rsh"
X_TESTS = 100
Y_TESTS = 2
Z_TESTS = 2


class ReductionMixin(object):
    def _test_func_role_combinations(self, func_role_combinations):
        """
        Assert that when a reduction breakpoint is conditional on a function
        role, that breakpoints are only set on the the given functions.
        We do this by setting breakpoints on all possible pairs of functions
        and check that the resolved breakpoints are on functions that are part
        of the given pair
        """
        for combination in func_role_combinations:
            self._delete_breakpoints()
            self.try_command(
                'language renderscript reduction breakpoint set '
                'find_min_user_type --function-role %s' % (
                    ','.join(combination)
                ),
                [r'Breakpoint(s) created']
            )
            func_suffixes = [combination[0][:4], combination[1][:4]]
            # just match the first 4 chars of the roles prefix
            funcs_match = 'find_min_user_type_((%s|%s))' % tuple(func_suffixes)
            # now check we stop on both functions for each coordinate in the
            # allocation
            for x in range(REDUCE_ITERATIONS):
                output = self.try_command(
                    'process continue',
                    expected_regex=[
                        r'resuming',
                        r'Process \d+ stopped',
                        r'frame #0: 0x[0-9a-fA-F]+ librs.reduce.so`%s' % funcs_match
                    ]
                )
                for line in output.splitlines():
                    match = re.search(funcs_match, line)
                    if match:
                        try:
                            func_suffixes.remove(match.group(1))
                        except ValueError:
                            # The outconverter may only be called in the final
                            # step but the accumulator will be called for every
                            # input index
                            continue
                        break
                if len(func_suffixes) == 0:
                    # We've popped the functions we're interested in off the list
                    break
            else:
                raise self.TestFail(
                    "unable to match function roles for " + repr(combination))

    def _reduction_breakpoint_set_single_type(
            self, script_soname, script_basename, reduce_name, funcname_types):
        """
        Assert - for each function role - that the correct symbol is resolved
        and trapped by the debugger.
        """
        for func, typename in funcname_types:
            self._delete_breakpoints()
            breakpoint_match = r'Breakpoint \d+: where = librs.%s.so`%s'
            # Autogenerated combiners don't have a filename in the debugger
            if not func.endswith(".combiner"):
                breakpoint_match = r'%s (\+ \d+ )?at %s' % (
                        breakpoint_match, script_basename)
            self.try_command(
                'language renderscript reduction breakpoint set %s'
                ' --function-role %s' % (reduce_name, typename),
                expected_regex=[breakpoint_match % (script_soname, func)]
            )
            self.try_command(
                'process continue',
                expected_regex=[
                    r'resuming',
                    r'Process \d+ stopped',
                    r'frame #0: 0x[0-9a-fA-F]+ librs.%s.so`%s' % (
                        script_soname, func)
                ]
            )
