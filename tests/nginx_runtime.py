"""Optional Docker integration test: python tests/nginx_runtime.py."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time

import yaml

ROOT = Path(__file__).resolve().parents[1]
HELM = os.environ.get('HELM', 'helm')


def run(*args, check=True):
    result = subprocess.run(args, text=True, capture_output=True)
    if check and result.returncode:
        raise RuntimeError(f'{args[:3]}: {result.stdout}\n{result.stderr}')
    return result


def docker(*args, **kwargs):
    return run('docker', *args, **kwargs)


CLIENT = r'''
const http = require('node:http');
const assert = require('node:assert/strict');
const data = JSON.parse(process.argv[1]);
async function request(host, path, headers = {}, method = 'GET', body = '') {
  return new Promise((resolve, reject) => {
    const req = http.request({hostname: host, port: 80, path, method, headers}, res => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => resolve({status: res.statusCode, body: Buffer.concat(chunks)}));
    });
    req.setTimeout(10000, () => req.destroy(new Error('timeout')));
    req.on('error', reject);
    req.end(body);
  });
}
(async () => {
  for (const host of data.hosts) {
    if (data.baseline && host.includes(':')) {
      await assert.rejects(request(host, '/-/ping'), {code: 'ECONNREFUSED'});
      console.log('baseline: IPv6 connection refused as reported');
      continue;
    }
    assert.equal((await request(host, '/-/ping')).status, 200);
    if (data.baseline) continue;
    const tokens = {};
    for (const username of ['alice', 'bob']) {
      const response = await request(host, '/-/verdaccio/sec/login', {'Content-Type': 'application/json'}, 'POST', JSON.stringify({username, password: 'test-password'}));
      assert.equal(response.status, 200, 'test user login: ' + response.body);
      tokens[username] = JSON.parse(response.body).token;
      assert.ok(tokens[username]);
    }
    for (const path of ['/ipv6-private', '/ipv6-private/-/ipv6-private-1.0.0.tgz']) {
      assert.equal((await request(host, path)).status, 401, 'anonymous denial');
      assert.equal((await request(host, path, {Authorization: 'Bearer invalid-test-token'})).status, 401, 'invalid credentials');
      assert.equal((await request(host, path, {Authorization: 'Bearer ' + tokens.bob})).status, 403, 'forbidden user');
      const response = await request(host, path, {Authorization: 'Bearer ' + tokens.alice});
      assert.equal(response.status, 200, 'authorized user');
      if (path.endsWith('.tgz')) {
        assert.equal(require('node:crypto').createHash('sha1').update(response.body).digest('hex'), data.shasum);
      } else {
        assert.equal(JSON.parse(response.body).name, 'ipv6-private');
      }
      assert.equal((await request(host, path)).status, 401, 'denied after authorized read');
      assert.equal((await request(host, path, {'X-Real-IP': '127.0.0.1', 'X-Forwarded-For': '127.0.0.1'})).status, 401, 'forged IP headers do not bypass auth');
    }
    assert.equal((await request(host, '/ipv6-private', {'Content-Length': String(101 * 1024 * 1024)}, 'PUT')).status, 413, 'shared body size limit');
    console.log(host + ': ping, metadata/tarball auth, invalid/forbidden users, post-auth denial, forged headers, 413 OK');
  }
})().catch(error => {console.error(error); process.exit(1);});
'''


def client(network, hosts, sha, baseline=False):
    result = docker('run', '--rm', '--network', network, 'node:24.15.0-alpine',
                    'node', '-e', CLIENT,
                    json.dumps({'hosts': hosts, 'shasum': sha, 'baseline': baseline}))
    print(result.stdout, end='', flush=True)


def main():
    chart = yaml.safe_load((ROOT / 'charts/verdaccio/Chart.yaml').read_text())
    backend_image = 'verdaccio/verdaccio:' + str(chart['appVersion'])
    PREFIX = 'chart195-' + str(os.getpid())
    containers = []
    networks = []

    with tempfile.TemporaryDirectory(prefix='chart195-') as temp:
        temp = Path(temp)
        temp.chmod(0o755)
        storage = temp / 'storage'
        storage.mkdir(mode=0o777)
        storage.chmod(0o777)
        package_dir = storage / 'ipv6-private'
        package_dir.mkdir(mode=0o777)
        package_dir.chmod(0o777)
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode='w:gz') as archive:
            contents = b'{"name":"ipv6-private","version":"1.0.0"}'
            info = tarfile.TarInfo('package/package.json')
            info.size = len(contents)
            archive.addfile(info, io.BytesIO(contents))
        tarball = buf.getvalue()
        sha = hashlib.sha1(tarball).hexdigest()
        (package_dir / 'ipv6-private-1.0.0.tgz').write_bytes(tarball)
        (package_dir / 'package.json').write_text(json.dumps({
            'name': 'ipv6-private', '_rev': '1-test',
            'versions': {'1.0.0': {'name': 'ipv6-private', 'version': '1.0.0',
                'dist': {'tarball': 'http://localhost:4873/ipv6-private/-/ipv6-private-1.0.0.tgz', 'shasum': sha}}},
            'dist-tags': {'latest': '1.0.0'}, '_uplinks': {}, '_distfiles': {}, '_attachments': {},
        }))
        # Test-only users and legacy hashes; no real credentials are read or used.
        password = '{SHA}' + base64.b64encode(hashlib.sha1(b'test-password').digest()).decode()
        (temp / 'htpasswd').write_text(f'alice:{password}\nbob:{password}\n')
        (temp / 'config.yaml').write_text(yaml.safe_dump({
            'storage': '/verdaccio/storage',
            'auth': {'htpasswd': {'file': '/verdaccio/conf/htpasswd', 'max_users': -1}},
            'uplinks': {},
            'security': {'api': {'legacy': False, 'jwt': {'sign': {'expiresIn': '1h'}, 'verify': {}}}},
            'packages': {'ipv6-private': {'access': 'alice', 'publish': 'alice'},
                         '**': {'access': '$authenticated', 'publish': '$authenticated'}},
            'log': {'type': 'stdout', 'format': 'pretty', 'level': 'warn'},
        }, sort_keys=False))
        for name, enabled in [('dual', True), ('v4', False)]:
            result = run(HELM, 'template', 'npm', str(ROOT / 'charts/verdaccio'),
                         '--set', 'cachingNginx.enabled=true',
                         '--set', 'cachingNginx.ipv6Enabled=' + str(enabled).lower())
            config = next(doc for doc in yaml.safe_load_all(result.stdout)
                          if doc and doc['kind'] == 'ConfigMap' and 'default.conf' in doc.get('data', {}))
            path = temp / name
            path.mkdir()
            for filename, contents in config['data'].items():
                (path / filename).write_text(contents)

        def start_nginx(name, backend, mode):
            containers.append(name)
            docker('run', '-d', '--name', name, '--network', 'container:' + backend,
                   '-v', f'{temp / mode / "nginx.conf"}:/etc/nginx/nginx.conf:ro',
                   '-v', f'{temp / mode / "default.conf"}:/etc/nginx/conf.d/default.conf:ro',
                   '--entrypoint', 'nginx', 'nginx:1.25.0', '-g', 'daemon off;')
            docker('exec', name, 'nginx', '-t')

        try:
            for index, mode in enumerate(['dual', 'ipv6-only'], start=1):
                network = PREFIX + '-' + mode
                networks.append(network)
                args = ['network', 'create', '--internal', '--ipv6', '--subnet', f'fd95:195:{index}::/64']
                if mode == 'ipv6-only':
                    args.append('--ipv4=false')
                docker(*args, network)
                backend = PREFIX + '-' + mode + '-backend'
                containers.append(backend)
                docker('run', '-d', '--name', backend, '--network', network,
                       '-v', f'{temp / "config.yaml"}:/verdaccio/conf/config.yaml:ro',
                       '-v', f'{temp / "htpasswd"}:/verdaccio/conf/htpasswd:ro',
                       '-v', f'{storage}:/verdaccio/storage', backend_image)
                for attempt in range(40):
                    ready = docker('exec', backend, 'node', '-e',
                        "require('node:http').get('http://127.0.0.1:4873/-/ping',r=>{r.resume();process.exit(r.statusCode===200?0:1)}).on('error',()=>process.exit(1))", check=False)
                    if not ready.returncode:
                        break
                    time.sleep(0.5)
                else:
                    raise RuntimeError(docker('logs', backend).stdout)
                addresses = json.loads(docker('inspect', backend).stdout)[0]['NetworkSettings']['Networks'][network]
                hosts = [addresses[key] for key in ['IPAddress', 'GlobalIPv6Address'] if addresses[key]]
                assert any(':' in host for host in hosts), addresses
                if mode == 'ipv6-only':
                    assert not addresses['IPAddress'], addresses
                if mode == 'dual':
                    baseline = PREFIX + '-baseline'
                    start_nginx(baseline, backend, 'v4')
                    client(network, hosts, sha, baseline=True)
                    docker('rm', '-f', baseline)
                    containers.remove(baseline)
                proxy = PREFIX + '-' + mode + '-proxy'
                start_nginx(proxy, backend, 'dual')
                client(network, hosts, sha)
                print(mode + ' passed', flush=True)

            # These sysctls disable IPv6 addresses, not the AF_INET6 socket family.
            # Check both configs; this does not simulate a kernel with ipv6.disable=1.
            for mode in ('dual', 'v4'):
                docker('run', '--rm', '--network', 'none',
                       '--sysctl', 'net.ipv6.conf.all.disable_ipv6=1',
                       '--sysctl', 'net.ipv6.conf.default.disable_ipv6=1',
                       '-v', f'{temp / mode / "nginx.conf"}:/etc/nginx/nginx.conf:ro',
                       '-v', f'{temp / mode / "default.conf"}:/etc/nginx/conf.d/default.conf:ro',
                       '--entrypoint', 'nginx', 'nginx:1.25.0', '-t')
                print(mode + ' config: nginx -t passed with IPv6 disabled via sysctl', flush=True)
        except Exception:
            for container in containers:
                if container.endswith('-backend'):
                    print(docker('logs', container, check=False).stdout, flush=True)
                    print(docker('exec', container, 'cat', '/verdaccio/conf/config.yaml', check=False).stdout, flush=True)
            raise
        finally:
            for container in reversed(containers):
                docker('rm', '-f', container, check=False)
            for network in reversed(networks):
                docker('network', 'rm', network, check=False)


if __name__ == "__main__":
    main()
