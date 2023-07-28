#!/usr/bin/env python3

"""
The junction.py script simplifies a networks by disaggregating an edge-network 
and reassembling the simplified network by combining simply-connected nodes
"""

import sys
import pandas as pd
import numpy as np
import datetime
import argparse

parser = argparse.ArgumentParser(description='Input an edge file and output the corresponding .jsonl format simplified network. By default outputs to stdout and timing information to stderr')

parser.add_argument('--tsv', dest='tsv', action='store_true',
                    default=False, help='process tsv format file')

parser.add_argument('--dump', dest='dump', action='store_true',
                    default=False, help='dump edge file with edge IDs')

parser.add_argument('--quiet', dest='quiet', action='store_true',
                    default=False, help='suppress timing ')

parser.add_argument('inputfile', type=str, help='name of edge-file to process')

parser.add_argument('outputfile', type=str, default=None, nargs='?', help='name of simplified edge-file to output, default stdout')

args = parser.parse_args()

def time_offset(string_str, time_output=True):
    if not args.quiet:
        if time_output:
            sys.stderr.write('{}\t{: > 8.3f}\n'.format(string_str, (datetime.datetime.now() - start_time).total_seconds()))
        else:
            sys.stderr.write('{}\n'.format(string_str))

start_time = datetime.datetime.now()
time_offset('Loading edges', False)

this_filelist = args.inputfile.split('.')
this_filename = '.'.join(this_filelist[:-1])
this_extension = this_filelist[-1]

if args.tsv or this_extension.lower() == 'tsv':
    edges = pd.read_csv(args.inputfile, delimiter='\t')
else:
    pd.read_json(args.inputfile, lines=True)

edges = edges.rename(columns={'_key': 'edge', 'edgeid': 'edge', 'from': 'source', 'to': 'target'})
edges['index'] = edges['edge']
edges = edges.set_index('index')

if not edges.index.is_unique:
    raise ValueError('Duplicate edge IDs\n{}'.format(edges[edges.index.duplicated(False)]))

time_offset('Loaded\t\t{:> 8} edges\t'.format(len(edges.index)))

time_offset('Creating segments', False)
time_offset('Adding missing edges', False)
parallel_edges = edges[['source','target']].reset_index()
parallel_edges = parallel_edges.merge(parallel_edges[['source', 'target']], how='left', left_on='source', right_on='target', suffixes=('', '_A')).drop(columns='target_A').dropna().drop_duplicates()
parallel_edges = parallel_edges.merge(parallel_edges[['source', 'target']], how='left', left_on='target', right_on='source', suffixes=('', '_B')).drop(columns='source_B').dropna().drop_duplicates()
parallel_edges = parallel_edges.query('source == target_B or target == source_A').set_index('index')

missing_index = edges.index.difference(parallel_edges.index)

time_offset('Added\t\t{:>8} edges\t'.format(len(missing_index)))
segments = pd.concat([edges, edges.loc[missing_index].rename(columns={'source': 'target', 'target': 'source'})], sort=False).reset_index()
segments['colour'] = pd.Series(segments.index).apply(lambda x: 'C{}'.format(str(x).zfill(5)))
segments['segment'] = segments['colour']

time_offset('Counting duplicates', False)
duplicate_segments = segments[segments.duplicated(['source', 'target'], keep=False)].sort_values(['source', 'target'])
duplicate_segments = duplicate_segments[['edge', 'source', 'length', 'target', 'wayid']]

time_offset('Dumping duplicate segments', False)
if len(duplicate_segments) > 0:
    pd.DataFrame(duplicate_segments).to_json(this_filename + '-duplicates.jsonl', orient='records', lines=True)

time_offset('Dumped duplicate{:> 8} segments'.format(len(duplicate_segments.index)))

time_offset('Dropping duplicate segments', False)
segments = segments.drop_duplicates(['source', 'target'])
time_offset('Created\t\t{:> 8} segments'.format(len(segments.index)))

time_offset('Counting nodes', False)
node_count = segments['source'].to_frame(name='node').reset_index().rename(columns={'index': 'edge'}).groupby('node').edge.nunique().to_frame(name='n')
time_offset('Counted\t\t{:> 8} nodes\t'.format(len(node_count.index)))

time_offset('Creating links', False)

df0 = segments[['source', 'target']]
df0 = df0.join(node_count['n'], on='source').rename(columns={'n': 'm'})
df0 = df0.join(node_count['n'], on='target')

