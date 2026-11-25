import argparse
import csv
import json
from pathlib import Path
import re
import statistics
import subprocess
import threading
import time


def write_csv(path, rows, columns=None):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def collect(args):
    adb = [args.adb, "-s", args.serial]

    def shell(*command):
        return subprocess.check_output([*adb, "shell", *command], text=True, encoding="utf-8", errors="replace", timeout=12)

    if subprocess.check_output([*adb, "get-state"], text=True).strip() != "device":
        raise SystemExit("ADB device is unavailable or unauthorized")
    if args.serial.startswith('emulator-') or shell('getprop', 'ro.kernel.qemu').strip() == '1':
        raise SystemExit('This collection is reserved for Android physical devices')
    args.out.mkdir(parents=True, exist_ok=False)
    metadata = {
        "scenario": args.scenario, "repetition": args.rep, "expectedPhotos": args.photos,
        "seededPhotos": args.seeded, "addedPhotos": args.added,
        "package": args.package, "serial": args.serial, "commit": args.commit, "apkSha256": args.apk_sha256,
        "model": shell("getprop", "ro.product.model").strip(),
        "android": shell("getprop", "ro.build.version.release").strip(),
        "sdk": shell("getprop", "ro.build.version.sdk").strip(),
    }
    (args.out / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    with (args.out / "device.txt").open("w", encoding="utf-8") as output:
        output.write(shell("df", "/data"))
        package = shell("dumpsys", "package", args.package)
        output.write("\n".join(line for line in package.splitlines() if
                               re.search(r"versionName=|versionCode=|READ_MEDIA_|READ_EXTERNAL_STORAGE", line)))
    stop = threading.Event()

    def memory():
        with (args.out / "memory.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["hostMs", "pssKiB"])
            while not stop.wait(1):
                try:
                    sample = shell("dumpsys", "meminfo", args.package)
                    pss = re.search(r"TOTAL PSS:\s*(\d+)", sample) or re.search(r"^\s*TOTAL\s+(\d+)", sample,re.M)
                    if pss:
                        writer.writerow([int(time.time()*1000), int(pss.group(1))])
                        stream.flush()
                except (subprocess.SubprocessError, OSError):
                    continue

    thread = threading.Thread(target=memory, daemon=True)
    logs = subprocess.Popen([*adb, "logcat", "-T", "1", "-v", "raw", "ReactNativeJS:I", "*:S"],
                            text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE)
    thread.start()
    print("Capture active. Open photo search and run the scenario. Ctrl+C after the last query.", flush=True)
    try:
        with (args.out / "events.jsonl").open("w", encoding="utf-8") as output:
            for line in logs.stdout:
                if "ONDEV_BENCH " not in line:
                    continue
                event = json.loads(line.split("ONDEV_BENCH ",1)[1])
                event["hostMs"] = int(time.time()*1000)
                output.write(json.dumps(event, ensure_ascii=False)+"\n")
                output.flush()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        logs.terminate()
        logs.wait(timeout=10)
        thread.join(timeout=13)


def summarize(root, labels=None):
    rows, queries = [], []
    for path in sorted(root.glob("*/events.jsonl")):
        meta = json.loads((path.parent/"metadata.json").read_text(encoding="utf-8"))
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        with (path.parent/"memory.csv").open(encoding="utf-8") as stream:
            memory = list(csv.DictReader(stream))
        for start in (event for event in events if event["kind"]=="index-start"):
            sequence = [e for e in events if e.get("runId")==start["runId"]]
            by_kind = {event["kind"]:event for event in sequence}
            index = by_kind.get("index", {})
            ready = by_kind.get("ready-frame")
            mounted = next((e for e in reversed(events) if
                            e["kind"]=="screen-mounted" and e["atMs"]<=start["atMs"]),None)
            samples = [int(m["pssKiB"]) for m in memory if
                       ready and start["hostMs"]<=int(m["hostMs"])<=ready["hostMs"]]
            counts_ok = (index.get("indexed") == meta["expectedPhotos"] and
                         index.get("fixtureCandidates") == meta["expectedPhotos"] and
                         index.get("fresh",0) + index.get("reused",0) == index.get("indexed"))
            fresh, reused = index.get("fresh"), index.get("reused")
            pattern_ok = None
            if ready and counts_ok:
                if meta["scenario"] == "A":
                    pattern_ok = index.get("cacheEntriesBefore") == 0 and fresh == meta["expectedPhotos"] and reused == 0
                elif meta["scenario"] == "B":
                    pattern_ok = fresh == 0 and reused == meta["expectedPhotos"]
                elif meta["scenario"] == "C":
                    pattern_ok = (fresh == index.get("fixtureAdded") == meta.get("addedPhotos")
                                  and index.get("freshAdded") == fresh
                                  and reused == meta["expectedPhotos"] - fresh)
            rows.append({
                **{key: value for key, value in meta.items() if key != 'serial'},
                "runId":start["runId"], "modelVersion":start["modelVersion"],
                "indexStartToReadyMs":ready["atMs"]-start["atMs"] if ready else None,
                "screenToReadyMs":ready["atMs"]-mounted["atMs"] if ready and mounted else None,
                "sampledPeakPssKiB":max(samples) if samples else None, "pssSamples":len(samples),
                **{k:index.get(k) for k in ("candidates","indexed","fresh","reused","failed","cacheEntriesBefore",
                                            "cacheReadMs","cacheWriteMs","imageWallMs","imageReportedMs","preprocessMs",
                                            "inferenceMs","freshAdded","reusedAdded","fixtureCandidates","fixtureAdded")},
                **{k:by_kind.get("gallery-list",{}).get(k) for k in ("limited","modelWaitMs","galleryReadMs","ranges")},
                "tileCount":ready.get("tileCount") if ready else None,
                "groupMs":ready.get("groupMs") if ready else None,
                "modelDownloadMs":by_kind.get("model-download",{}).get("ms"),
                "expectedCachePattern":pattern_ok,
                "measurementComplete":bool(ready and counts_ok and not start["download"]
                                           and index.get("failed") == 0 and not index.get("cancelled")),
            })
            for query in (e for e in sequence if e["kind"]=="query-frame"):
                stages = next((e for e in sequence if e["kind"]=="query-inferred" and e["queryId"]==query["queryId"]),{})
                queries.append({
                    **{k:meta[k] for k in ("scenario","repetition","expectedPhotos")},
                    "runId":start["runId"],"queryId":query["queryId"],"inputToFrameMs":query["inputToFrameMs"],
                    "debounceMs":stages.get("debounceMs"),"inferenceMs":stages.get("inferenceMs"),
                    "rankMs":query["rankMs"],"resultCount":query["resultCount"],
                    "ranks":json.dumps(query["results"],ensure_ascii=False),
                })
    if rows:
        write_csv(root/"index-runs.csv",rows)
    if queries:
        write_csv(root/"query-ranks.csv",queries)
    aggregates = []
    cohorts = {}
    for row in rows:
        if row["measurementComplete"]:
            key = tuple(row[k] for k in ("scenario","expectedPhotos","model","android","commit","apkSha256","modelVersion"))
            cohorts.setdefault(key,[]).append(row)
    for key, runs in cohorts.items():
        group = dict(zip(("scenario","expectedPhotos","model","android","commit","apkSha256","modelVersion"),key))
        group["repetitions"] = len(runs)
        for field in ("screenToReadyMs","indexStartToReadyMs","sampledPeakPssKiB"):
            values = [r[field] for r in runs if r[field] is not None]
            group[field+"Median"] = statistics.median(values) if values else None
            group[field+"Min"] = min(values) if values else None
            group[field+"Max"] = max(values) if values else None
        aggregates.append(group)
    if aggregates:
        write_csv(root/"index-summary.csv",aggregates)
    if labels:
        compare_ranks(root, labels, queries)
    print(f"Index records: {len(rows)}, query records: {len(queries)}")


def compare_ranks(root, labels, queries):
    by_id = {(str(q["runId"]), str(q["queryId"])): q for q in queries}
    labeled = {}
    with labels.open(encoding="utf-8-sig", newline="") as stream:
        for label in csv.DictReader(stream):
            record = by_id.get((label["runId"], label["queryId"]))
            if record is None or record["scenario"] != label["scenario"]:
                raise ValueError("Label does not match a captured query")
            key = (label["repetition"], label["seededPhotos"], label["queryLabel"], label["expectedFixture"])
            arms = labeled.setdefault(key,{})
            if label["scenario"] in arms:
                raise ValueError("Duplicate label for a scenario")
            arms[label["scenario"]] = record
    pairs = []
    for (rep,photos,query,expected), arms in labeled.items():
        if "A" not in arms or "B" not in arms:
            continue
        before,after = (json.loads(arms[arm]["ranks"]) for arm in ("A","B"))
        a,b = ([item[1] for item in rank] for rank in (before,after))
        matched_a = len(a) == arms["A"]["resultCount"]
        matched_b = len(b) == arms["B"]["resultCount"]
        pairs.append(dict(repetition=rep,seededPhotos=photos,query=query,expectedFixture=expected,
                          rankA=next((item[0] for item in before if item[1]==expected),None),
                          rankB=next((item[0] for item in after if item[1]==expected),None),
                          sameOrder=(a==b) if matched_a and matched_b else None,
                          sameSet=(set(a)==set(b)) if matched_a and matched_b else None))
    if pairs:
        write_csv(root/"rank-comparison.csv",pairs)


parser=argparse.ArgumentParser()
commands=parser.add_subparsers(dest="cmd",required=True)
capture=commands.add_parser("collect")
capture.add_argument("--adb",default="adb")
capture.add_argument("--serial",required=True)
capture.add_argument("--package",required=True)
capture.add_argument("--commit",required=True)
capture.add_argument("--apk-sha256",required=True)
capture.add_argument("--scenario",choices=["A","B","C","offline"],required=True)
capture.add_argument("--rep",type=int,required=True)
capture.add_argument("--photos",type=int,required=True)
capture.add_argument("--seeded",type=int,required=True)
capture.add_argument("--added",type=int,default=0)
capture.add_argument("--out",type=Path,required=True)
summary=commands.add_parser("summarize")
summary.add_argument("root",type=Path)
summary.add_argument("--labels",type=Path)
if __name__=="__main__":
    args=parser.parse_args()
    collect(args) if args.cmd=="collect" else summarize(args.root,args.labels)
