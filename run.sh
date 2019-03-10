#!/bin/sh

./junction.py --tsv testedges.tsv testsegments-file.ndjson

if [ ! -f images ]; then
  mkdir images
fi

./networkx/plot-graph.py --tsv testedges.tsv
./networkx/plot-graph.py --json testsegments-file.ndjson

./networkx/plot-graph.py --tsv example-edges.tsv
./networkx/plot-graph.py --json example-segments.ndjson

