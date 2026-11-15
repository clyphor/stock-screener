"""Keep run output private.

The repo is public, so anything a workflow prints can be read by anyone in GitHub's Actions tab. When the
SUPABASE_SERVICE_KEY secret is set, this runs the screener with its output written to a file instead of the
screen, and `python privlog.py --upload` saves that file to the database (private_files, readable only by the
admin account). Without the key (e.g. test runs) the output is printed as normal.

  python privlog.py python run.py --markets US     # run quietly
  python privlog.py --upload daily                 # save the output privately (run with `if: always()`)
"""
import os
import subprocess
import sys
from datetime import datetime, timezone

OUT = "/tmp/run_output.txt"
PRIVATE = bool(os.environ.get("SUPABASE_SERVICE_KEY"))


def run(cmd):
    with open(OUT, "w") as f:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                             env=dict(os.environ, PYTHONUNBUFFERED="1"))
        for line in p.stdout:
            f.write(line)
            f.flush()
            if not PRIVATE:
                sys.stdout.write(line)
        code = p.wait()
    if PRIVATE:
        print(f"Finished (exit code {code}). Output is private — open the Run log on the page while signed in as admin.")
    return code


def upload(kind):
    if not PRIVATE or not os.path.exists(OUT):
        return 0
    import gate
    text = open(OUT, errors="replace").read()[-400000:]
    name = datetime.now(timezone.utc).strftime(f"raw/%Y-%m-%d_%H%M_{kind}.txt")
    ok = gate.private(name, {"text": text}) and gate.private(f"raw/latest_{kind}.txt", {"text": text, "name": name})
    print("Output saved privately." if ok else "Couldn't save the output privately.")
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["--upload"]:
        sys.exit(upload(sys.argv[2] if len(sys.argv) > 2 else "run"))
    sys.exit(run(sys.argv[1:]))
