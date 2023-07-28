#!/bin/sh

./junction.py --tsv testedges.tsv testsegments-file.jsonl

if [ ! -d images ]; then
    mkdir images
fi

./plot-graph.py --tsv testedges.tsv
./plot-graph.py --json testsegments-file.jsonl

./plot-graph.py --tsv example-edges.tsv
./plot-graph.py --json example-segments.jsonl

