"""Annotation cache integrity and the Luna-to-Sol handoff, without network calls."""
import asyncio
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import annotate_changes as annotations
from agent_runner import AgentRunnerError, default_model_for
from slice_changes import bound_batches, make_batches, parse_slices
from sync import ClaudeCodeSync, PROJECTS

ANNOTATION = {
    'name': 'status', 'summary': 'Adds a --status flag to print session status.',
    'importance': 4, 'user_facing': True, 'feature_flag': None, 'disabled': False,
    'component': 'cli', 'change_type': 'new_feature', 'evidence': '"--status"',
}
ANSWER = '<result>' + json.dumps([ANNOTATION]) + '</result>'
DIFF = '''=== Added ===
+++ Added status (cli.js:1-3)
function status() { return "--status"; }
'''


class AnnotationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.batches = self.root / 'batches'
        self.batches.mkdir()
        self.batch = {'id': 1, 'section': 'added', 'names': ['status'],
                      'count': 1, 'content': DIFF}
        annotations.write_json(self.batches / 'batch-001.json', self.batch)
        self.cache = self.batches / 'batch-001-annotations.json'
        self.runner = Mock()
        self.runner.run.return_value = ANSWER
        self.factory = patch.object(annotations, 'make_agent_runner', return_value=self.runner)
        self.make_runner = self.factory.start()
        self.addCleanup(self.factory.stop)
        self.capture = contextlib.redirect_stdout(io.StringIO())
        self.capture.__enter__()
        self.addCleanup(self.capture.__exit__, None, None, None)

    def annotate(self, **kwargs):
        return asyncio.run(annotations.annotate_batches(self.batches, cwd=self.root, **kwargs))

    def test_codex_role_defaults(self):
        self.assertEqual(default_model_for('codex', 'annotation'), 'gpt-6-luna')
        self.assertEqual(default_model_for('codex', 'changelog'), 'gpt-6.1-sol')
        result = self.annotate()
        self.assertEqual(result[0]['_batch_id'], 1)
        self.assertEqual(self.make_runner.call_args.kwargs['model'], 'gpt-6-luna')
        request = self.runner.run.call_args.args[0]
        self.assertEqual(request.allowed_tools, [])
        self.assertEqual(request.timeout, 300)
        self.assertIn('100% similarity score does not prove', request.prompt)

    def test_large_batches_are_bounded_without_dropping_content(self):
        for content in ('a' * 10000, 'function x() {}\n' * 1000):
            batches = bound_batches([{**self.batch, 'content': content}], max_chars=1000)
            self.assertGreater(len(batches), 1)
            self.assertTrue(all(len(b['content']) <= 1000 for b in batches))
            self.assertEqual([b['id'] for b in batches], list(range(1, len(batches) + 1)))
            reconstructed = ''.join(b['content'].split('\n\n', 1)[1] for b in batches)
            self.assertEqual(reconstructed, content)

    def test_interrupted_json_write_preserves_previous_cache(self):
        annotations.write_json(self.cache, {'previous': True})
        with self.assertRaises(TypeError):
            annotations.write_json(self.cache, {'invalid': object()})
        self.assertEqual(json.loads(self.cache.read_text()), {'previous': True})
        self.assertFalse(list(self.batches.glob('.batch-*.json.*')))

    def test_provider_selection_uses_shared_runner(self):
        for provider in ('codex', 'claude', 'qwen'):
            with self.subTest(provider=provider):
                self.annotate(agent_provider=provider, model='chosen')
                self.assertEqual(self.make_runner.call_args.args[0], provider)
                self.assertEqual(self.make_runner.call_args.kwargs['model'], 'chosen')

    def test_cache_tracks_model_effort_prompt_and_batch_content(self):
        self.annotate()
        self.annotate()
        self.assertEqual(self.runner.run.call_count, 1)
        self.annotate(model='other-luna')
        self.annotate(model='other-luna', codex_reasoning_effort='medium')
        with patch.object(annotations, 'ANNOTATION_PROMPT', annotations.ANNOTATION_PROMPT + '\nExtra rule'):
            self.annotate(model='other-luna', codex_reasoning_effort='medium')
            self.batch['content'] += '\nchanged again'
            annotations.write_json(self.batches / 'batch-001.json', self.batch)
            self.annotate(model='other-luna', codex_reasoning_effort='medium')
        self.assertEqual(self.runner.run.call_count, 5)

    def test_legacy_corrupt_and_invalid_cache_regenerate(self):
        for cached in ('{broken', json.dumps({**self.batch, 'annotations': [ANNOTATION]})):
            self.cache.write_text(cached)
            self.annotate()
        data = json.loads(self.cache.read_text())
        data['annotations'][0]['importance'] = 'high'
        annotations.write_json(self.cache, data)
        self.annotate()
        self.assertEqual(self.runner.run.call_count, 3)

    def test_orphaned_annotation_is_not_collected(self):
        annotations.write_json(self.batches / 'batch-099-annotations.json',
                               {'id': 99, 'section': 'added', 'annotations': [ANNOTATION]})
        self.assertEqual(len(self.annotate()), 1)

    def test_invalid_output_never_marks_batch_complete(self):
        bad_outputs = ['not JSON', '<result>{}</result>', '<result>[null]</result>']
        for change in ({'importance': True}, {'importance': 6}, {'importance': '4'},
                       {'user_facing': 'yes'}, {'evidence': {}}, {'summary': None}):
            bad_outputs.append(json.dumps([{**ANNOTATION, **change}]))
        for output in bad_outputs:
            with self.subTest(output=output):
                self.runner.run.return_value = output
                with self.assertRaises(AgentRunnerError):
                    self.annotate()
                self.assertFalse(self.cache.exists())

    def test_valid_empty_and_fenced_json(self):
        self.assertEqual(annotations.parse_annotations('<result>[]</result>'), [])
        self.assertEqual(annotations.parse_annotations('```json\n' + json.dumps([ANNOTATION]) + '\n```'),
                         [ANNOTATION])
        self.runner.run.return_value = '[]'
        self.assertEqual(self.annotate(), [])
        self.assertEqual(self.annotate(), [])
        self.assertEqual(self.runner.run.call_count, 1)

    def test_partial_failure_preserves_success_and_retries_only_failed_batch(self):
        annotations.write_json(self.batches / 'batch-002.json', {**self.batch, 'id': 2})
        self.runner.run.side_effect = [ANSWER, AgentRunnerError('offline')]
        with self.assertRaisesRegex(AgentRunnerError, '1/2 annotation batches failed'):
            self.annotate()
        self.assertTrue(self.cache.exists())
        self.assertFalse((self.batches / 'batch-002-annotations.json').exists())
        self.runner.run.side_effect = [ANSWER]
        self.assertEqual(len(self.annotate()), 2)
        self.assertEqual(self.runner.run.call_count, 3)

    def test_failed_standalone_run_removes_previous_summary(self):
        summary = self.root / 'annotations-v1.2.3.json'
        annotations.write_json(summary, [ANNOTATION])
        self.runner.run.side_effect = AgentRunnerError('offline')
        with self.assertRaises(AgentRunnerError):
            asyncio.run(annotations.main('v1.2.3', self.batches))
        self.assertFalse(summary.exists())


class HandoffTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.sync = ClaudeCodeSync(self.root, PROJECTS['claude-code'], annotate=True,
                                   changelog=True, diff=True, changes=True, prettier=True,
                                   codex_reasoning_effort='medium',
                                   codex_annotation_reasoning_effort='low')
        self.sync.setup_directories()
        self.sync._notify_send_path = None
        self.sync._tool_version = 'test'
        self.sync.allow_degraded_diff = True  # fixture diff is not astdiff
        self.diff = self.sync.diff_dir / 'v1.2.3.diff'
        self.diff.write_text(DIFF)
        (self.sync.pretty_dir / 'pretty-v1.2.3.js').write_text('function status() { return "--status"; }')
        self.capture = contextlib.redirect_stdout(io.StringIO())
        self.capture.__enter__()
        self.addCleanup(self.capture.__exit__, None, None, None)

    def test_reslicing_uses_current_input_and_removes_obsolete_batches(self):
        with patch.object(self.sync, '_annotate_all_batches', return_value=[ANNOTATION]):
            self.sync._run_annotation_pipeline('1.2.3', self.diff)
            batches = self.sync.changes_dir / 'v1.2.3' / 'batches'
            (batches / 'batch-099.json').write_text('{}')
            (batches / 'batch-099-annotations.json').write_text('{}')
            (batches / 'batch-notes.json').write_text('keep')
            self.diff.write_text(DIFF.replace('status', 'health'))
            self.sync._run_annotation_pipeline('1.2.3', self.diff)
            self.assertIn('health', (batches / 'batch-001.json').read_text())
            self.assertFalse((batches / 'batch-099.json').exists())
            self.assertFalse((batches / 'batch-099-annotations.json').exists())
            self.assertEqual((batches / 'batch-notes.json').read_text(), 'keep')

    def test_luna_annotations_reach_sol_and_record_provenance(self):
        executable = self.root / 'codex'
        prose = '# Changelog for version 1.2.3\n\n## Session status\n' + 'The --status flag reports session status. ' * 8
        executable.write_text('''#!/usr/bin/env python3
import json, pathlib, sys
prompt = sys.stdin.read()
model = sys.argv[sys.argv.index('--model') + 1]
effort = sys.argv[sys.argv.index('--config') + 1]
if model == 'gpt-6-luna':
    assert 'model_reasoning_effort="low"' == effort
    answer = ''' + repr(ANSWER) + '''
else:
    assert model == 'gpt-6.1-sol'
    assert 'model_reasoning_effort="medium"' == effort
    assert 'Pre-analyzed Change Annotations' in prompt
    assert 'Adds a --status flag' in prompt
    answer = ''' + repr(prose) + '''
pathlib.Path(sys.argv[sys.argv.index('--output-last-message') + 1]).write_text(answer)
print(json.dumps({'type': 'turn.completed'}))
''')
        executable.chmod(0o700)
        self.sync.codex_executable = str(executable)
        with patch.dict(os.environ, {'CHANGELOG_AGENT_LOG_DIR': str(self.root / 'logs')}), \
             patch.object(self.sync, 'generate_string_diff', return_value=None), \
             patch.object(self.sync, '_write_official_release_notes', return_value=None):
            self.assertTrue(self.sync.generate_changelog('1.2.3'))
        text = (self.sync.changelog_dir / 'changelog-v1.2.3.md').read_text()
        self.assertIn('using codex `gpt-6.1-sol` (medium effort)', text)
        self.assertIn('annotations (`gpt-6-luna`)', text)

    def test_failed_annotations_block_prose_and_preserve_existing_changelog(self):
        target = self.sync.changelog_dir / 'changelog-v1.2.3.md'
        target.write_text('accepted previous output')
        with patch.object(self.sync, 'generate_string_diff', return_value=None), \
             patch.object(self.sync, '_write_official_release_notes', return_value=None), \
             patch.object(self.sync, '_annotate_all_batches', side_effect=AgentRunnerError('bad batch')), \
             patch.object(self.sync, '_run_agent_query') as prose:
            self.assertFalse(self.sync.generate_changelog('1.2.3'))
        prose.assert_not_called()
        self.assertEqual(target.read_text(), 'accepted previous output')

    def test_redo_annotations_use_selected_iteration(self):
        selected = self.sync.changes_dir / 'changes-v1.2.3-2.md'
        selected.write_text(DIFF)
        with patch.object(self.sync, 'generate_string_diff', return_value=None), \
             patch.object(self.sync, '_write_official_release_notes', return_value=None), \
             patch.object(self.sync, '_run_annotation_pipeline', side_effect=AgentRunnerError('stop')) as annotate:
            self.assertFalse(self.sync.generate_changelog('1.2.3', iteration=2))
        self.assertEqual(annotate.call_args.args, ('1.2.3', selected))

    def test_unified_diff_hunks_keep_file_context(self):
        self.diff.write_text('''diff --git a/cli.rs b/cli.rs
--- a/cli.rs
+++ b/cli.rs
@@ -1 +1 @@
-old
+new
@@ -8 +8 @@
-old2
+new2
diff --git a/new.rs b/new.rs
new file mode 100644
--- /dev/null
+++ b/new.rs
@@ -0,0 +1 @@
+new_file
''')
        slices = parse_slices(self.diff)
        self.assertEqual(len(slices), 3)
        self.assertIn('diff --git a/cli.rs b/cli.rs', slices[1]['content'])
        self.assertNotIn('+new\n', slices[1]['content'])
        self.assertEqual(slices[2]['section'], 'added')
        self.assertEqual(len(make_batches(slices)), 2)
        with self.assertRaises(ValueError):
            make_batches(slices, batch_size=0)


