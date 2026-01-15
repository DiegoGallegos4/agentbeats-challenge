#!/usr/bin/env python
import argparse
import asyncio
import json
import os
import signal
import shlex
import subprocess
import sys
import time
from pathlib import Path
import tomllib

import httpx
from dotenv import load_dotenv

from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import Message as A2AMessage, Part, Role, TextPart, DataPart


load_dotenv(override=True)


async def wait_for_agents(cfg: dict, timeout: int = 30) -> bool:
    endpoints = []

    for p in cfg["participants"]:
        if p.get("cmd"):
            endpoints.append(f"http://{p['host']}:{p['port']}")

    if cfg["green_agent"].get("cmd"):
        endpoints.append(f"http://{cfg['green_agent']['host']}:{cfg['green_agent']['port']}")

    if not endpoints:
        return True

    print(f"Waiting for {len(endpoints)} agent(s) to be ready...")
    start_time = time.time()

    async def check_endpoint(endpoint: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                resolver = A2ACardResolver(httpx_client=client, base_url=endpoint)
                await resolver.get_agent_card()
                return True
        except Exception:
            return False

    while time.time() - start_time < timeout:
        ready_count = 0
        for endpoint in endpoints:
            if await check_endpoint(endpoint):
                ready_count += 1

        if ready_count == len(endpoints):
            return True

        print(f"  {ready_count}/{len(endpoints)} agents ready, waiting...")
        await asyncio.sleep(1)

    print(f"Timeout: Only {ready_count}/{len(endpoints)} agents became ready after {timeout}s")
    return False


def parse_toml(scenario_path: str) -> dict:
    path = Path(scenario_path)
    if not path.exists():
        print(f"Error: Scenario file not found: {path}")
        sys.exit(1)

    data = tomllib.loads(path.read_text())

    def host_port(ep: str):
        s = (ep or "")
        s = s.replace("http://", "").replace("https://", "")
        s = s.split("/", 1)[0]
        host, port = s.split(":", 1)
        return host, int(port)

    green_ep = data.get("green_agent", {}).get("endpoint", "")
    g_host, g_port = host_port(green_ep)
    green_cmd = data.get("green_agent", {}).get("cmd", "")

    parts = []
    for p in data.get("participants", []):
        if isinstance(p, dict) and "endpoint" in p:
            h, pt = host_port(p["endpoint"])
            parts.append({
                "role": str(p.get("role", "")),
                "host": h,
                "port": pt,
                "cmd": p.get("cmd", ""),
            })

    cfg = data.get("config", {})
    return {
        "green_agent": {"host": g_host, "port": g_port, "cmd": green_cmd},
        "participants": parts,
        "config": cfg,
    }


def build_request(cfg: dict) -> dict:
    return {
        "participants": {
            "agent": f"http://{cfg['participants'][0]['host']}:{cfg['participants'][0]['port']}"
            if cfg["participants"]
            else "",
        },
        "config": cfg.get("config", {}),
    }


def create_message(text: str, context_id: str | None = None) -> A2AMessage:
    return A2AMessage(
        kind="message",
        role=Role.user,
        parts=[Part(TextPart(kind="text", text=text))],
        message_id=os.urandom(8).hex(),
        context_id=context_id,
    )


def merge_parts(parts: list[Part]) -> str:
    chunks = []
    for part in parts:
        if isinstance(part.root, TextPart):
            chunks.append(part.root.text)
        elif isinstance(part.root, DataPart):
            chunks.append(json.dumps(part.root.data, indent=2))
    return "\n".join(chunks)


async def run_client(cfg: dict) -> int:
    endpoint = f"http://{cfg['green_agent']['host']}:{cfg['green_agent']['port']}"
    payload = build_request(cfg)
    text = json.dumps(payload)
    try:
        async with httpx.AsyncClient(timeout=60) as httpx_client:
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url=endpoint)
            agent_card = await resolver.get_agent_card()
            client = ClientFactory(ClientConfig(httpx_client=httpx_client)).create(agent_card)
            outbound = create_message(text)

            last_event = None
            async for event in client.send_message(outbound):
                last_event = event

        if last_event is None:
            print("No response received from green agent.")
            return 1

        if isinstance(last_event, A2AMessage):
            print(merge_parts(last_event.parts))
            return 0

        task, update = last_event
        msg = task.status.message
        if msg:
            print(merge_parts(msg.parts))
        if task.artifacts:
            for artifact in task.artifacts:
                print(merge_parts(artifact.parts))
        return 0
    except Exception as exc:
        print(f"Error running scenario: {exc}")
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run agent scenario")
    parser.add_argument("scenario", help="Path to scenario TOML file")
    parser.add_argument("--show-logs", action="store_true", help="Show agent stdout/stderr")
    parser.add_argument("--serve-only", action="store_true", help="Start agent servers only")
    args = parser.parse_args()

    cfg = parse_toml(args.scenario)

    sink = None if args.show_logs or args.serve_only else subprocess.DEVNULL
    parent_bin = str(Path(sys.executable).parent)
    base_env = os.environ.copy()
    base_env["PATH"] = parent_bin + os.pathsep + base_env.get("PATH", "")

    procs = []
    try:
        for p in cfg["participants"]:
            cmd_args = shlex.split(p.get("cmd", ""))
            if cmd_args:
                print(f"Starting {p['role']} at {p['host']}:{p['port']}")
                procs.append(subprocess.Popen(
                    cmd_args,
                    env=base_env,
                    stdout=sink,
                    stderr=sink,
                    text=True,
                    start_new_session=True,
                ))

        green_cmd_args = shlex.split(cfg["green_agent"].get("cmd", ""))
        if green_cmd_args:
            print(f"Starting green agent at {cfg['green_agent']['host']}:{cfg['green_agent']['port']}")
            procs.append(subprocess.Popen(
                green_cmd_args,
                env=base_env,
                stdout=sink,
                stderr=sink,
                text=True,
                start_new_session=True,
            ))

        if not asyncio.run(wait_for_agents(cfg)):
            print("Error: Not all agents became ready. Exiting.")
            return

        print("Agents started. Press Ctrl+C to stop.")
        if args.serve_only:
            while True:
                for proc in procs:
                    if proc.poll() is not None:
                        print(f"Agent exited with code {proc.returncode}")
                        break
                time.sleep(0.5)
        else:
            sys.exit(asyncio.run(run_client(cfg)))

    except KeyboardInterrupt:
        pass
    finally:
        print("\nShutting down...")
        for p in procs:
            if p.poll() is None:
                try:
                    os.killpg(p.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        time.sleep(1)
        for p in procs:
            if p.poll() is None:
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


if __name__ == "__main__":
    main()
