"""只测试本轮机械性修复，不将待处理的审查发现当成已修复。"""
import contextlib
import io
import runpy
import sys
import types
import unittest
from pathlib import Path

with contextlib.redirect_stdout(io.StringIO()):
    probe = runpy.run_path(str(Path(__file__).with_name('audit_probe.py')))


class MechanicalFixTests(unittest.TestCase):
    def test_creation_notification_has_initiator_name(self):
        probe['messages'].clear()
        _, response, output = probe['create']({})
        self.assertTrue(response['ok'])
        self.assertEqual(output, '')
        self.assertEqual(len(probe['messages']), 1)
        self.assertEqual(probe['messages'][0]['sender_name'], '测试经理')

    def test_review_numbers_differ_with_identical_time(self):
        ns = probe['ns']
        real_datetime = ns['datetime']

        class FixedTime:
            @classmethod
            def now(cls, tz):
                return probe['datetime'](2026, 10, 9, 10, 0, 0, tzinfo=tz)

        ns['datetime'] = FixedTime
        try:
            numbers = [ns['_generate_review_no']() for _ in range(100)]
            self.assertEqual(len(set(numbers)), 100)
            self.assertTrue(all(len(number) <= 64 and number.startswith('REV-20261009-') for number in numbers))
        finally:
            ns['datetime'] = real_datetime

    def test_config_failure_logs_and_returns_existing_defaults(self):
        module_name = 'backend.projects.insulation_pipe_supply_2026.services.config_service'
        stub = types.ModuleType(module_name)

        def fail():
            raise ValueError('模拟配置读取失败')

        stub.load_tube_config = fail
        previous = sys.modules.get(module_name)
        sys.modules[module_name] = stub
        try:
            with self.assertLogs('joint-review-audit-probe', level='WARNING'):
                result = probe['ns']['get_arbitrator_accounts']()
            self.assertEqual(result, probe['ns']['DEFAULT_ARBITRATOR_ACCOUNTS'])
        finally:
            if previous is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = previous


if __name__ == '__main__':
    unittest.main()
