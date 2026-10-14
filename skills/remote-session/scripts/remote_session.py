#!/usr/bin/env python3
"""Stage a source snapshot and continue it through a configured remote T3 service."""
import argparse
import base64
import hashlib
import json
import os
import re
import shlex
import socket
import struct
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


def run(args, cwd=None):
    result = subprocess.run(args, cwd=cwd, capture_output=True, check=True)
    return result.stdout


def credential_path(name):
    path = Path(name)
    return (any(part in {'.git', '.ssh', '.aws', '.metamask-e2e', 'node_modules'} for part in path.parts)
            or path.name.startswith('.env') and not path.name.endswith(('.example', '.template'))
            or path.suffix.lower() in {'.pem', '.key', '.p12', '.pfx'}
            or path.name.lower() in {'credentials.json', 'credentials'})


def file_state(path):
    if path.is_symlink():
        return {'kind': 'symlink', 'target': os.readlink(path)}
    if not path.exists():
        return {'kind': 'absent'}
    if not path.is_file():
        raise ValueError(f'Cannot snapshot directory/gitlink as a file: {path}')
    return {'kind': 'file', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'executable': bool(path.stat().st_mode & 0o111)}


def stage(root, directory, extras, context):
    root = Path(run(['git', 'rev-parse', '--show-toplevel'], root).decode().strip())
    tracked = sorted(set(run(['git', 'ls-files', '-z'], root).decode().split('\0')[:-1]
                         + run(['git', 'ls-tree', '-r', '--name-only', '-z', 'HEAD'], root).decode().split('\0')[:-1]))
    extras = list(dict.fromkeys(extras))
    for name in tracked + extras:
        path = Path(name)
        if (path.is_absolute() or '..' in path.parts or credential_path(name)
                or not (root / path).parent.resolve().is_relative_to(root.resolve())):
            raise ValueError(f'Unsafe source path: {name}')
    for name in extras:
        if not (root / name).exists() and not (root / name).is_symlink():
            raise ValueError(f'Extra file missing: {name}')
    head = run(['git', 'rev-parse', 'HEAD'], root).decode().strip()
    manifest = {'head': head, 'files': {name: file_state(root / name) for name in sorted(set(tracked + extras))}}
    (directory / 'manifest.json').write_text(json.dumps(manifest))
    (directory / 'changes.patch').write_bytes(run(['git', 'diff', '--binary', 'HEAD'], root))
    run(['git', 'bundle', 'create', str(directory / 'base.bundle'), 'HEAD'], root)
    with tarfile.open(directory / 'files.tar.gz', 'w:gz') as archive:
        for name in extras:
            archive.add(root / name, arcname=name, recursive=False)
    (directory / 'context.md').write_text(Path(context).read_text())
    untracked = run(['git', 'ls-files', '--others', '--exclude-standard', '-z'], root).decode().split('\0')[:-1]
    return {'head': head, 'sourceRoot': str(root), 'omittedUntracked': sorted(set(untracked) - set(extras))}


def verify(root, manifest):
    manifest = json.loads(Path(manifest).read_text())
    head = run(['git', 'rev-parse', 'HEAD'], root).decode().strip()
    mismatches = [name for name, expected in manifest['files'].items() if file_state(Path(root) / name) != expected]
    if head != manifest['head']:
        mismatches.insert(0, 'HEAD')
    return {'status': 'failed' if mismatches else 'passed', 'checkedFiles': len(manifest['files']), 'mismatches': mismatches}


def readiness(toolkit=None):
    script = Path.home() / '.agents/skill-config/scripts/skills.py'
    skills = json.loads(run([sys.executable, str(script), 'ready']))
    result = {'skills': {key: skills[key] for key in ('repo_head', 'source_sha256')}}
    if toolkit:
        result['toolkit'] = json.loads(run(['env', 'METAMASK_E2E_ROOT=' + str(toolkit),
                                          sys.executable, str(script), 'toolkit-identity']))
    return result


def assert_readiness(expected, actual):
    if expected['skills'] != actual['skills']:
        raise ValueError('Required skills differ between hosts; publish and sync before handoff.')
    if expected.get('toolkit', {}).get('digest') != actual.get('toolkit', {}).get('digest'):
        raise ValueError('Required toolkit source differs between hosts; transfer the selected task toolkit and verify its digest before handoff.')


