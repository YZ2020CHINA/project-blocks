"""Report real execution progress without writing or replacing the canvas layout."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request
import uuid

import project_blocks


def post(url, body):
    request = urllib.request.Request(url + '/api/activity',
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json'}, method='POST')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=5) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(json.load(error).get('error', str(error))) from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', required=True)
    parser.add_argument('--node', required=True, help='Existing card ID')
    parser.add_argument('--status', choices=['todo', 'doing', 'blocked', 'review', 'done'])
    parser.add_argument('--message')
    parser.add_argument('--progress', type=float)
    parser.add_argument('--evidence', action='append', default=[])
    parser.add_argument('--run-id', help='Heartbeat for an existing run; omit --status')
    parser.add_argument('--run', nargs=argparse.REMAINDER, help='Command and arguments; success becomes review, failure blocked')
    args = parser.parse_args()
    try:
        project_root = Path(args.project_root).resolve(strict=True)
        root = project_root / 'project-blocks'
        if (project_root/'integration/plugin/plugin.json').is_file() and (project_root/'data/project.json').is_file():
            root = project_root
        if not (root / 'data/project.json').is_file():
            raise ValueError('工程不存在，请先 ensure；不要用进度命令创建示例工程')
        if not args.run and args.status is None and not args.run_id:
            raise ValueError('心跳需要 --run-id；开始工序请用 --status doing')
        service = project_blocks.start(root)
        run_id = args.run_id or uuid.uuid4().hex
        body = dict(nodeId=args.node, runId=run_id)
        if args.message is not None:
            body['message'] = args.message
        if args.status or args.run:
            body['status'] = 'doing' if args.run else args.status
        if args.progress is not None:
            body['progress'] = args.progress
        if args.evidence:
            body['evidence'] = args.evidence
        result = post(service['url'], body)
        if not args.run:
            print(json.dumps(dict(url=service['url'], runId=run_id, **result), ensure_ascii=False))
            return 0
        # No shell interpolation; the child inherits stdout and stderr for Codex.
        command = args.run[1:] if args.run[0] == '--' else args.run
        child = None
        try:
            child = subprocess.Popen(command, cwd=args.project_root)
            while child.poll() is None:
                try:
                    child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    post(service['url'], dict(nodeId=args.node, runId=run_id))
            code = child.returncode
        except BaseException:
            if child is not None and child.poll() is None:
                child.terminate()
                child.wait(timeout=5)
            post(service['url'], dict(nodeId=args.node, status='blocked', runId=run_id,
                expectedRunId=run_id, message='执行中断或命令无法启动，请检查后重试'))
            raise
        post(service['url'], dict(nodeId=args.node, status='review' if code == 0 else 'blocked',
            runId=run_id, expectedRunId=run_id,
            message='命令结束，等待实际验收' if code == 0 else f'命令失败，退出码 {code}'))
        return code
    except Exception as error:
        print(json.dumps(dict(error=str(error)), ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
