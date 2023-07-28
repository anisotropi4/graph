#!/usr/bin/env python3

"""
The junction.py script simplifies a networks by disaggregating an edge-network
and reassembling the simplified network by combining simply-connected nodes
"""

import argparse
import datetime as dt
import sys

import pandas as pd

START_TIME = dt.datetime.now()


def log(string_str, quiet, time_output=True):
    if not quiet:
        if time_output:
            now = (dt.datetime.now() - START_TIME).total_seconds()
            sys.stderr.write(f"{string_str}\t{now: > 8.3f}\n")

        else:
            sys.stderr.write(f"{string_str}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Input an edge file and output the corresponding .jsonl format simplified network. By default outputs to stdout and timing information to stderr"
    )

    parser.add_argument(
        "--tsv",
        dest="tsv",
        action="store_true",
        default=False,
        help="process tsv format file",
    )

    parser.add_argument(
        "--dump",
        dest="dump",
        action="store_true",
        default=False,
        help="dump edge file with edge IDs",
    )

    parser.add_argument(
        "--quiet",
        dest="quiet",
        action="store_true",
        default=False,
        help="suppress timing",
    )

    parser.add_argument("inputfile", type=str, help="name of edge-file to process")

    parser.add_argument(
        "outputfile",
        type=str,
        default=None,
        nargs="?",
        help="name of simplified edge-file to output, default stdout",
    )

    args = parser.parse_args()
    log("Loading edges", args.quiet, False)

    this_filelist = args.inputfile.split(".")
    this_filename = ".".join(this_filelist[:-1])
    this_extension = this_filelist[-1]

    if args.tsv or this_extension.lower() == "tsv":
        edges = pd.read_csv(args.inputfile, delimiter="\t")
    else:
        edges = pd.read_json(args.inputfile, lines=True)

    edges = edges.rename(
        columns={"_key": "edge", "edgeid": "edge", "from": "source", "to": "target"}
    )
    edges["index"] = edges["edge"]
    edges = edges.set_index("index")

    if not edges.index.is_unique:
        raise ValueError(
            f"Duplicate edge IDs\n{edges[edges.index.duplicated(False)]}"
        )

    log(f"Loaded\t\t{len(edges.index):> 8} edges\t", args.quiet)

    log("Creating segments", args.quiet, False)
    log("Adding missing edges", args.quiet, False)
    parallel_edges = edges[["source", "target"]].reset_index()
    parallel_edges = (
        parallel_edges.merge(
            parallel_edges[["source", "target"]],
            how="left",
            left_on="source",
            right_on="target",
            suffixes=("", "_A"),
        )
        .drop(columns="target_A")
        .dropna()
        .drop_duplicates()
    )
    parallel_edges = (
        parallel_edges.merge(
            parallel_edges[["source", "target"]],
            how="left",
            left_on="target",
            right_on="source",
            suffixes=("", "_B"),
        )
        .drop(columns="source_B")
        .dropna()
        .drop_duplicates()
    )
    parallel_edges = parallel_edges.query(
        "source == target_B or target == source_A"
    ).set_index("index")

    missing_index = edges.index.difference(parallel_edges.index)

    log(f"Added\t\t{len(missing_index):>8} edges\t", args.quiet)
    segments = pd.concat(
        [
            edges,
            edges.loc[missing_index].rename(
                columns={"source": "target", "target": "source"}
            ),
        ],
        sort=False,
    ).reset_index()
    segments["colour"] = pd.Series(segments.index).apply(
        lambda x: f"C{str(x).zfill(5)}"
    )
    segments["segment"] = segments["colour"]

    log("Counting duplicates", args.quiet, False)
    duplicate_segments = segments[
        segments.duplicated(["source", "target"], keep=False)
    ].sort_values(["source", "target"])
    duplicate_segments = duplicate_segments[
        ["edge", "source", "length", "target", "wayid"]
    ]

    log("Dumping duplicate segments", args.quiet, False)
    if len(duplicate_segments) > 0:
        pd.DataFrame(duplicate_segments).to_json(
            f"{this_filename}-duplicates.jsonl", orient="records", lines=True
        )

    log(
        f"Dumped duplicate{len(duplicate_segments.index):> 8} segments",
        args.quiet,
    )

    log("Dropping duplicate segments", args.quiet, False)
    segments = segments.drop_duplicates(["source", "target"])
    log(f"Created\t\t{len(segments.index):> 8} segments", args.quiet)

    log("Counting nodes", args.quiet, False)
    node_count = (
        segments["source"]
        .to_frame(name="node")
        .reset_index()
        .rename(columns={"index": "edge"})
        .groupby("node")
        .edge.nunique()
        .to_frame(name="n")
    )
    log(f"Counted\t\t{len(node_count.index):> 8} nodes\t", args.quiet)

    log("Creating links", args.quiet, False)

    df0 = segments[["source", "target"]]
    df0 = df0.join(node_count["n"], on="source").rename(columns={"n": "m"})
    df0 = df0.join(node_count["n"], on="target")

    df1 = (
        df0.reset_index()
        .set_index("source")
        .query("m < 3")
        .rename(columns={"index": "target_ix"})
        .drop(columns=["m", "n"])
    )
    df2 = df0.reset_index().set_index("target").rename(columns={"index": "source_ix"})

    links = df2.join(df1).query("source != target").dropna().astype({"target_ix": int})
    links = links.reindex(links.index.rename("node")).reset_index()
    links.index = links["source_ix"]
    links["count"] = 0

    log(f"Created\t\t{len(links.index):> 8} links\t", args.quiet)
    log("Processing segments", args.quiet, False)
    links["active"] = (links["n"] == 2) & (links["m"] != 2)

    count = 0
    while links["active"].any():
        for this_id in links.query("active").index:
            if count % 1024 == 0:
                log(
                    "Active\t\t{len(links.query('active').index):> 8} segments",
                    args.quiet,
                )
            links.at[this_id, "active"] = False
            next_id = links.at[this_id, "target_ix"]
            links.at[this_id, "count"] += 1
            while True:
                segments.at[next_id, "segment"] = segments.at[this_id, "segment"]
                this_id = next_id

                if this_id not in links.index:
                    break
                next_id = links.at[this_id, "target_ix"]
                links.at[this_id, "count"] += 1
            count += 1
    log(
        f"Active\t\t{len(links.query('active').index):> 8} segments", args.quiet
    )

    links["loop"] = (links["n"] == 2) & (links["m"] == 2) & (links["count"] == 0)
    links["active"] = links["loop"]
    log(f"Processed\t{len(segments.index):> 8} segments", args.quiet)

    log("Processing loops", args.quiet, False)
    count = 0
    for start_id in links.query("active").index:
        if count % 1024 == 0:
            log(
                f"Active\t\t{len(links.query('active').index):> 8} loops\t",
                args.quiet,
            )
        this_id = start_id
        for _ in range(0, 3):
            links.at[this_id, "count"] += 1
            links.at[this_id, "active"] = False
            next_id = links.at[this_id, "target_ix"]
            segments.at[next_id, "segment"] = segments.at[this_id, "segment"]
            this_id = next_id
        count += 1

    log(f"Active\t\t{len(links.query('active').index):> 8} loops\t", args.quiet)
    log(f"Processed\t{len(links.query('loop').index):> 8} loops\t", args.quiet)

    if args.dump:
        log("Dumping segments", False)
        pd.DataFrame(segments).T.to_json(this_filename + "-dump.jsonl")
        log(f"Dumped\t\t{len(segments.index):> 8} segments", args.quiet)

    log("Outputing segments", args.quiet, False)

    output_segments = segments.query("colour == segment")[
        ["source", "target", "segment"]
    ]
    output_segments["nodes"] = output_segments.apply(lambda x: [], axis=1)
    output_segments["wayids"] = output_segments.apply(lambda x: [], axis=1)
    output_segments["length"] = -0.0

    count = 0
    for start_id in segments.query("colour == segment").index:
        if count % 8192 == 0:
            log(f"Output\t\t{count:> 8} segments", args.quiet)

        start_node = segments.at[start_id, "source"]
        end_node = segments.at[start_id, "target"]
        these_nodes = [start_node, end_node]
        length = segments.at[start_id, "length"]
        these_edges = [segments.at[start_id, "edge"]]
        this_wayid = segments.at[start_id, "wayid"]
        wayids = [this_wayid]
        this_id = start_id
        while this_id in links.index:
            this_id = links.at[this_id, "target_ix"]
            if (
                links.at[start_id, "loop"]
                and start_id == links.at[this_id, "target_ix"]
            ):
                break
            this_node = segments.at[this_id, "target"]
            if this_node == start_node:
                break
            these_nodes.append(this_node)
            these_edges.append(segments.at[this_id, "edge"])
            if this_wayid != segments.at[this_id, "wayid"]:
                this_wayid = segments.at[this_id, "wayid"]
                wayids.append(this_wayid)
            end_node = this_node
            length += segments.at[this_id, "length"]

        output_segments.at[start_id, "target"] = end_node
        output_segments.at[start_id, "length"] = length
        output_segments.at[start_id, "wayids"] = wayids
        output_segments.at[start_id, "nodes"] = these_nodes
        count += 1

    log(f"Output\t\t{len(output_segments):> 8} segments", args.quiet)
    log("Writing segments", args.quiet, False)

    if args.outputfile:
        output_segments.to_json(args.outputfile, orient="records", lines=True)
    else:
        output_segments.to_json(sys.stdout, orient="records", lines=True)

    log(f"Written\t\t{len(output_segments):> 8} segments", args.quiet)


if __name__ == "__main__":
    main()
