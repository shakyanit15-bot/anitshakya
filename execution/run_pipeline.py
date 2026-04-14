from __future__ import annotations

import argparse
import subprocess


def run_cmd(cmd: list[str]) -> None:
    out = subprocess.run(cmd, check=True)
    if out.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/base.yaml")
    parser.add_argument("--profile", default=None)
    args = parser.parse_args()

    base = ["python", "-m"]
    train_cmd = base + ["models.train_ensemble", "--config", args.config, "--output", "models/artifacts"]
    wf_cmd = base + ["validation.walk_forward", "--config", args.config, "--model", "models/artifacts/ensemble.joblib"]
    report_cmd = base + ["reports.report_generator", "--config", args.config]

    if args.profile:
        train_cmd += ["--profile", args.profile]
        wf_cmd += ["--profile", args.profile]
        report_cmd += ["--profile", args.profile]

    run_cmd(train_cmd)
    run_cmd(wf_cmd)
    run_cmd(report_cmd)


if __name__ == "__main__":
    main()
