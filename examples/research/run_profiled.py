#!/usr/bin/env python3
"""
Run the iterative research task with a sandboxing profile selector (Tx.Hx.Nx).

Profiles follow AISI guidance:
  - T: Tooling (T0 unrestricted exec, T1 restricted web, T2 no exec)
  - H: Host isolation (H0 local, H1 docker, H2 k8s, H3 proxmox)
  - N: Network isolation (N0 full, N1 allow-listed, N2 no external)

This script sets env toggles for T, maps H to Inspect's Task.sandbox, attaches
an approval preset, and runs the `iterative_task` using Inspect's programmatic eval.
"""

from __future__ import annotations

import argparse
import os
import re


def parse_profile(profile: str) -> tuple[str, str, str]:
    m = re.fullmatch(r"T([012])\.H([0123])\.N([012])", profile.strip(), flags=re.IGNORECASE)
    if not m:
        raise argparse.ArgumentTypeError(
            "Invalid profile. Expected format like 'T1.H2.N1' with T in 0..2, H in 0..3, N in 0..2"
        )
    return (f"T{m.group(1)}", f"H{m.group(2)}", f"N{m.group(3)}")


def apply_tooling(tooling: str, enable_browser: bool = False, enable_web_search: bool | None = None) -> None:
    # Clear known toggles first to avoid sticky state across runs
    for var in (
        "INSPECT_ENABLE_EXEC",
        "INSPECT_ENABLE_WEB_BROWSER",
        "INSPECT_ENABLE_WEB_SEARCH",
    ):
        os.environ.pop(var, None)

    if tooling.upper() == "T2":
        # No execution; optionally allow search if the user passes enable_web_search
        if enable_web_search:
            os.environ["INSPECT_ENABLE_WEB_SEARCH"] = "1"
        return
    if tooling.upper() == "T1":
        # Restricted: only web tools
        if enable_web_search is None or enable_web_search:
            os.environ["INSPECT_ENABLE_WEB_SEARCH"] = "1"
        return
    # T0: unrestricted (exec on). Browser is optional to keep footprint small by default.
    os.environ["INSPECT_ENABLE_EXEC"] = "1"
    if enable_browser:
        os.environ["INSPECT_ENABLE_WEB_BROWSER"] = "1"


def map_host_isolation(host: str) -> str:
    host = host.upper()
    return {"H0": "local", "H1": "docker", "H2": "k8s", "H3": "proxmox"}[host]


def main() -> int:
    from inspect_ai import Task
    from inspect_ai._eval.eval import eval as eval_tasks  # programmatic eval
    from inspect_ai.dataset import Sample

    from inspect_agents import build_iterative_agent
    from inspect_agents.approval import approval_preset
    from inspect_agents.model import resolve_model

    ap = argparse.ArgumentParser(description="Run iterative research task with Tx.Hx.Nx profile")
    ap.add_argument("prompt", nargs="*", help="Prompt text for the task")
    ap.add_argument("--profile", default="T1.H1.N1", help="Profile like T1.H1.N1 (default: T1.H1.N1)")
    ap.add_argument("--tooling", choices=["T0", "T1", "T2"], help="Override T component")
    ap.add_argument("--host", choices=["H0", "H1", "H2", "H3"], help="Override H component")
    ap.add_argument("--net", choices=["N0", "N1", "N2"], help="Override N component")
    ap.add_argument("--approval", default="dev", choices=["ci", "dev", "prod"], help="Approval preset")
    ap.add_argument("--time-limit", type=int, default=120, help="Time budget seconds (default 120)")
    ap.add_argument("--max-steps", type=int, default=20, help="Max loop steps (default 20)")
    ap.add_argument("--enable-browser", action="store_true", help="Enable web_browser tool (T0 only)")
    ap.add_argument(
        "--enable-web-search",
        action="store_true",
        help="Enable web_search tool (defaults on for T1; requires provider keys)",
    )
    ap.add_argument("--log-dir", default=os.getenv("INSPECT_LOG_DIR", "./logs"))
    args = ap.parse_args()

    # Resolve profile
    t, h, n = parse_profile(args.profile)
    if args.tooling:
        t = args.tooling
    if args.host:
        h = args.host
    if args.net:
        n = args.net

    # Apply env toggles for tooling
    apply_tooling(t, enable_browser=args.enable_browser, enable_web_search=args.enable_web_search)

    # Ensure logs/traces are repo-local unless overridden
    os.makedirs(args.log_dir, exist_ok=True)
    os.environ.setdefault("INSPECT_LOG_DIR", args.log_dir)
    os.environ.setdefault("INSPECT_TRACE_FILE", os.path.join(args.log_dir, "trace.log"))

    # Build agent
    model_id = resolve_model()
    agent = build_iterative_agent(
        prompt=(
            "You are an iterative coding agent. Work in small, verifiable steps. "
            "Use tools when needed and keep the repo tidy."
        ),
        model=model_id,
        real_time_limit_sec=int(args.time_limit),
        max_steps=int(args.max_steps),
    )

    # Build Task with sandbox + approvals
    sandbox = map_host_isolation(h)
    approval = approval_preset(args.approval)
    user_input = " ".join(args.prompt).strip() or os.getenv(
        "PROMPT", "Curate a list of arXiv papers that Quantinuum published in 2025"
    )
    task = Task(dataset=[Sample(input=user_input)], solver=agent, sandbox=sandbox, approval=approval)

    # Run programmatic eval (displays console UI and writes logs under INSPECT_LOG_DIR)
    print(f"Profile: {t}.{h}.{n} | Sandbox={sandbox} | Approval={args.approval}")
    if h == "H2" and n == "N1":
        print("Note: Configure K8s allowDomains in your Helm values for N1.")
    if h == "H1" and n in {"N1", "N2"}:
        print("Note: N1/N2 under Docker require egress controls (proxy/firewall); prefer K8s for N1/N2.")

    eval_tasks(task, log_dir=args.log_dir, log_realtime=True, log_samples=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
