"""Actual scoped profiler crash regression; never native engineering readiness."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from perf_bridge import digest

SOURCE = r"""
#include <signal.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <time.h>
int main(int argc, char **argv) {
    struct rlimit core = {0, 0}; setrlimit(RLIMIT_CORE, &core);
    struct timespec start, now; clock_gettime(CLOCK_MONOTONIC, &start);
    volatile unsigned long value = 1;
    do { for (int i=0; i<100000; ++i) value = value*1664525+1013904223;
         clock_gettime(CLOCK_MONOTONIC, &now);
    } while (now.tv_sec-start.tv_sec < 3);
    if (argc>1 && atoi(argv[1])) raise(atoi(argv[1]));
    return value == 0;
}
"""


def main(root: Path) -> int:
    scratch = root / "profiler-signal-regression"
    scratch.mkdir(exist_ok=True)
    source, binary = scratch / "workload.c", scratch / "workload"
    source.write_text(SOURCE)
    subprocess.run(["/usr/bin/gcc", "-O1", str(source), "-o", str(binary)], check=True)
    records = []
    for sig, expected in ((11, 139), (0, 0)):
        data = scratch / ("workload-" + str(sig) + ".data")
        measured = subprocess.run(
            [
                str(root / "perf-bin/perf"),
                "record",
                "-F",
                "99",
                "-g",
                "-o",
                str(data),
                "--",
                str(binary),
                str(sig),
            ],
            capture_output=True,
            text=True,
            timeout=40,
            check=False,
        )
        (scratch / (str(sig) + ".stdout")).write_text(measured.stdout)
        (scratch / (str(sig) + ".stderr")).write_text(measured.stderr)
        receipt = json.loads(Path(str(data) + ".receipt.json").read_text())
        decoded = subprocess.run(
            [str(root / "perf-bin/perf"), "script", "-i", str(data)],
            capture_output=True,
            text=True,
            timeout=40,
            check=False,
        )
        record = {
            "signal": sig,
            "expected_wrapper_exit": expected,
            "actual_wrapper_exit": measured.returncode,
            "recording": receipt,
            "decode_exit": decoded.returncode,
            "decoded_bytes": len(decoded.stdout),
        }
        record["passed"] = (
            measured.returncode == expected
            and receipt["perf_exit_code"] == 0
            and data.read_bytes()[:8] == b"PERFILE2"
            and (
                decoded.returncode != 0 if sig else decoded.returncode == 0 and bool(decoded.stdout)
            )
        )
        records.append(record)
    result = {
        "scope": "Actual tool qualification regression, separate from native test evidence",
        "workload_source_sha256": digest(source),
        "workload_binary_sha256": digest(binary),
        "cases": records,
        "passed": all(r["passed"] for r in records),
    }
    (scratch / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]).resolve(strict=True)))
