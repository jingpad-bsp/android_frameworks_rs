'''Module that contains the test TestSourceStepCpp.'''

import os

from harness.test_base_remote import TestBaseRemote


class TestSourceStepCpp(TestBaseRemote):
    '''Test stepping through the source in an NDK app.'''

    def get_bundle_target(self):
        '''Return string with name of bundle executable to run.

        Returns:
            A string containing the name of the binary that this test can be run
            with.
        '''
        return "CppBranchingFunCalls"

    def test_setup(self, android):
        '''This test requires to be run on one thread.'''
        android.push_prop('debug.rs.max-threads', 1)

    def test_shutdown(self, android):
        '''Reset the number of RS threads to the previous value.'''
        android.pop_prop('debug.rs.max-threads')

    def test_case(self, _):
        '''Run the lldb commands that are being tested.

        Raises:
            TestFail: One of the lldb commands did not provide the expected
            output.
        '''
        self.try_command('language renderscript status',
                         ['Runtime Library discovered',
                          'Runtime Driver discovered'])

        self.try_command('b -f simple.rs -l 47',
                         ['(pending)'])

        self.try_command('process continue',
                         ['stopped',
                          'stop reason = breakpoint',
                          'simple.rs:47'])

        # set the source mapping
        file_dir = os.path.dirname(os.path.realpath(__file__))
        new_dir = os.path.join(file_dir, '..', '..', 'cpp', 'BranchingFunCalls')
        self.set_src_map('simple.rs', new_dir)

        self.try_command('process status',
                         ['-> 47',
                          'int i = in;'])

        #47     int i = in;
        self.try_command('thread step-in',
                         ['-> 48'])
        #48     float f = (float) i;
        self.try_command('thread step-in',
                         ['-> 49'])
        #49     modify_f(&f);
        self.try_command('thread step-over',
                         ['-> 50'])
        #50  	modify_i(&i);
        self.try_command('thread step-in',
                         ['-> 33'])
        #33         int j = *i;
        self.try_command('b -f simple.rs -l 38',
                         ['modify_i',
                          'simple.rs:38'])
        self.try_command('c',
                         ['stop reason = breakpoint',
                          'simple.rs:38',
                          '-> 38'])
        #38    set_i(i, 0);
        # For the line number anything between #20 and #22 is fine
        self.try_command('thread step-in',
                         [],
                         [r'-> 2[012]'])
        #22    int tmp = b;
        self.try_command('thread step-out',
                         ['-> 38'])

        self.try_command('breakpoint delete 1', ['1 breakpoints deleted'])

        self.try_command('breakpoint delete 2', ['1 breakpoints deleted'])

        self.try_command('process continue',
                         ['exited with status = 0'])
