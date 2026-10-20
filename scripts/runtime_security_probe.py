"""Read-only checks of the disposable CI runtime containers; never print environment."""

import json
import subprocess


def main():
    result = {}
    for service, uid in (("web", 10001), ("db", 999)):
        probe = """
set -eu
id -u
awk '/^CapEff:/ {print $2} /^NoNewPrivs:/ {print $2}' /proc/self/status
"""
        output = subprocess.check_output(
            ["docker", "compose", "exec", "-T", service, "sh", "-c", probe], text=True
        ).splitlines()
        if output != [str(uid), "0000000000000000", "1"]:
            raise SystemExit("Runtime identity/capability restrictions not effective: " + service)
        result[service] = dict(uid=uid, effective_capabilities=0, no_new_privileges=True)
    setid = subprocess.check_output(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "web",
            "find",
            "/usr",
            "-xdev",
            "-type",
            "f",
            "(",
            "-perm",
            "-4000",
            "-o",
            "-perm",
            "-2000",
            ")",
            "-print",
        ],
        text=True,
    )
    if setid.strip():
        raise SystemExit("Unexpected set-ID executable in application image")
    result["web"]["usr_setid_executables"] = 0
    print("DEELVO_RUNTIME_SECURITY=" + json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
