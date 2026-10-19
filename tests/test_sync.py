"""Offline regression checks for the scheduled archive pipeline."""
import contextlib
import io
import os
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import bun_extract
import post
from astdiff_filter import filter_astdiff
from agent_runner import AgentRunRequest, AgentRunnerError, QwenOpenAICompatRunner
from sync import ClaudeCodeSync, PROJECTS


def target_text(sync, version='0.1.1'):
    return (sync.changelog_dir / f'changelog-v{version}.md').read_text()


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sync = ClaudeCodeSync(self.root, PROJECTS['codex'], changelog=True,
                                   diff=True, changes=True, since='0.1.0',
                                   agent_provider='codex')
        self.sync.setup_directories()
        self.sync._notify_send_path = None
        self.sync._tool_version = 'test'
        self.output = io.StringIO()
        self.capture = contextlib.redirect_stdout(self.output)
        self.capture.__enter__()
        self.addCleanup(self.capture.__exit__, None, None, None)

    def test_small_published_release_is_kept(self):
        (self.sync.source_dir / '.git').mkdir()
        result = subprocess.CompletedProcess([], 0, 'rust-v0.1.0\nrust-v0.1.1\n')
        with patch('github_releases.run', return_value=result), \
             patch.object(self.sync, '_is_significant_intermediate_tag', return_value=False), \
             patch.object(self.sync, '_get_github_release', side_effect=[None, {'name': 'patch'}]):
            self.assertEqual(self.sync.get_github_releases(), ['0.1.1'])

    def test_missing_release_cached_across_runs(self):
        response = Mock(status_code=404)
        with patch('sync.requests.get', return_value=response) as get:
            self.assertIsNone(self.sync._get_github_release('0.1.1'))
            self.sync._github_release_cache.clear()
            self.assertIsNone(self.sync._get_github_release('0.1.1'))
            get.assert_called_once()

    def test_transient_metadata_failure_is_not_unreleased(self):
        import requests
        with patch('sync.requests.get', side_effect=requests.ConnectionError('offline')):
            self.assertIsNone(self.sync._write_official_release_notes('0.1.1'))
        self.assertFalse(self.sync._is_unreleased_github_version('0.1.1'))
        self.assertFalse((self.sync.archive_dir / '.github-release-cache.json').exists())

    def test_404_labels_even_a_redo_without_discovery(self):
        with patch('sync.requests.get', return_value=Mock(status_code=404)):
            self.sync._write_official_release_notes('0.1.1')
        self.assertTrue(self.sync._is_unreleased_github_version('0.1.1'))

    def test_npm_project_uses_independent_github_release_notes(self):
        sync = ClaudeCodeSync(self.root, PROJECTS['claude-code'], changelog=True,
                              agent_provider='codex')
        sync.setup_directories()
        response = Mock(status_code=200)
        response.json.return_value = {
            'name': 'v2.1.170',
            'tag_name': 'v2.1.170',
            'published_at': '2026-06-09T21:23:00Z',
            'html_url': 'https://github.com/anthropics/claude-code/releases/tag/v2.1.170',
            'body': 'Fixed sessions not saving transcripts.',
            'draft': False,
            'prerelease': False,
        }

        with patch('sync.requests.get', return_value=response) as get:
            notes = sync._write_official_release_notes('2.1.170')

        self.assertEqual(
            get.call_args.args[0],
            'https://api.github.com/repos/anthropics/claude-code/releases/tags/v2.1.170',
        )
        self.assertIn('repository: `anthropics/claude-code`', notes.read_text())
        self.assertIn('Fixed sessions not saving transcripts.', notes.read_text())
        self.assertFalse(sync._is_unreleased_github_version('2.1.170'))

    def test_generation_prompt_includes_published_release_baseline(self):
        (self.sync.diff_dir / 'v0.1.1.diff').write_text('+new feature\n')
        notes = self.sync.changes_dir / 'release-notes-v0.1.1.md'
        notes.write_text('# Official release notes\n\nFixed transcript persistence.\n')
        self.sync.ensure_changelog_prompt()
        answer = '# Changelog\n\n## Other Changes\n' + '- Fixed transcripts. ' * 30

        with patch.object(self.sync, 'generate_string_diff', return_value=None), \
             patch.object(self.sync, '_write_official_release_notes', return_value=notes), \
             patch.object(self.sync, '_run_agent_query', return_value=answer) as agent:
            self.assertTrue(self.sync.generate_changelog('0.1.1'))

        prompt = agent.call_args.args[0]
        self.assertIn('## Official Release Notes', prompt)
        self.assertIn(str(notes.resolve()), prompt)
        self.assertIn('Treat the published items as a floor', prompt)
        self.assertIn('release notes', target_text(self.sync).splitlines()[-1])

    def generate(self, answer, **kwargs):
        (self.sync.diff_dir / 'v0.1.1.diff').write_text('+new feature\n')
        self.sync.ensure_changelog_prompt()
        with patch.object(self.sync, 'generate_string_diff', return_value=None), \
             patch.object(self.sync, '_write_official_release_notes', return_value=None), \
             patch.object(self.sync, '_run_agent_query', **kwargs) as agent:
            if not kwargs:
                agent.return_value = answer
            return self.sync.generate_changelog('0.1.1')

    def test_metadata_cannot_make_a_short_answer_pass(self):
        self.assertFalse(self.generate('# Changelog\n\n## Changes\nToo short.'))
        self.assertFalse((self.sync.changelog_dir / 'changelog-v0.1.1.md').exists())
        self.assertEqual(self.sync.get_versions_to_changelog(), ['0.1.1'])
        draft = self.sync.changelog_dir / '.drafts' / 'changelog-v0.1.1.md'
        self.assertNotIn('Generated by', draft.read_text())

    def test_valid_answer_is_promoted_and_has_metadata(self):
        self.assertTrue(self.generate('# Changelog\n\n## Changes\n' + 'Evidence for a feature. ' * 15))
        target = self.sync.changelog_dir / 'changelog-v0.1.1.md'
        trailer = target.read_text().splitlines()[-2:]
        self.assertTrue(trailer[0].startswith('Generated by `harness-investigations@'))
        self.assertEqual(trailer[1], 'Inputs: raw diff')
        self.assertFalse((self.sync.changelog_dir / '.drafts' / target.name).exists())
        self.assertEqual(self.sync.get_versions_to_changelog(), [])

    def use_astdiff(self):
        astdiff_project = patch.object(self.sync.project, 'use_astdiff', True)
        astdiff_project.start()
        self.addCleanup(astdiff_project.stop)

    def generate_with_strings(self, diff_text):
        strings = '=== ADDED ===\n+ New flag\n'
        answer = '# Changelog\n\n## Other Changes\n' + '- Added a flag. ' * 30
        (self.sync.diff_dir / 'v0.1.1.diff').write_text(diff_text)
        self.sync.ensure_changelog_prompt()
        with patch.object(self.sync, 'generate_string_diff', return_value=strings), \
             patch.object(self.sync, '_write_official_release_notes', return_value=None), \
             patch.object(self.sync, '_run_agent_query', return_value=answer) as agent:
            ok = self.sync.generate_changelog('0.1.1')
        return ok, agent

    def test_astdiff_project_refuses_raw_diff_by_default(self):
        self.use_astdiff()
        ok, agent = self.generate_with_strings('+new feature\n')
        self.assertFalse(ok)
        agent.assert_not_called()
        self.assertEqual(self.sync.get_versions_to_changelog(), ['0.1.1'])

    def test_degraded_override_still_passes_code_diff(self):
        # A string diff alone must not displace the code diff.
        self.use_astdiff()
        self.sync.allow_degraded_diff = True
        ok, agent = self.generate_with_strings('+new feature\n')
        self.assertTrue(ok)
        prompt = agent.call_args.args[0]
        self.assertIn('## Code Changes (Raw Unified Diff)', prompt)
        self.assertIn('## String Literal Changes', prompt)
        self.assertEqual(target_text(self.sync).splitlines()[-1],
                         'Inputs: raw diff (astdiff unavailable), strings')

    def test_stale_filtered_astdiff_is_rebuilt(self):
        self.use_astdiff()
        stale = self.sync.changes_dir / 'changes-v0.1.1.md'
        stale.write_text('STALE')
        os.utime(stale, (0, 0))
        astdiff = ('Structural similarity: 99.0%\n\n=== Added Functions ===\n'
                   '@@@ added function newFeature\n+function newFeature() { return "--status"; }\n')
        ok, agent = self.generate_with_strings(astdiff)
        self.assertTrue(ok)
        self.assertNotIn('STALE', stale.read_text())
        self.assertIn('## Code Changes (Filtered AST Diff)', agent.call_args.args[0])

    def test_filtered_astdiff_is_preferred_and_labelled(self):
        (self.sync.changes_dir / 'changes-v0.1.1.md').write_text('Structural similarity: 99%\n')
        self.assertTrue(self.generate('# Changelog\n\n## Changes\n' + 'A change. ' * 30))
        self.assertEqual(target_text(self.sync).splitlines()[-1], 'Inputs: astdiff')

    def test_exception_preserves_existing_final(self):
        target = self.sync.changelog_dir / 'changelog-v0.1.1.md'
        target.write_text('existing accepted output')
        self.assertFalse(self.generate(None, side_effect=AgentRunnerError('offline')))
        self.assertEqual(target.read_text(), 'existing accepted output')

    def test_cleanup_failure_does_not_publish(self):
        self.sync.do_cleanup = True
        with patch.object(self.sync, 'cleanup_single_changelog', return_value=False):
            self.assertFalse(self.generate('# Changelog\n\n## Changes\n' + 'Some evidence. ' * 25))
        self.assertFalse((self.sync.changelog_dir / 'changelog-v0.1.1.md').exists())

    def test_retry_delivery_without_regenerating_or_recommitting(self):
        self.sync.git_commit = self.sync.post = True
        target = self.sync.changelog_dir / 'changelog-v0.1.1.md'
        target.write_text('accepted')
        self.sync._queue_delivery(target, '0.1.1')
        with patch.object(self.sync, 'git_commit_changelog', return_value=True) as commit, \
             patch.object(self.sync, 'post_single_changelog', side_effect=[False, True]) as publish:
            self.sync.retry_pending_deliveries()
            self.assertTrue(self.sync._delivery_path(target).exists())
            self.sync.retry_pending_deliveries()
            self.assertEqual(commit.call_count, 1)
            self.assertEqual(publish.call_count, 2)
            self.assertFalse(self.sync._delivery_path(target).exists())

    def test_commit_failure_leaves_post_pending(self):
        self.sync.git_commit = self.sync.post = True
        target = self.sync.changelog_dir / 'changelog-v0.1.1.md'
        target.write_text('accepted')
        self.sync._queue_delivery(target, '0.1.1')
        with patch.object(self.sync, 'git_commit_changelog', return_value=False), \
             patch.object(self.sync, 'post_single_changelog') as publish:
            self.sync.retry_pending_deliveries()
            publish.assert_not_called()
        self.assertTrue(json.loads(self.sync._delivery_path(target).read_text())['commit'])

    def test_unavailable_agent_is_failure(self):
        with patch.object(self.sync, '_check_agent_available', return_value=False):
            self.sync.phase_4_generate_changelogs()
        self.assertEqual(self.sync.failure_count(), 1)

    def test_scheduled_grace_defers_notification_but_direct_run_keeps_it(self):
        self.sync._notify_send_path = '/usr/bin/notify-send'
        with patch('sync.run') as notify:
            with patch.dict('os.environ', {'CHANGELOG_DEFER_FAILURE_NOTIFICATIONS': '1'}):
                self.sync._notify_failure('sync failed', 'temporary outage')
            notify.assert_not_called()
            with patch.dict('os.environ', {'CHANGELOG_DEFER_FAILURE_NOTIFICATIONS': '0'}):
                self.sync._notify_failure('sync failed', 'temporary outage')
            notify.assert_called_once()

    def test_diff_iterations_do_not_duplicate_generation(self):
        for name in ('v0.1.1.diff', 'v0.1.1-2.diff'):
            (self.sync.diff_dir / name).touch()
        self.assertEqual(self.sync.get_versions_to_changelog(), ['0.1.1'])

    def test_astdiff_perfect_match_score_does_not_hide_changed_gate(self):
        # Real 2.1.242 -> 2.1.243 output: astdiff paired the old LSP getter
        # with an unrelated getter, and emitted the new gate as an addition.
        raw = """--- pretty-v2.1.242.js
+++ pretty-v2.1.243.js
Structural similarity: 99.8%

=== Added ===

+++ Added Blr (pretty-v2.1.243.js:800913-800915)
+ function Blr() {
+   return p4("true");
+ }

=== Structural Changes ===

@@@ function 'Zpr' (was 'Blr') — structural (100.0%)
--- pretty-v2.1.242.js:790698
+++ pretty-v2.1.243.js:803321
@@ -1,3 +1,3 @@
 function Blr() {
-  return Hi5.ENABLE_LSP_TOOL;
+  return Hi5.CLAUDE_PROJECT_UUID;
 }
"""
        filtered = filter_astdiff(raw)
        self.assertIn('-  return Hi5.ENABLE_LSP_TOOL;', filtered)
        self.assertIn('+  return Hi5.CLAUDE_PROJECT_UUID;', filtered)
        self.assertIn('return p4("true");', filtered)
        self.assertNotIn('reformatting-only', filtered)

    def test_astdiff_uses_selected_executable_and_records_artifacts(self):
        sync = ClaudeCodeSync(self.root, PROJECTS['claude-code'], diff=True,
                              astdiff_executable=sys.executable)
        sync.setup_directories()
        old = self.root / 'pretty-v1.0.0.js'; old.write_text('const x = false;')
        new = self.root / 'pretty-v1.0.1.js'; new.write_text('const x = true;')
        with patch.object(sync, '_run_astdiff', return_value=subprocess.CompletedProcess([], 0, 'diff')) as diff:
            self.assertTrue(sync.generate_diff(old, new))
        self.assertEqual(diff.call_args.args[0], str(Path(sys.executable).resolve()))
        metadata = json.loads((sync.diff_dir / 'v1.0.1.meta.json').read_text())
        self.assertEqual(metadata['astdiff']['path'], str(Path(sys.executable).resolve()))
        self.assertNotEqual(metadata['older']['sha256'], metadata['newer']['sha256'])
        self.assertEqual(metadata['output']['path'], str((sync.diff_dir / 'v1.0.1.diff').resolve()))
        self.assertEqual(len(metadata['output']['sha256']), 64)

    def test_missing_astdiff_does_not_silently_use_textual_diff(self):
        sync = ClaudeCodeSync(self.root, PROJECTS['claude-code'], diff=True,
                              astdiff_executable=str(self.root / 'missing-astdiff'))
        sync.setup_directories()
        with patch('sync.run') as run:
            self.assertFalse(sync.generate_diff(self.root / 'pretty-v1.0.0.js',
                                                self.root / 'pretty-v1.0.1.js'))
        run.assert_not_called()

    def test_latest_prettifies_newest_pair_in_both_orders(self):
        for new_first in (False, True):
            sync = ClaudeCodeSync(self.root, PROJECTS['claude-code'], prettier=True,
                                  latest=True, diff=True, new_first=new_first)
            sync.setup_directories()
            for v in ('1.0.0', '1.0.1', '1.0.2'):
                (sync.original_dir / f'cli-v{v}.js').write_text('var x = 1;')
            self.assertEqual({p.name for p in sync.get_files_to_prettify()},
                             {'cli-v1.0.1.js', 'cli-v1.0.2.js'})

    def test_split_module_snapshot_bypasses_prettier_without_copying(self):
        sync = ClaudeCodeSync(self.root, PROJECTS['claude-code'], prettier=True)
        sync.setup_directories()
        original = sync.original_dir / 'cli-v2.1.271.js'
        original.write_text('// esbuild analysis snapshot\nconst feature = true;\n')
        original.with_suffix('.modules.json').write_text('{}\n')

        with patch('sync.run') as run, \
             patch.object(sync, 'update_claude_md'):
            self.assertTrue(sync.prettify_file(original))

        analysis = sync.pretty_dir / 'pretty-v2.1.271.js'
        run.assert_not_called()
        self.assertTrue(analysis.samefile(original))
        self.assertEqual(analysis.read_text(), original.read_text())

    def test_split_module_diff_uses_esbuild_snapshots_on_both_sides(self):
        sync = ClaudeCodeSync(self.root, PROJECTS['claude-code'], prettier=True,
                              diff=True, astdiff_executable=sys.executable)
        sync.setup_directories()
        originals = []
        for version_str in ('2.1.270', '2.1.271'):
            original = sync.original_dir / f'cli-v{version_str}.js'
            original.write_text(f'const version = "{version_str}";\n')
            original.with_suffix('.modules.json').write_text('{}\n')
            originals.append(original)
            with patch.object(sync, 'update_claude_md'):
                self.assertTrue(sync.prettify_file(original))

        pair = sync.get_files_to_diff(['2.1.271'])
        self.assertEqual(pair, [(originals[0], originals[1])])
        with patch.object(
            sync,
            '_run_astdiff',
            return_value=subprocess.CompletedProcess([], 0, 'raw snapshot diff'),
        ) as diff:
            self.assertTrue(sync.generate_diff(*pair[0]))
        self.assertEqual(diff.call_args.args[1:], tuple(originals))

    def test_missing_analysis_input_blocks_dependent_phases(self):
        sync = ClaudeCodeSync(self.root, PROJECTS['claude-code'], prettier=True,
                              diff=True, changes=True, changelog=True)
        sync.setup_directories()
        (sync.pretty_dir / 'pretty-v1.0.0.js').write_text('const old = true;\n')

        with patch.object(sync, '_check_agent_available', return_value=True):
            sync.phase_3_generate_diffs(['1.0.0', '1.0.1'])
            sync.phase_5_filter_diffs()
            sync.phase_4_generate_changelogs()

        output = self.output.getvalue()
        self.assertEqual(sync.failure_count(), 1)
        self.assertIn('Diff for v1.0.1 is blocked by missing analysis input', output)
        self.assertIn('Diff filtering is blocked by missing diffs for: v1.0.1', output)
        self.assertIn('Changelog generation is blocked by missing diffs for: v1.0.1', output)
        self.assertNotIn('All diffs already generated.', output)
        self.assertNotIn('All diffs already filtered.', output)
        self.assertNotIn('All changelogs already generated.', output)

    def test_since_filtered_versions_keep_existing_diff_baseline(self):
        sync = ClaudeCodeSync(self.root, PROJECTS['claude-code'], prettier=True,
                              diff=True, since='1.0.1')
        sync.setup_directories()
        old = sync.pretty_dir / 'pretty-v1.0.0.js'
        new = sync.pretty_dir / 'pretty-v1.0.1.js'
        old.write_text('const value = false;\n')
        new.write_text('const value = true;\n')

        self.assertEqual(sync.get_files_to_diff(['1.0.1']), [(old, new)])

    def test_git_commit_scopes_files_and_retries_failed_push(self):
        def git(*args):
            return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                                  capture_output=True, text=True).stdout
        git('init', '-q')
        git('config', 'user.name', 'Test')
        git('config', 'user.email', 'test@example.invalid')
        git('config', 'commit.gpgsign', 'false')
        other = self.root / 'unrelated'
        other.write_text('user work')
        git('add', 'unrelated')
        target = self.sync.changelog_dir / 'changelog-v0.1.1.md'
        target.write_text('accepted')
        with patch.object(self.sync, 'git_push_changelog', side_effect=[False, True]) as push:
            self.assertFalse(self.sync.git_commit_changelog(target, '0.1.1'))
            head = git('rev-parse', 'HEAD')
            self.assertTrue(self.sync.git_commit_changelog(target, '0.1.1'))
            self.assertEqual(git('rev-parse', 'HEAD'), head)
            self.assertEqual(push.call_count, 2)
        self.assertEqual(git('diff', '--cached', '--name-only').strip(), 'unrelated')
        self.assertIn('Assisted-by: Codex', git('log', '-1', '--format=%B'))
        self.assertFalse((self.root / 'commit-msg').exists())