if __name__ == '__main__':
    unittest.main()


class AnnotationSummaryTests(unittest.TestCase):
    def test_primary_term_prefers_known_feature_then_env_then_flag(self):
        from annotation_summary import primary_evidence_term
        self.assertEqual(primary_evidence_term({'name': 'Skill tool', 'evidence': '"--worktree"'}), 'Skill')
        self.assertEqual(primary_evidence_term({'summary': 'Adds CLAUDE_CODE_FOO_BAR'}), 'CLAUDE_CODE_FOO_BAR')
        self.assertEqual(primary_evidence_term({'evidence': ['--json', '--status-line']}), '--status-line')
        self.assertIsNone(primary_evidence_term({'evidence': '"short"'}))

    def test_summary_tiers_and_flags(self):
        from annotation_summary import format_annotation_summary
        text = format_annotation_summary([
            {'importance': 5, 'name': 'Big', 'user_facing': True, 'feature_flag': 'tengu_x', 'disabled': True},
            {'importance': 3, 'name': 'Mid'},
            {'importance': 1, 'name': 'Small'},
        ], '1.2.3')
        self.assertIn('HIGH IMPORTANCE (i=4-5, 1 items)', text)
        self.assertIn('★i=5 Big', text)
        self.assertIn('[tengu_x!disabled]', text)
        self.assertLess(text.index('Mid'), text.index('Small'))
