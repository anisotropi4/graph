#!/bin/bash

if [ ! -d venv ]; then
    echo Set up python3 virtual environment
    python3 -m venv venv
    source venv/bin/activate
    pip3 install --upgrade pip
    pip3 install -r requirements.txt
else
    source venv/bin/activate
fi

./junction.py --tsv testedges.tsv testsegments-file.jsonl

if [ ! -d images ]; then
    mkdir images
fi

./plot-graph.py --tsv testedges.tsv
./plot-graph.py --json testsegments-file.jsonl

./plot-graph.py --tsv example-edges.tsv
./plot-graph.py --json example-segments.jsonl