class RpcSocket:
    """One authenticated JSON RPC request; no dependency on a project's node_modules."""
    def __init__(self, host, port, token):
        self.socket = socket.create_connection((host, port), timeout=20)
        self.buffer = b''
        key = base64.b64encode(os.urandom(16)).decode()
        request = (f'GET /ws?orchestrationProtocol=2 HTTP/1.1\r\nHost: {host}:{port}\r\n'
                   f'Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Version: 13\r\n'
                   f'Sec-WebSocket-Key: {key}\r\nAuthorization: Bearer {token}\r\n\r\n')
        self.socket.sendall(request.encode())
        while b'\r\n\r\n' not in self.buffer:
            chunk = self.socket.recv(4096)
            if not chunk:
                raise ConnectionError('T3 connection closed during handshake')
            self.buffer += chunk
            if len(self.buffer) > 65536:
                raise ValueError('Oversized WebSocket handshake')
        headers, self.buffer = self.buffer.split(b'\r\n\r\n', 1)
        if not headers.startswith(b'HTTP/1.1 101 '):
            raise ValueError(headers.split(b'\r\n', 1)[0].decode())
        expected = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
        received = dict(line.decode().split(':', 1) for line in headers.split(b'\r\n')[1:] if b':' in line)
        if {k.lower(): v.strip() for k, v in received.items()}.get('sec-websocket-accept') != expected:
            raise ValueError('Invalid WebSocket handshake')

    def read(self, size):
        while len(self.buffer) < size:
            chunk = self.socket.recv(max(4096, size - len(self.buffer)))
            if not chunk:
                raise ConnectionError('T3 connection closed before response')
            self.buffer += chunk
        result, self.buffer = self.buffer[:size], self.buffer[size:]
        return result

    def send(self, payload, opcode=1):
        mask = os.urandom(4)
        length = len(payload)
        header = bytes([0x80 | opcode])
        if length < 126:
            header += bytes([0x80 | length])
        elif length <= 65535:
            header += bytes([0x80 | 126]) + struct.pack('!H', length)
        else:
            header += bytes([0x80 | 127]) + struct.pack('!Q', length)
        self.socket.sendall(header + mask + bytes(value ^ mask[index % 4] for index, value in enumerate(payload)))

    def call(self, tag, payload):
        self.send(json.dumps({'_tag': 'Request', 'id': '0', 'tag': tag, 'payload': payload, 'headers': []}).encode())
        message = b''
        while True:
            first, second = self.read(2)
            length = second & 127
            if length == 126:
                length = struct.unpack('!H', self.read(2))[0]
            elif length == 127:
                length = struct.unpack('!Q', self.read(8))[0]
            if length > 16 * 1024 * 1024:
                raise ValueError('Oversized T3 response')
            mask = self.read(4) if second & 128 else None
            data = self.read(length)
            if mask:
                data = bytes(value ^ mask[index % 4] for index, value in enumerate(data))
            opcode = first & 15
            if opcode == 8:
                raise ConnectionError('T3 closed the RPC socket')
            if opcode == 9:
                self.send(data, 10)
                continue
            if opcode == 10:
                continue
            if opcode not in {0, 1}:
                raise ValueError('Unexpected T3 frame type')
            message += data
            if first & 128:
                response = json.loads(message)
                message = b''
                if response.get('_tag') == 'Exit' and response.get('requestId') == '0':
                    if response['exit']['_tag'] != 'Success':
                        raise ValueError('T3 RPC rejected launch: ' + json.dumps(response['exit'])[:1000])
                    return response['exit']['value']


