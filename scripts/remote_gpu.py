"""Small password-from-environment SSH/SFTP helper for the GPU server.

The password is intentionally never accepted as a command-line argument and is
never written to project files, logs, manifests, or remote commands.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import os
from pathlib import Path
from pathlib import PurePosixPath
import shlex
import stat

import paramiko


HOST = "connect.westc.seetacloud.com"
PORT = 40958
USER = "root"


def connect() -> paramiko.SSHClient:
    password = os.environ.get("SEETA_PASSWORD") or getpass.getpass(
        f"Password for {USER}@{HOST}:{PORT}: "
    )
    client = paramiko.SSHClient()
    known_hosts = Path.home() / ".ssh" / "known_hosts"
    client.load_host_keys(str(known_hosts))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(HOST, port=PORT, username=USER, password=password,
                   look_for_keys=False, allow_agent=False, timeout=20)
    return client


def mkdirs(sftp: paramiko.SFTPClient, path: str) -> None:
    current = ""
    for part in PurePosixPath(path).parts:
        if part in ("/", ""):
            current = "/"
            continue
        current = current.rstrip("/") + "/" + part
        try:
            sftp.stat(current)
        except OSError:
            sftp.mkdir(current)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def remote_digest(sftp: paramiko.SFTPClient, path: str) -> str | None:
    try:
        sftp.stat(path)
    except OSError:
        return None
    channel = sftp.get_channel().get_transport().open_session()
    channel.exec_command(f"sha256sum {shlex.quote(path)}")
    result = channel.makefile("rb").read().decode("utf-8", "replace").strip().split()
    channel.makefile_stderr("rb").read()
    channel.recv_exit_status()
    return result[0] if result else None


def upload_file(sftp: paramiko.SFTPClient, local: Path, remote: str) -> None:
    remote_path = PurePosixPath(remote)
    mkdirs(sftp, str(remote_path.parent))
    local_hash = digest(local)
    existing_hash = remote_digest(sftp, remote)
    if existing_hash == local_hash:
        print(f"already verified {local} -> {remote} sha256={local_hash}", flush=True)
        return
    temporary = remote + ".uploading"
    size = local.stat().st_size
    last_percent = [-1]

    def progress(transferred: int, total: int) -> None:
        percent = int(100 * transferred / max(total, 1))
        if percent == 100 or percent >= last_percent[0] + 10:
            print(f"{local.name}: {percent}% ({transferred}/{total} bytes)", flush=True)
            last_percent[0] = percent

    sftp.put(str(local), temporary, callback=progress)
    remote_hash_cmd = f"sha256sum {shlex.quote(temporary)}"
    channel = sftp.get_channel().get_transport().open_session()
    channel.exec_command(remote_hash_cmd)
    result = channel.makefile("rb").read().decode("utf-8", "replace").strip().split()
    err = channel.makefile_stderr("rb").read().decode("utf-8", "replace")
    status = channel.recv_exit_status()
    if status != 0 or not result:
        raise RuntimeError(f"remote sha256sum failed for {remote}: {err}")
    if result[0] != local_hash:
        raise RuntimeError(f"SHA-256 mismatch for {local}: local={local_hash}, remote={result[0]}")
    try:
        sftp.posix_rename(temporary, remote)
    except (IOError, OSError):
        try:
            sftp.remove(remote)
        except OSError:
            pass
        sftp.rename(temporary, remote)
    print(f"verified {local} -> {remote} sha256={local_hash}", flush=True)


def download_tree(sftp: paramiko.SFTPClient, remote: str, local: Path) -> None:
    """Download a remote file or directory tree without modifying the remote."""
    attrs = sftp.stat(remote)
    if stat.S_ISREG(attrs.st_mode):
        local.parent.mkdir(parents=True, exist_ok=True)
        sftp.get(remote, str(local))
        print(f"downloaded {remote} -> {local} ({attrs.st_size} bytes)", flush=True)
        return
    if not stat.S_ISDIR(attrs.st_mode):
        raise ValueError(f"Unsupported remote file type: {remote}")
    local.mkdir(parents=True, exist_ok=True)
    for entry in sorted(sftp.listdir_attr(remote), key=lambda item: item.filename):
        download_tree(sftp, f"{remote.rstrip('/')}/{entry.filename}", local / entry.filename)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="op", required=True)
    ex = sub.add_parser("exec")
    ex.add_argument("command")
    put = sub.add_parser("put")
    put.add_argument("local", type=Path)
    put.add_argument("remote")
    tree = sub.add_parser("put-tree")
    tree.add_argument("local", type=Path)
    tree.add_argument("remote")
    get = sub.add_parser("get")
    get.add_argument("remote")
    get.add_argument("local", type=Path)
    get_tree = sub.add_parser("get-tree")
    get_tree.add_argument("remote")
    get_tree.add_argument("local", type=Path)
    args = parser.parse_args()

    client = connect()
    try:
        if args.op == "exec":
            stdin, stdout, stderr = client.exec_command(args.command)
            out = stdout.read().decode("utf-8", "replace")
            err = stderr.read().decode("utf-8", "replace")
            if out:
                print(out, end="")
            if err:
                print(err, end="")
            raise SystemExit(stdout.channel.recv_exit_status())
        with client.open_sftp() as sftp:
            if args.op == "get":
                download_tree(sftp, args.remote, args.local)
            elif args.op == "get-tree":
                download_tree(sftp, args.remote, args.local)
            elif args.op == "put":
                upload_file(sftp, args.local, args.remote)
            else:
                root = args.local.resolve()
                for local in sorted(path for path in root.rglob("*") if path.is_file()):
                    relative = local.relative_to(root).as_posix()
                    upload_file(sftp, local, args.remote.rstrip("/") + "/" + relative)
    finally:
        client.close()


if __name__ == "__main__":
    main()
