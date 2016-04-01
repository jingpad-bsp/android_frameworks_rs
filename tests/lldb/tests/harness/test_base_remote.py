'''Module that contains the base class TestBaseRemote'''

import os
import re

from test_base import TestBase
from . import util_log


class TestBaseRemote(TestBase):
    '''Base class for all tests that connect to a remote device.

    Provides common functionality to set up the connection and tear it down.
    '''

    def __init__(self, device_port, device, timer):
        super(TestBaseRemote, self).__init__(device_port, device, timer)
        # port used by lldb-server on the device.
        self._device_port = device_port
        self._platform = None
        # id of the device that adb will communicate with.
        self._device = device

    def set_src_map(self, file_name, new_src_path):
        '''Call lldb to set the source mapping of a given file.

        Set lldb's source mapping of a given file to a given path. This can be
        used to make the test suite independent of where an APK was compiled.

        Args:
            file_name: String, which is the name of the file whose mapping is
                to be changed
            new_src_path: String which is the new absolute path to the source
                file.
        '''
        line_table = self.do_command('target modules dump line-table '
                                     + file_name)

        lines = line_table.split('\n')
        if 'Line table for' not in lines[0]:
            raise self.TestFail('Could not determine source path of '
                                + file_name)

        # Expecting output like:
        # (lldb) target modules dump line-table scalars.rs
        # Line table for /home/jenkins/workspace/grd-aosp-parameterised-build/
        # merge_151216/frameworks/rs/tests/lldb/java/BranchingFunCalls/src/rs/
        # frameworks/rs/tests/lldb/java/BranchingFunCalls/src/rs/scalars.rs in
        # `librs.scalars.so
        # 0xb30f2374: /home/jenkins/workspace/grd-aosp-parameterised-build/
        # merge_151216/frameworks/rs/tests/lldb/java/BranchingFunCalls/src/rs/
        # scalars.rs:46
        # ...
        # For some reason the first line contains a mangled path?
        old_path = re.findall(r"[^ :]+", lines[1])[1]
        old_dir = os.path.dirname(old_path)

        self.try_command('settings set target.source-map %s %s'
                         % (old_dir, new_src_path), [''])

    def post_run(self):
        '''Clean up after execution.'''
        if self._platform:
            self._platform.DisconnectRemote()

    def test_case(self, _):
        '''Run the lldb commands that are being tested.

        Raises:
            TestFail: One of the lldb commands did not provide the expected
                      output.
        '''
        raise NotImplementedError

    def _connect_to_platform(self, lldb_module, dbg, remote_pid):
        '''Connect to an lldb platform that has been started elsewhere.

        Args:
            lldb_module: A handle to the lldb module.
            dbg: The instance of the SBDebugger that should connect to the
                 server.
            remote_pid: The integer that is the process id of the binary that
                        the debugger should attach to.

        Returns:
            True if the debugger successfully attached to the server and
            process.
        '''
        # pylint: disable=too-many-return-statements
        remote_pid = str(remote_pid)

        log = util_log.get_logger()

        err1 = dbg.SetCurrentPlatform('remote-android')
        if err1.Fail():
            log.fatal(err1.GetCString())
            return False

        self._platform = dbg.GetSelectedPlatform()
        if not self._platform:
            return False

        connect_string = \
            'adb://{0}:{1}'.format(self._device, self._device_port)
        opts = lldb_module.SBPlatformConnectOptions(connect_string)

        for _ in range(2):
            err2 = self._platform.ConnectRemote(opts)
            if err2.Fail():
                log.error(err2.GetCString())

                if 'Connection refused' in err2.GetCString():
                    log.warning('Connection to lldb server was refused. '
                                'Trying again.')
                else:
                    # Unknown error. Don't try again.
                    return False
            else:
                # Success
                break
        else:
            log.fatal('Not trying again, maximum retries exceeded.')
            return False

        target = dbg.CreateTarget(None)
        if not target:
            return False

        dbg.SetSelectedTarget(target)
        listener = lldb_module.SBListener()
        err3 = lldb_module.SBError()
        process = target.AttachToProcessWithID(listener, int(remote_pid), err3)
        if err3.Fail() or not process:
            log.fatal(err3.GetCString())
            return False

        return True

    def run(self, dbg, remote_pid, lldb, wimpy):
        '''Execute the actual test.

        Args:
            dbg: The instance of the SBDebugger that is used to test commands.
            remote_pid: The integer that is the process id of the binary that
                        the debugger is attached to.
            lldb: A handle to the lldb module.
            wimpy: Boolean to specify only a subset of the commands be executed.

        Returns:
            True if the test passed, or False if not.
        '''
        assert dbg
        assert remote_pid
        assert lldb

        self._lldb = lldb

        try:
            self.test_assert(self._connect_to_platform(lldb, dbg, remote_pid))
            self._ci = dbg.GetCommandInterpreter()
            assert self._ci

            self.test_assert(self._ci.IsValid())
            self.test_assert(self._ci.HasCommands())

            self.test_case(wimpy)

        except self.TestFail:
            return False

        return True