df1 = df0.reset_index().set_index('source').query('m < 3').rename(columns={'index': 'target_ix'}).drop(columns=['m', 'n'])
df2 = df0.reset_index().set_index('target').rename(columns={'index': 'source_ix'})

links = df2.join(df1).query('source != target').dropna().astype({'target_ix': int})
links = links.reindex(links.index.rename('node')).reset_index()
links.index = links['source_ix']
links['count'] = 0

time_offset('Created\t\t{:> 8} links\t'.format(len(links.index)))
time_offset('Processing segments', False)
links['active'] = ((links['n'] == 2) & (links['m'] != 2)) 

count = 0
while links['active'].any():    
    for this_id in links.query('active').index:
        if count % 1024 == 0:
            time_offset('Active\t\t{:> 8} segments'.format(len(links.query('active').index)))
        links.at[this_id, 'active'] = False
        next_id = links.at[this_id, 'target_ix']
        links.at[this_id, 'count'] += 1
        while True:
            segments.at[next_id, 'segment'] = segments.at[this_id, 'segment']
            this_id = next_id

            if this_id not in links.index:
                break
            next_id = links.at[this_id, 'target_ix']
            links.at[this_id, 'count'] += 1
        count += 1
time_offset('Active\t\t{:> 8} segments'.format(len(links.query('active').index)))

links['loop'] = ((links['n'] == 2) & (links['m'] == 2) & (links['count'] == 0))
links['active'] = links['loop']
time_offset('Processed\t{:> 8} segments'.format(len(segments.index)))

time_offset('Processing loops', False)
count = 0
for start_id in links.query('active').index:
    if count % 1024 == 0:
        time_offset('Active\t\t{:> 8} loops\t'.format(len(links.query('active').index)))
    this_id = start_id
    for i in range(0, 3):
        links.at[this_id, 'count'] += 1
        links.at[this_id, 'active'] = False
        next_id = links.at[this_id, 'target_ix']
        segments.at[next_id, 'segment'] = segments.at[this_id, 'segment']
        this_id = next_id
    count += 1

time_offset('Active\t\t{:> 8} loops\t'.format(len(links.query('active').index)))
time_offset('Processed\t{:> 8} loops\t'.format(len(links.query('loop').index)))

if args.dump:
    time_offset('Dumping segments', False)
    pd.DataFrame(segments).T.to_json(this_filename + '-dump.jsonl')
    time_offset('Dumped\t\t{:> 8} segments'.format(len(segments.index)))

time_offset('Outputing segments', False)

output_segments = segments.query('colour == segment')[['source', 'target', 'segment']]
output_segments['nodes'] = output_segments.apply(lambda x: list(), axis=1)
output_segments['wayids'] = output_segments.apply(lambda x: list(), axis=1)
output_segments['length'] = -0.0

count = 0
for start_id in segments.query('colour == segment').index:
    if count % 8192 == 0:
        time_offset('Output\t\t{:> 8} segments'.format(count))

    start_node = segments.at[start_id, 'source']
    end_node = segments.at[start_id, 'target']
    these_nodes = [start_node, end_node]
    length = segments.at[start_id, 'length']
    these_edges = [segments.at[start_id, 'edge']]
    this_wayid = segments.at[start_id, 'wayid']
    wayids = [this_wayid]
    this_id = start_id
    this_segment = segments.at[start_id, 'segment']
    while this_id in links.index:
        this_id = links.at[this_id, 'target_ix']
        if links.at[start_id, 'loop'] and start_id == links.at[this_id, 'target_ix']:
            break
        this_node = segments.at[this_id, 'target']
        if this_node == start_node:
            break
        these_nodes.append(this_node)
        these_edges.append(segments.at[this_id, 'edge'])
        if this_wayid != segments.at[this_id, 'wayid']:
            this_wayid = segments.at[this_id, 'wayid']
            wayids.append(this_wayid)
        end_node = this_node
        length += segments.at[this_id, 'length']

    output_segments.at[start_id, 'target'] = end_node
    output_segments.at[start_id, 'length'] = length
    output_segments.at[start_id, 'wayids'] = wayids
    output_segments.at[start_id, 'nodes'] = these_nodes
    count += 1

time_offset('Output\t\t{:> 8} segments'.format(len(output_segments)))
time_offset('Writing segments', False)


if args.outputfile:
    output_segments.to_json(args.outputfile, orient='records', lines=True)
else:
    output_segments.to_json(sys.stdout, orient='records', lines=True)

time_offset('Written\t\t{:> 8} segments'.format(len(output_segments)))