class ExtractionTests(unittest.TestCase):
    def test_wrapper_offset_counts_utf8_bytes(self):
        wrapper = '(function(exports, require, module, __filename, __dirname){const x="café 🐈";})'.encode()
        self.assertEqual(bun_extract.find_js_end(wrapper + b'\x00binary', ROOT), len(wrapper))

    def graph(self, source=b'export const feature = 1;'):
        payload = bytearray()
        name = b'/$bunfs/root/cli'
        payload.extend(name + b'\0')
        source_at = len(payload)
        payload.extend(source + b'\0')
        table = len(payload)
        payload.extend(struct.pack('<12I4B', 0, len(name), source_at, len(source),
                                   0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0))
        payload.extend(struct.pack('<QIIIIII', len(payload), table, 52, 0, 0, 0, 0))
        payload.extend(b'\n---- Bun! ----\n')
        return struct.pack('<Q', len(payload)) + payload

    def test_graph_reads_exact_source_range(self):
        self.assertEqual(bun_extract.read_module_graph(self.graph()),
                         {'/$bunfs/root/cli': 'export const feature = 1;'})

    def test_graph_rejects_truncation_and_missing_source(self):
        for data in (self.graph()[:-1], self.graph(b''), self.graph(b'hello\0binary')):
            with self.subTest(data=data[:10]), self.assertRaises(RuntimeError):
                bun_extract.read_module_graph(data)

    def test_rebundle_includes_unreferenced_worker_and_unused_declarations(self):
        result = bun_extract.rebundle_modules({
            '/$bunfs/root/cli': 'console.log("main entry");',
            '/$bunfs/root/worker.js': 'export const workerFeature = "retained worker";',
        }, ROOT).decode()
        self.assertIn('retained worker', result)
        self.assertIn('main entry', result)
        self.assertIn('2 embedded Bun modules', result)


