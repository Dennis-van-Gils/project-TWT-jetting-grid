#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example code block

# DEBUG info: Report on memory allocation?
REPORT_MALLOC = False
if REPORT_MALLOC:
    import tracemalloc
    from utils_tracemalloc import tracemalloc_report

    tracemalloc.start()

if REPORT_MALLOC:
    tracemalloc_report(tracemalloc.take_snapshot(), limit=4)
"""

import os
import linecache
import tracemalloc


def tracemalloc_report(snapshot, key_type="lineno", limit=10):
    # Based on:
    # https://python.readthedocs.io/en/stable/library/tracemalloc.html#pretty-top
    snapshot = snapshot.filter_traces(
        (
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<unknown>"),
        )
    )
    top_stats = snapshot.statistics(key_type)

    print("\nTracemalloc top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        print(
            "#%s: %s:%s: %.1f MiB"
            % (index, filename, frame.lineno, stat.size / 1024 / 1024)
        )
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print("    %s\n" % line)
        else:
            print("")

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("%s other: %.1f MiB" % (len(other), size / 1024 / 1024))
    total = sum(stat.size for stat in top_stats)
    print("Total allocated size: %.1f MiB" % (total / 1024 / 1024))
