# Transport Network Simplification through Network Disaggregation and Reassembly of OpenStreet Map (OSM) networks

## Overview

Geographic representations of networks, such as transport networks, typically consist of end-point, junctions and simply-connected nodes. Where a simply-connected node is a node which is only connected to two other nodes. Typically OSM networks consist of a large number of simply-connected nodes with a smaller number of end-point or simply-connected nodes. 

This approach looks to disaggregate, or break up, of OSM transport-network data into its consitutent edges and reassembly of a simplified network through the removal of duplicate or parallel edges, and combining simply-connected nodes. For example, based on analysis of a OSM British rail-network data shows 497 359 nodes with 506 337 edges 1 012 604 segments 925 172 (91.4%) are simply-connected.

More details about the implementation is given [here](graph.md)

## Pre-requisites

To extract and process the data is dependant on the following tools:

  - [python3](https://python.org) 
  - [pandas](http://pandas.pydata.org/), [numpy](https://www.numpy.org/) and [networkx](https://networkx.github.io) python3 packages
  
#### For ease of python dependency management a local python3 [miniconda](https://conda.io/miniconda.html) or [anaconda](https://www.anaconda.com/distribution/) installation is recomended

## Running simplification against example data

   Executing the `run.sh` script runs the simplication and visualisation of the `testedges.tsv` data-set, creating simplified network and visualises this using the `networkx` module

### Example simplification of data
   
   Running the `junction.py` script to converts the examples in the `testedges.tsv` into the simplified `testsegments-files.ndjson` data as follows:
   
```
   $ ./junction.py --tsv testedges.tsv testsegments-file.ndjson
```

### Example data and the simplified visualisation 

   Running the `plot-graph.py` script as follows creates `.svg` visualisations of the test and simplified networks in the images directory `graph.html` 

```
   $ ./networkx/plot-graph.py --tsv testedges.tsv
   $ ./networkx/plot-graph.py --json testsegments-file.ndjson
```

### Miscellaneous example visualisation

   Additional graphs used in the `graphs.html` are then generated as:
```
    $ ./networkx/plot-graph.py --tsv example-edges.tsv
    $ ./networkx/plot-graph.py --json example-segments.ndjson
```
## Documentation

   The `graph.html` (and `graph.md`) is generated from the `graph.yaml` file using the `output-html.py` script from the [goldfinch/markdown](https://github.com/anisotropi4/goldfinch/tree/master/markdown)
