"""Local-only Project Blocks server. Python standard library, no installation."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import argparse
import hashlib
import json
import os
import threading
import webbrowser
import time
import uuid

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data/project.json'
LOCK = threading.Lock()
MAX_BYTES = 16 * 1024 * 1024
STATUSES = {'todo', 'doing', 'blocked', 'review', 'done'}


def write_json(path, value):
    raw = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temp.write_bytes(raw)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    return raw


def read_activity():
    path = DATA.with_name('activity.json')
    if not path.exists():
        return {'version': 1, 'nodes': {}}
    return json.loads(path.read_bytes())


def validate(p):
    if not isinstance(p, dict) or not isinstance(p.get('nodes'), list):
        raise ValueError('工程必须包含 nodes 数组')
    nodes = p['nodes']
    if not isinstance(p.get('title', ''), str):
        raise ValueError('工程标题必须是字符串')
    for field in ('groups', 'stickyNotes', 'customRoutes'):
        if not isinstance(p.get(field, []), list):
            raise ValueError(f'{field} 必须是数组')
    viewport = p.get('viewport', {})
    if not isinstance(viewport, dict) or any(not isinstance(viewport.get(k), (int, float)) for k in ('x', 'y', 'scale')) or not 0 < viewport['scale'] <= 10:
        raise ValueError('视口参数无效')
    if len(nodes) > 2000:
        raise ValueError('单个工程最多 2000 张卡片')
    ids = [n.get('id') for n in nodes if isinstance(n, dict)]
    if len(ids) != len(nodes) or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('卡片 ID 必须是非空且唯一的字符串')
    known = set(ids)
    for n in nodes:
        for axis in ('x', 'y'):
            if not isinstance(n.get(axis), (int, float)) or not (-1000000 <= n[axis] <= 1000000):
                raise ValueError('卡片坐标无效')
        if not isinstance(n.get('choices', []), list):
            raise ValueError('输出关系必须是数组')
        for c in n.get('choices', []):
            if not isinstance(c, dict) or not isinstance(c.get('id'), str):
                raise ValueError('输出关系需要 ID')
            if c.get('target') and c['target'] not in known:
                raise ValueError('关系指向不存在的卡片')
        if n.get('defaultNext') and n['defaultNext'] not in known:
            raise ValueError('关系指向不存在的卡片')
    return p


def read_data():
    raw = DATA.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'app'), **kwargs)

    def json_response(self, status, value):
        raw = json.dumps(value, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == '/api/info':
            return self.json_response(200, {'app': 'project-blocks', 'apiVersion': 2, 'dataFile': str(DATA), 'projectRoot': str(DATA.parent.parent.parent if DATA.parent.name == 'data' else DATA.parent)})
        if self.path == '/api/activity':
            try:
                with LOCK:
                    activity = read_activity()
                    p, _ = read_data()
                    nodes = {n['id']: n for n in p['nodes']}
                    # External JSON edits are also authoritative over old runs.
                    activity['nodes'] = {key: entry for key, entry in activity['nodes'].items()
                        if key in nodes and entry.get('status') == nodes[key].get('workflow', {}).get('status')}
                return self.json_response(200, activity)
            except (ValueError, OSError) as e:
                return self.json_response(422, {'error': str(e)})
        if self.path == '/api/project':
            try:
                with LOCK:
                    p, rev = read_data()
                self.json_response(200, {'project': validate(p), 'revision': rev, 'dataFile': str(DATA)})
            except (ValueError, OSError) as e:
                self.json_response(422, {'error': str(e)})
        elif self.path.startswith('/api/'):
            self.json_response(404, {'error': '接口不存在'})
        else:
            super().do_GET()

    def do_POST(self):
        if self.path != '/api/activity':
            return self.json_response(404, {'error': '接口不存在'})
        origin = self.headers.get('Origin')
        if origin and origin not in {f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'}:
            return self.json_response(403, {'error': '仅接受本地进度更新'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 65536:
                return self.json_response(413, {'error': '进度请求为空或过大'})
            body = json.loads(self.rfile.read(length))
            node_id, status = body.get('nodeId'), body.get('status')
            if status is not None and status not in STATUSES:
                raise ValueError('工序状态无效')
            for field in ('message', 'runId'):
                if field in body and (not isinstance(body[field], str) or len(body[field]) > 2000):
                    raise ValueError(f'{field} 必须是最多 2000 字符的字符串')
            progress = body.get('progress')
            if progress is not None and (type(progress) not in (int, float) or not 0 <= progress <= 100):
                raise ValueError('进度必须是 0 到 100 的数字')
            evidence = body.get('evidence', [])
            if not isinstance(evidence, list) or any(not isinstance(e, str) for e in evidence):
                raise ValueError('验收证据必须是字符串数组')
            with LOCK:
                p, revision = read_data()
                node = next((n for n in p['nodes'] if n['id'] == node_id), None)
                if node is None:
                    raise ValueError('卡片不存在，请先建立真实工序')
                activity = read_activity()
                old = activity['nodes'].get(node_id, {})
                if status is None and (not body.get('runId') or body['runId'] != old.get('runId') or old.get('status') != 'doing'):
                    return self.json_response(409, {'error': '执行已结束或被另一个执行接管'})
                if status is None and node.get('workflow', {}).get('status') != 'doing':
                    return self.json_response(409, {'error': '工程状态已变化，旧执行不能继续上报心跳'})
                # A wrapper may only finish its own run, never a later agent's work.
                if body.get('expectedRunId') and body['expectedRunId'] != old.get('runId'):
                    return self.json_response(409, {'error': '执行已被另一个执行接管'})
                if status == 'done':
                    if not evidence:
                        raise ValueError('标记完成需要实际验收证据')
                    for source in p['nodes']:
                        dependencies = [c.get('target') for c in source.get('choices', []) if c.get('tag', '前置依赖') == '前置依赖'] if source.get('choices') else [source.get('defaultNext')]
                        if node_id in dependencies and source.get('workflow', {}).get('status') != 'done':
                            raise ValueError('仍有前置工序未完成')
                now = time.time() * 1000
                entry = {**old, 'status': status or old['status'], 'updatedAt': now}
                for field in ('message', 'runId'):
                    if field in body:
                        entry[field] = body[field]
                if status is not None:
                    entry['progress'] = progress
                    if 'runId' not in body:
                        entry['runId'] = uuid.uuid4().hex
                    node.setdefault('workflow', {})['status'] = status
                    if evidence:
                        node['workflow']['evidence'] = list(dict.fromkeys(node['workflow'].get('evidence', []) + evidence))
                    validate(p)
                    DATA.with_suffix('.backup.json').write_bytes(DATA.read_bytes())
                    revision = hashlib.sha256(write_json(DATA, p)).hexdigest()
                elif progress is not None:
                    entry['progress'] = progress
                activity['nodes'][node_id] = entry
                activity['updatedAt'] = now
                write_json(DATA.with_name('activity.json'), activity)
            return self.json_response(200, {'revision': revision, 'activity': entry})
        except (ValueError, TypeError, OSError, AttributeError, KeyError) as e:
            return self.json_response(422, {'error': str(e)})

    def do_PUT(self):
        # Same-origin JSON only; bind loopback and reject browser cross-origin writes.
        if self.path != '/api/project':
            return self.json_response(404, {'error': '接口不存在'})
        origin = self.headers.get('Origin')
        if origin and origin not in {f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'}:
            return self.json_response(403, {'error': '仅接受本地页面保存'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BYTES:
                return self.json_response(413, {'error': '文件为空或超过 16 MB'})
            body = json.loads(self.rfile.read(length))
            p = validate(body.get('project'))
            with LOCK:
                previous, revision = read_data()
                if body.get('revision') != revision:
                    return self.json_response(409, {'error': '磁盘工程已更新，请先处理版本冲突'})
                raw = json.dumps(p, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')
                DATA.with_suffix('.backup.json').write_bytes(DATA.read_bytes())
                temp = DATA.with_suffix('.tmp')
                temp.write_bytes(raw)
                os.replace(temp, DATA)
                revision = hashlib.sha256(raw).hexdigest()
                activity = read_activity()
                by_id = {n['id']: n for n in p['nodes']}
                for old in previous['nodes']:
                    current = by_id.get(old['id'])
                    if current is None or current.get('workflow', {}).get('status') != old.get('workflow', {}).get('status'):
                        activity['nodes'].pop(old['id'], None)
                write_json(DATA.with_name('activity.json'), activity)
            self.json_response(200, {'revision': revision})
        except (ValueError, TypeError, OSError, AttributeError) as e:
            self.json_response(422, {'error': str(e)})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--data', type=Path, default=DATA, help='Project JSON path')
    args = parser.parse_args()
    DATA = args.data.resolve()
    if not DATA.exists():
        example = ROOT / 'data/example.project.json'
        if args.data == ROOT / 'data/project.json' and example.exists():
            DATA.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation preserves another launcher's first save.
            try:
                with DATA.open('xb') as initial:
                    initial.write(example.read_bytes())
            except FileExistsError:
                pass
        else:
            parser.error('Project JSON does not exist; initialize the project before starting.')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'Project Blocks: {url}\nData: {DATA}', flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