def remote(spec_path):
    spec_path = Path(spec_path)
    spec = json.loads(spec_path.read_text())
    directory = spec_path.parent
    if spec['mode'] == 'send':
        assert_readiness(spec['readiness'], readiness(spec.get('remoteToolkitRoot')))
    home = Path(spec.get('t3Home', '~/.t3')).expanduser()
    runtime = json.loads((home / 'userdata/server-runtime.json').read_text())
    command = shlex.split(run(['ps', '-p', str(runtime['pid']), '-o', 'command=']).decode())
    cli = command[0]
    if not Path(cli).is_file() or 'runtime/versions/' not in cli:
        raise ValueError('Cannot identify configured T3 CLI from its running service')
    sessions = []

    def issue(scopes):
        result = json.loads(run([cli, 'auth', 'session', 'issue', '--base-dir', str(home),
                                 *[value for scope in scopes for value in ['--scope', scope]],
                                 '--ttl', '10m', '--label', 'Remote session handoff', '--json']))
        sessions.append(result)
        return result['token']

    def api(path, token, payload=None):
        headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json', 'x-t3-orchestration-protocol': '2'}
        request = urllib.request.Request(f'http://{runtime["host"]}:{runtime["port"]}{path}',
                                         data=None if payload is None else json.dumps(payload).encode(), headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise ValueError(f'T3 HTTP {error.code}: {error.read().decode()[:600]}') from None

    try:
        token = issue(['orchestration:read'] if spec['mode'] == 'probe' else ['orchestration:read', 'orchestration:operate'])
        projects = api('/api/projects', token)['projects']
        if spec['mode'] == 'probe':
            rpc = RpcSocket(runtime['host'], runtime['port'], token)
            try:
                rpc.call('orchestration.getArchivedShellSnapshot', {})
            finally:
                rpc.socket.close()
            return {'status': 'connected', 'host': socket.gethostname(), 'projects': [
                {'id': item['id'], 'title': item['title'], 'workspaceRoot': item['workspaceRoot']} for item in projects]}
        repo = Path(spec['repo']).expanduser().resolve()
        run(['git', 'rev-parse', '--git-dir'], repo)
        project = next((item for item in projects if Path(item['workspaceRoot']).resolve() == repo), None)
        if project is None:
            registration = issue(['orchestration:read', 'orchestration:operate', 'settings:write'])
            project = api('/api/projects/mutate', registration, {
                'type': 'project.create', 'commandId': str(uuid.uuid4()), 'projectId': str(uuid.uuid4()),
                'title': repo.name, 'workspaceRoot': str(repo), 'createWorkspaceRootIfMissing': False, 'scripts': []})
        identifier = spec['id']
        base = 'handoff/remote-session-' + identifier
        run(['git', 'fetch', str(directory / 'base.bundle'), 'HEAD:refs/heads/' + base], repo)
        thread_id = str(uuid.uuid4())
        import_context = (f'Source handoff is staged at {directory}. Read project guidance, then import source BEFORE continuing. '
                          f'In your bound clean worktree, run git apply --check {shlex.quote(str(directory / "changes.patch"))} '
                          f'and git apply {shlex.quote(str(directory / "changes.patch"))} (skip an empty patch), then extract '
                          f'{directory}/files.tar.gz there. If source was already imported, verify it rather than overwrite it. '
                          f'Run python3 {directory}/remote_session.py verify --cwd "$PWD" --manifest {directory}/manifest.json. '
                          'A mismatch blocks further work; do not discard edits or manufacture a match. Dependencies and credentials '
                          'are separate; reuse the remote setup. Report that import verification, then continue the task below.\n\n')
        if spec.get('remoteToolkitRoot'):
            import_context += (f"Use METAMASK_E2E_ROOT={shlex.quote(spec['remoteToolkitRoot'])} for this task's toolkit. "
                               f"Its verified native source digest is {spec['readiness']['toolkit']['digest']}. "
                               "Recheck skills.py toolkit-identity before dependent work; do not substitute the default toolkit.\n\n")
        payload = {'commandId': str(uuid.uuid4()), 'threadId': thread_id, 'creationSource': 'server', 'projectId': project['id'],
                   'title': spec['title'], 'modelSelection': spec['modelSelection'], 'runtimeMode': spec['runtimeMode'],
                   'interactionMode': spec['interactionMode'], 'workspaceStrategy': {
                       'type': 'worktree', 'baseRef': base, 'branch': 't3code/remote-session-' + identifier, 'startFromOrigin': False},
                   'initialMessage': {'text': import_context + (directory / 'context.md').read_text(), 'attachments': []}}
        (directory / 'launch-input.json').write_text(json.dumps(payload))
        rpc = RpcSocket(runtime['host'], runtime['port'], token)
        try:
            try:
                result = rpc.call('orchestration.launchThread', payload)
                (directory / 'launch-result.json').write_text(json.dumps(result))
            except (TimeoutError, ConnectionError):
                # Observe the preallocated ID; never replay an ambiguous mutation.
                try:
                    api('/api/orchestration/threads/' + thread_id, token)
                except ValueError as error:
                    raise ValueError(f'Launch response missing; inspect thread {thread_id} and {directory}/launch-input.json '
                                     f'before retrying. {error}') from None
        finally:
            rpc.socket.close()
        projection = api('/api/orchestration/threads/' + thread_id, token)['projection']
        thread = projection['thread']
        return {'status': 'launched', 'threadId': thread_id, 'title': thread['title'],
                'worktreePath': thread.get('worktreePath'), 'runStatus': projection['runs'][-1]['status'],
                'staging': str(directory), 'sourceImport': 'required-before-continuation', 'url': 't3-thread://v1/' + thread_id}
    finally:
        failures = []
        for session in sessions:
            try:
                run([cli, 'auth', 'session', 'revoke', '--base-dir', str(home), session['sessionId']])
            except subprocess.CalledProcessError:
                failures.append(session['sessionId'])
        if failures:
            print(json.dumps({'cleanup': 'session-revocation-failed', 'sessionIds': failures, 'ttl': '10m'}), file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='mode', required=True)
    for mode in ['probe', 'send']:
        command = commands.add_parser(mode)
        command.add_argument('--ssh', required=True)
        command.add_argument('--t3-home', default='~/.t3')
    command.add_argument('--repo', required=True)
    command.add_argument('--cwd', default=os.getcwd())
    command.add_argument('--context', required=True)
    command.add_argument('--title', required=True)
    command.add_argument('--file', action='append', default=[])
    command.add_argument('--toolkit-root', help='Exact toolkit required by this task')
    command.add_argument('--remote-toolkit-root', help='Matching toolkit already staged on the target')
    command.add_argument('--provider', required=True)
    command.add_argument('--model', required=True)
    command.add_argument('--model-options', default='{}')
    command.add_argument('--runtime-mode', required=True, choices=['approval-required', 'auto-accept-edits', 'auto', 'full-access'])
    command.add_argument('--interaction-mode', required=True, choices=['default', 'plan'])
    command = commands.add_parser('verify')
    command.add_argument('--cwd', default=os.getcwd())
    command.add_argument('--manifest', required=True)
    command = commands.add_parser('_remote')
    command.add_argument('spec')
    args = parser.parse_args()
    if args.mode == '_remote':
        print(json.dumps(remote(args.spec)))
        return 0
    if args.mode == 'verify':
        result = verify(args.cwd, args.manifest)
        print(json.dumps(result))
        return result['status'] != 'passed'
    if not re.fullmatch(r'[a-zA-Z0-9_.@:-]+', args.ssh) or args.ssh.startswith('-'):
        raise ValueError('Invalid SSH target')
    identifier = time.strftime('%Y%m%d-') + uuid.uuid4().hex[:12]
    destination = '/tmp/t3-remote-session-' + identifier
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=yes', args.ssh]
    with tempfile.TemporaryDirectory(prefix='t3-remote-session-') as temporary:
        directory = Path(temporary)
        spec = {'id': identifier, 'mode': args.mode, 't3Home': args.t3_home}
        if args.mode == 'send':
            if bool(args.toolkit_root) != bool(args.remote_toolkit_root):
                raise ValueError('Pass both --toolkit-root and --remote-toolkit-root for a toolkit-dependent task.')
            spec['readiness'] = readiness(args.toolkit_root)
            spec['remoteToolkitRoot'] = args.remote_toolkit_root
            source = stage(args.cwd, directory, args.file, args.context)
            if source['omittedUntracked']:
                raise ValueError('Untracked files omitted; select them with --file or move unrelated files out of this handoff checkout: '
                                 + ', '.join(source['omittedUntracked']))
            spec.update(repo=args.repo, title=args.title, modelSelection={
                'instanceId': args.provider, 'model': args.model, 'options': json.loads(args.model_options)},
                        runtimeMode=args.runtime_mode, interactionMode=args.interaction_mode, source=source)
        (directory / 'spec.json').write_text(json.dumps(spec))
        (directory / 'remote_session.py').write_bytes(Path(__file__).read_bytes())
        run(ssh + [shlex.join(['mkdir', '-p', destination])])
        run(['scp', '-q', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
             *[str(path) for path in directory.iterdir()], args.ssh + ':' + destination + '/'])
        if args.mode == 'send':
            print(json.dumps({'status': 'staged', 'ssh': args.ssh, 'staging': destination, 'head': source['head']}), flush=True)
        result = run(ssh + [shlex.join(['env', 'PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin',
                                       'python3', destination + '/remote_session.py', '_remote', destination + '/spec.json'])])
        print(result.decode().strip())
        if args.mode == 'probe':
            run(ssh + [shlex.join(['rm', '-r', destination])])
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        if isinstance(error, subprocess.CalledProcessError):
            message = error.stderr.decode(errors='replace')[-1500:] or str(error)
        else:
            message = str(error)
        print(json.dumps({'status': 'failed', 'error': message}), file=sys.stderr)
        sys.exit(1)
