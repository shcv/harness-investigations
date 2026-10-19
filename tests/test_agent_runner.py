"""Transcript capture and retention, without calling inference providers."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from agent_runner import (AgentRunRequest, AgentRunnerError, ClaudeSdkRunner,
                          CodexExecRunner, QwenOpenAICompatRunner, SessionLog)


class TranscriptTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.logs = self.root / 'logs'
        env = patch.dict(os.environ, {'CHANGELOG_AGENT_LOG_DIR': str(self.logs)})
        env.start()
        self.addCleanup(env.stop)
        self.request = AgentRunRequest('inspect source', cwd=self.root,
                                       system_prompt='read only', allowed_tools=['Read'],
                                       env={'TEST_SECRET': 'do-not-log-this'})

    def fake_codex(self):
        executable = self.root / 'codex'
        executable.write_text('''#!/usr/bin/env python3
import json, pathlib, sys, time
prompt = sys.stdin.read()
assert '--json' in sys.argv
print(json.dumps({'type': 'item.completed', 'item': {
    'type': 'command_execution', 'command': 'cat source',
    'aggregated_output': 'source contents', 'exit_code': 0}}), flush=True)
print('diagnostic output', file=sys.stderr, flush=True)
if 'timeout' in prompt:
    time.sleep(10)
output = pathlib.Path(sys.argv[sys.argv.index('--output-last-message') + 1])
if 'empty' not in prompt:
    output.write_text('final answer')
sys.exit(3 if 'fail' in prompt else 0)
''')
        executable.chmod(0o700)
        return CodexExecRunner('test-model', 'medium', str(executable))

    def test_codex_preserves_events_inputs_answer_and_diagnostics(self):
        runner = self.fake_codex()
        self.assertEqual(runner.run(self.request), 'final answer')
        log = runner.last_log_dir
        event = json.loads((log / 'events.jsonl').read_text())
        self.assertEqual(event['item']['command'], 'cat source')
        self.assertEqual(event['item']['aggregated_output'], 'source contents')
        self.assertEqual((log / 'final.txt').read_text(), 'final answer')
        self.assertIn('diagnostic output', (log / 'stderr.log').read_text())
        self.assertIn('inspect source', (log / 'prompt.txt').read_text())
        metadata = json.loads((log / 'metadata.json').read_text())
        self.assertEqual(metadata['status'], 'succeeded')
        self.assertEqual(metadata['requested_model'], 'test-model')
        self.assertEqual(metadata['reasoning_effort'], 'medium')
        self.assertEqual(log.stat().st_mode & 0o777, 0o700)
        for path in log.iterdir():
            self.assertNotIn('do-not-log-this', path.read_text())

    def test_codex_failure_timeout_and_empty_answer_keep_partial_trace(self):
        runner = self.fake_codex()
        for prompt, error in [('fail', AgentRunnerError), ('timeout', subprocess.TimeoutExpired),
                              ('empty', AgentRunnerError)]:
            with self.subTest(prompt=prompt), self.assertRaises(error):
                runner.run(AgentRunRequest(prompt, cwd=self.root, timeout=0.3))
            log = runner.last_log_dir
            self.assertIn('source contents', (log / 'events.jsonl').read_text())
            self.assertIn('diagnostic output', (log / 'stderr.log').read_text())
            self.assertEqual(json.loads((log / 'metadata.json').read_text())['status'], 'failed')
            self.assertTrue((log / 'error.txt').exists())
            self.assertFalse((log / 'final.txt').exists())

    def test_qwen_records_tool_calls_and_actual_results(self):
        runner = QwenOpenAICompatRunner('test-model', 'http://example.invalid', api_key='private-key')
        (self.root / 'source').write_text('actual file contents')
        responses = [
            {'choices': [{'message': {'tool_calls': [{'id': 'call-1', 'type': 'function',
              'function': {'name': 'read_file', 'arguments': '{"path":"source"}'}}]}}]},
            {'model': 'resolved-model', 'choices': [{'message': {'content': 'the answer'}}]},
        ]
        with patch.object(runner, '_post', side_effect=responses):
            self.assertEqual(runner.run(self.request), 'the answer')
        events = [json.loads(line) for line in (runner.last_log_dir / 'events.jsonl').read_text().splitlines()]
        result = next(event['data'] for event in events if event['type'] == 'tool_result')
        self.assertEqual(result['tool_call_id'], 'call-1')
        self.assertIn('actual file contents', result['content'])
        self.assertEqual(json.loads((runner.last_log_dir / 'metadata.json').read_text())['resolved_model'],
                         'resolved-model')
        self.assertNotIn('private-key', (runner.last_log_dir / 'events.jsonl').read_text())

    def test_claude_records_sdk_tool_use_and_tool_result_messages(self):
        @dataclass
        class AssistantMessage:
            content: list
            model: str = 'resolved-claude'

        @dataclass
        class UserMessage:
            content: list

        @dataclass
        class ResultMessage:
            result: str = 'answer'
            is_error: bool = False

        async def query(**kwargs):
            yield AssistantMessage([{'type': 'tool_use', 'id': 'read-1', 'name': 'Read',
                                     'input': {'file_path': 'source'}}])
            yield UserMessage([{'type': 'tool_result', 'tool_use_id': 'read-1', 'content': 'source text'}])
            yield ResultMessage()

        sdk = types.SimpleNamespace(AssistantMessage=AssistantMessage, ResultMessage=ResultMessage,
                                    ClaudeAgentOptions=lambda **kwargs: kwargs, query=query)
        runner = ClaudeSdkRunner('claude')
        with patch.dict(sys.modules, {'claude_agent_sdk': sdk}):
            self.assertEqual(runner.run(self.request), 'answer')
        events = [json.loads(line) for line in (runner.last_log_dir / 'events.jsonl').read_text().splitlines()]
        self.assertEqual(events[0]['data']['content'][0]['name'], 'Read')
        self.assertEqual(events[1]['data']['content'][0]['content'], 'source text')

    def test_retention_keeps_five_and_never_deletes_active_or_unrelated_logs(self):
        runner = QwenOpenAICompatRunner('model', 'http://example.invalid')
        active = SessionLog(runner, self.request)
        self.addCleanup(active._active.close)
        unrelated = self.logs / 'run-user-notes'
        unrelated.mkdir()
        (unrelated / 'notes').write_text('keep')
        # Simulate a process killed before finish: its kernel lock is released
        # but the metadata still says running. It must not survive forever.
        abandoned = SessionLog(runner, self.request)
        abandoned._active.close()
        paths = []
        for i in range(7):
            with patch.object(runner, '_post', return_value={'choices': [{'message': {'content': 'ok'}}]}):
                runner.run(self.request)
            paths.append(runner.last_log_dir)
        self.assertTrue(active.path.exists())
        self.assertFalse(abandoned.path.exists())
        self.assertTrue(unrelated.exists())
        self.assertEqual([p.exists() for p in paths], [False, False, True, True, True, True, True])
        active.finish('succeeded', None)
        self.assertFalse(active.path.exists())


if __name__ == '__main__':
    unittest.main()
