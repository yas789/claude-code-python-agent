"""Build/install a wheel and verify its command without checkout imports or a model."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args, *, cwd, env, expected=0):
    result = subprocess.run(
        [str(arg) for arg in args],
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != expected:
        raise RuntimeError(
            f"Command {args!r} exited {result.returncode}, expected {expected}:\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result


def main():
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT")
        and not key.startswith(("MLAB_", "OPENROUTER_"))
    }
    env["PYTHONNOUSERSITE"] = "1"
    with tempfile.TemporaryDirectory(prefix="mlab-package-") as directory:
        root = Path(directory).resolve()
        dist, venv, caller = root / "dist", root / "venv", root / "caller project"
        caller.mkdir()
        requirements = root / "requirements.txt"
        run(["uv", "build", "--wheel", "--out-dir", dist, ROOT], cwd=caller, env=env)
        wheels = list(dist.glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"Expected one newly built wheel, found {wheels}")
        run(
            [
                "uv",
                "export",
                "--project",
                ROOT,
                "--locked",
                "--no-dev",
                "--no-emit-project",
                "--output-file",
                requirements,
            ],
            cwd=caller,
            env=env,
        )
        run(["uv", "venv", "--python", sys.executable, venv], cwd=caller, env=env)
        python, command = venv / "bin/python", venv / "bin/mlab"
        run(
            ["uv", "pip", "install", "--python", python, "--require-hashes", "-r", requirements],
            cwd=caller,
            env=env,
        )
        run(
            ["uv", "pip", "install", "--python", python, "--no-deps", wheels[0]],
            cwd=caller,
            env=env,
        )
        run(["uv", "pip", "check", "--python", python], cwd=caller, env=env)
        imported = run(
            [python, "-I", "-c", "import app.cli; print(app.cli.__file__)"], cwd=caller, env=env
        )
        if not Path(imported.stdout.strip()).resolve().is_relative_to(venv):
            raise RuntimeError(f"Application was not imported from the wheel: {imported.stdout}")
        help_result = run([command, "--help"], cwd=caller, env=env)
        if "--workspace" not in help_result.stdout or "--prompt" not in help_result.stdout:
            raise RuntimeError(f"Installed command did not show help: {help_result.stdout}")
        startup = run([command], cwd=caller, env=env, expected=2)
        if startup.stdout or "Interactive mlab needs a terminal" not in startup.stderr:
            raise RuntimeError(f"Unexpected non-TTY startup: {startup}")
    print(
        "Wheel build, locked runtime install, isolated imports, help, and non-TTY startup passed."
    )


if __name__ == "__main__":
    main()