class ProviderAndPostTests(unittest.TestCase):
    def setUp(self):
        logs = tempfile.TemporaryDirectory()
        self.addCleanup(logs.cleanup)
        env = patch.dict('os.environ', {'CHANGELOG_AGENT_LOG_DIR': logs.name})
        env.start()
        self.addCleanup(env.stop)

    def test_qwen_rejects_outside_and_symlink_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            allowed = root / 'source'; allowed.mkdir()
            secret = root / 'secret'; secret.write_text('secret contents')
            (allowed / 'link').symlink_to(secret)
            for path in ('../secret', 'link'):
                response = QwenOpenAICompatRunner._exec_read_file({'path': path}, allowed, [allowed])
                self.assertIn('outside', response)
                self.assertNotIn('secret contents', response)

    def test_qwen_reads_relative_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'source').write_text('line one\nline two\n')
            response = QwenOpenAICompatRunner._exec_read_file({'path': 'source', 'offset': 2}, root, [root])
            self.assertIn('2|line two', response)
            self.assertNotIn('1|line one', response)

    def test_qwen_enforces_tools_disabled_and_truncation(self):
        runner = QwenOpenAICompatRunner('model', 'http://example.invalid')
        for choice in ({'message': {'tool_calls': [{'id': 'x'}]}},
                       {'message': {'content': 'partial'}, 'finish_reason': 'length'}):
            with patch.object(runner, '_post', return_value={'choices': [choice]}), \
                 self.assertRaises(AgentRunnerError):
                runner.run(AgentRunRequest('prompt', allowed_tools=[]))

    def test_post_dry_run_preserves_resume_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'changelog-v1.0.0.md'; target.write_text('# Changelog\n\n## Changes\ntext')
            state = {'1.0.0': {'thread_id': 'thread', 'chunks_posted': 1, 'total_chunks': 2}}
            before = json.dumps(state)
            with patch('post.save_upload_state') as save, contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(post.post_changelog(target, Mock(), state, root, 'https://example.invalid', dry_run=True))
                save.assert_not_called()
            self.assertEqual(json.dumps(state), before)

    def test_post_receipt_survives_retries_and_is_channel_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'changelog-v1.0.0.md'; target.write_text('# Changelog')
            state = {}
            with patch('post.post_to_discord', return_value=(True, 'thread', 1)) as send, \
                 contextlib.redirect_stdout(io.StringIO()):
                for channel in ('codex', 'codex', 'claude-agent-sdk'):
                    self.assertTrue(post.post_changelog(target, Mock(), state, root,
                        'https://example.invalid', project_name='server', channel_name=channel))
                self.assertEqual(send.call_count, 2)
                self.assertTrue(state['codex:1.0.0']['complete'])

    def test_subscriber_failure_keeps_its_own_cursor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / 'changelog'; directory.mkdir()
            (directory / 'changelog-v1.0.1.md').write_text('# New release')
            channels = {'codex': post.ChannelConfig('codex', 'changelog', directory, '1.0.0')}
            webhooks = [post.WebhookConfig(name, 'https://example.invalid', ['codex'])
                        for name in ('first', 'second')]
            def advance(channel, v):
                channels[channel].last_posted_version = v
            with patch('sys.argv', ['post.py', '--new', '--project', 'codex']), \
                 patch('post.get_project_root', return_value=root), \
                 patch('post.load_webhook_configs', return_value=webhooks), \
                 patch('post.load_channels', return_value=channels), \
                 patch('post.save_channel_version', side_effect=advance), \
                 patch('post.post_changelog', side_effect=[True, False, True]) as send, \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(post.main(), 1)
                self.assertEqual(channels['codex'].last_posted_version, '1.0.1')
                self.assertEqual(post.load_upload_state(root, 'second')['_channel_cursors']['codex'], '1.0.0')
                self.assertEqual(post.main(), 0)
                self.assertEqual(send.call_count, 3)
                self.assertEqual(post.load_upload_state(root, 'second')['_channel_cursors']['codex'], '1.0.1')


if __name__ == '__main__':
    unittest.main()


class SubtextTrailerTests(unittest.TestCase):
    def test_trailer_lines_become_subtext(self):
        body = '# Changelog\n\nGenerated by the team, not a trailer.\n\nText.\n\n\n'
        trailer = 'Generated by `harness-investigations@abc` using codex `m`\nInputs: astdiff\n'
        self.assertEqual(
            post.subtext_trailer(body + trailer),
            body + '-# Generated by `harness-investigations@abc` using codex `m`\n-# Inputs: astdiff\n',
        )

    def test_without_trailer_is_unchanged(self):
        self.assertEqual(post.subtext_trailer('# Changelog\n\nBody\n'), '# Changelog\n\nBody\n')
