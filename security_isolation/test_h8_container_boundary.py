"""H8 OS isolation checks on a disposable Github-hosted Docker container."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from prototypes.camel_selective_v0.process_boundary_v0 import request

IMAGE = os.environ.get("CAMEL_H8_IMAGE", "python:3.12-alpine")

@unittest.skipUnless(sys.platform.startswith("linux"), "Linux required")
class H8ContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv("CAMEL_H8_ENABLED") != "1":
            raise unittest.SkipTest("Explicit H8 workflow only")
        subprocess.run(["docker", "info"], check=True,
                       stdout=subprocess.DEVNULL, timeout=15)
        cls.temp = tempfile.TemporaryDirectory(prefix="h8-")
        cls.root = Path(cls.temp.name)
        cls.ipc = cls.root / "ipc"
        cls.ipc.mkdir(mode=0o755)
        cls.host_private = cls.root / "host-private"
        cls.host_private.mkdir(mode=0o700)
        (cls.host_private / "synthetic-canary.txt").write_text("SYNTHETIC_HOST_PRIVATE")
        # Keep the temporary root private (0700); Docker daemon binds only ipc.
        cls.path = str(cls.ipc / "adapter.sock")
        cls.checkout = Path(__file__).resolve().parents[1]
        cls.adapter = subprocess.Popen(
            [sys.executable, "-m",
             "prototypes.camel_selective_v0.process_boundary_v0",
             "--socket", cls.path, "--approved-id", "USR-0042"],
            cwd=cls.checkout, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, close_fds=True)
        for _ in range(150):
            if cls.adapter.poll() is not None:
                raise RuntimeError(cls.adapter.stderr.read().decode()[:500])
            if Path(cls.path).exists():
                break
            time.sleep(.02)
        else:
            raise RuntimeError("H7 synthetic adapter socket never bound")
        os.chmod(cls.path, 0o660)  # restricted group access only, no world bits

    @classmethod
    def tearDownClass(cls):
        cls.adapter.terminate()
        try:
            cls.adapter.wait(timeout=3)
        except subprocess.TimeoutExpired:
            cls.adapter.kill()
            cls.adapter.wait(timeout=3)
        cls.adapter.stderr.close()
        cls.temp.cleanup()

    def guest(self, code):
        command = [
            "docker", "run", "--rm", "--pull=never",
            "--network=none", "--read-only", "--cap-drop=ALL",
            "--security-opt=no-new-privileges", "--pids-limit=32",
            "--memory=192m", "--cpus=1", "--user=65534:65534",
            # Deliberate single synthetic socket group access, not an OS auth claim.
            "--group-add", str(os.stat(self.path).st_gid),
            "--tmpfs=/tmp:rw,noexec,nosuid,size=4m",
            "--mount", "type=bind,src=" + str(self.ipc) + ",dst=/ipc,readonly",
            "--workdir=/", IMAGE, "python", "-c", code,
        ]
        out = subprocess.run(command, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr[-1200:])
        return json.loads(out.stdout.strip())

    def test_H8_01_enforces_unprivileged_process_without_capabilities(self):
        x = self.guest(
            "import os,json;"
            "s=open('/proc/self/status').read().splitlines();"
            "d=dict(l.split(':',1) for l in s if ':' in l);"
            "print(json.dumps([os.geteuid(),os.getegid(),"
            "d['CapEff'].strip(),d['NoNewPrivs'].strip(),os.getpid()]))"
        )
        self.assertEqual(x, [65534, 65534, "0000000000000000", "1", 1])

    def test_H8_02_read_only_filesystem_and_network_isolation(self):
        x = self.guest(
            "import os,json;"
            "print(json.dumps([bool(os.statvfs('/').f_flag & os.ST_RDONLY),"
            "sorted(os.listdir('/sys/class/net')),os.access('/tmp',os.W_OK)]))"
        )
        self.assertEqual(x, [True, ["lo"], True])

    def test_H8_03_no_access_to_host_private_files_or_docker_daemon(self):
        x = self.guest(
            "from pathlib import Path;import json;"
            "print(json.dumps([Path('/host-private/synthetic-canary.txt').exists(),"
            "Path('/var/run/docker.sock').exists(),"
            "Path('/home/runner/work').exists()]))"
        )
        self.assertEqual(x, [False, False, False])

    def test_H8_04_even_reachable_socket_denied_to_separate_container_pid(self):
        x = self.guest(
            "import socket,json;"
            "s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);"
            "s.settimeout(3);s.connect('/ipc/adapter.sock');"
            "s.sendall(b'{\"user_id\":\"USR-0042\"}\\n');"
            "print(json.dumps(json.loads(s.recv(1024).decode().strip())))"
        )
        self.assertEqual(x, {"attempted": False, "code": "DENY_PEER_PID"})
        trusted = request(self.path, {"user_id":"USR-0042"},
                          expected_server_pid=self.adapter.pid)
        self.assertEqual(trusted,
                         {"attempted":True,"code":"HANDLER_RETURNED"})

if __name__ == "__main__":
    unittest.main()
