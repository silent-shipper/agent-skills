#!/usr/bin/env python3
"""Exercise source reconstruction and RPC framing without creating a T3 thread."""
import json
import os
import socket
import struct
import tarfile
import tempfile
import threading
import unittest
from pathlib import Path

from remote_session import RpcSocket, assert_readiness, credential_path, run, stage, verify


class RemoteSessionTests(unittest.TestCase):
    def test_handoff_requires_complete_skills_and_native_toolkit_identity(self):
        source = {'skills': {'repo_head': 'same-head', 'source_sha256': 'helpers-too'},
                  'toolkit': {'root': '/laptop/task', 'digest': 'native-source'}}
        target = {'skills': dict(source['skills']), 'toolkit': {'root': '/mini/task', 'digest': 'native-source'}}
        assert_readiness(source, target)
        target['skills']['source_sha256'] = 'different-helper'
        with self.assertRaisesRegex(ValueError, 'skills differ'):
            assert_readiness(source, target)
        target['skills'] = dict(source['skills'])
        target['toolkit']['digest'] = 'different-source'
        with self.assertRaisesRegex(ValueError, 'toolkit source differs'):
            assert_readiness(source, target)
        with self.assertRaisesRegex(ValueError, 'toolkit source differs'):
            assert_readiness(source, {'skills': source['skills']})

    def test_snapshot_reconstructs_staged_and_unstaged_edits_rename_delete_and_new_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'source'
            root.mkdir()
            run(['git', 'init', '-q'], root)
            run(['git', 'config', 'user.email', 'fixture@example.invalid'], root)
            run(['git', 'config', 'user.name', 'Fixture'], root)
            for name in ['edit', 'rename', 'delete']:
                (root / name).write_text('before\n')
            run(['git', 'add', '.'], root)
            run(['git', 'commit', '-qm', 'fixture'], root)
            run(['git', 'mv', 'rename', 'renamed'], root)
            run(['git', 'rm', '-q', 'delete'], root)
            (root / 'edit').write_text('staged\n')
            run(['git', 'add', 'edit'], root)
            (root / 'edit').write_text('unstaged after staging\n')
            (root / 'new-script').write_text('#!/bin/sh\nexit 0\n')
            (root / 'new-script').chmod(0o755)
            (root / 'link').symlink_to('edit')
            context = Path(temporary) / 'context.md'
            context.write_text('Continue fixture work')
            payload = Path(temporary) / 'payload'
            payload.mkdir()
            source = stage(root, payload, ['new-script', 'link'], context)
            self.assertEqual(source['omittedUntracked'], [])
            target = Path(temporary) / 'target'
            run(['git', 'clone', '-q', str(payload / 'base.bundle'), str(target)])
            run(['git', 'apply', str(payload / 'changes.patch')], target)
            with tarfile.open(payload / 'files.tar.gz') as archive:
                archive.extractall(target)
            self.assertEqual(verify(target, payload / 'manifest.json')['status'], 'passed')
            (target / 'delete').write_text('incorrectly retained')
            (target / 'new-script').chmod(0o644)
            result = verify(target, payload / 'manifest.json')
            self.assertEqual(set(result['mismatches']), {'delete', 'new-script'})

    def test_new_code_omissions_are_reported_and_credentials_are_refused(self):
        self.assertTrue(credential_path('.env.private-key-runtime.local'))
        self.assertTrue(credential_path('.metamask-e2e/bootstrap/profile'))
        self.assertFalse(credential_path('.env.example'))
        self.assertFalse(credential_path('apps/web/.env.local.example'))
        self.assertFalse(credential_path('apps/web/.env.e2e.secrets.example'))
        self.assertFalse(credential_path('apps/web/.env.production.template'))
        self.assertTrue(credential_path('apps/web/.env.local'))
        self.assertTrue(credential_path('apps/web/.env.local.example.backup'))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run(['git', 'init', '-q'], root)
            run(['git', 'config', 'user.email', 'fixture@example.invalid'], root)
            run(['git', 'config', 'user.name', 'Fixture'], root)
            (root / 'base').write_text('base')
            run(['git', 'add', 'base'], root)
            run(['git', 'commit', '-qm', 'fixture'], root)
            (root / 'new-code.py').write_text('pass')
            context = root.parent / (root.name + '-context.md')
            try:
                context.write_text('context')
                payload = root / '.git/payload'
                payload.mkdir()
                self.assertEqual(stage(root, payload, [], context)['omittedUntracked'], ['new-code.py'])
                with self.assertRaisesRegex(ValueError, 'Unsafe source path'):
                    stage(root, payload, ['.env.private-key-runtime.local'], context)
                (root / 'outside').symlink_to(root.parent, target_is_directory=True)
                with self.assertRaisesRegex(ValueError, 'Unsafe source path'):
                    stage(root, payload, ['outside/' + context.name], context)
            finally:
                context.unlink(missing_ok=True)

    def test_rpc_handles_masked_request_ping_and_fragmented_unicode_response(self):
        client, server = socket.socketpair()
        rpc = RpcSocket.__new__(RpcSocket)
        rpc.socket, rpc.buffer = client, b''
        errors = []

        def receive(size):
            data = b''
            while len(data) < size:
                data += server.recv(size - len(data))
            return data

        def peer():
            try:
                first, second = receive(2)
                self.assertTrue(second & 128)
                length = second & 127
                if length == 126:
                    length = struct.unpack('!H', receive(2))[0]
                elif length == 127:
                    length = struct.unpack('!Q', receive(8))[0]
                mask, data = receive(4), receive(length)
                request = json.loads(bytes(value ^ mask[index % 4] for index, value in enumerate(data)))
                self.assertEqual(request['payload']['context'], 'source' * 15000)
                response = json.dumps({'_tag': 'Exit', 'requestId': '0', 'exit': {'_tag': 'Success', 'value': {'title': 'Mini → continued'}}}, ensure_ascii=False).encode()
                middle = len(response) // 2
                server.sendall(bytes([0x89, 1]) + b'x')
                server.sendall(bytes([0x01, middle]) + response[:middle])
                server.sendall(bytes([0x80, len(response) - middle]) + response[middle:])
                pong, length = receive(2)
                self.assertEqual(pong, 0x8a)
                self.assertEqual(length, 0x81)
                mask, payload = receive(4), receive(1)
                self.assertEqual(bytes([payload[0] ^ mask[0]]), b'x')
            except BaseException as error:
                errors.append(error)
            finally:
                server.close()

        thread = threading.Thread(target=peer)
        thread.start()
        try:
            self.assertEqual(rpc.call('fixture.read', {'context': 'source' * 15000}), {'title': 'Mini → continued'})
        finally:
            client.close()
            thread.join(timeout=5)
        if errors:
            raise errors[0]


if __name__ == '__main__':
    unittest.main()
