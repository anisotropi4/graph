#!/usr/bin/env python3

import sys
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import argparse

wayid_list = {'Aggregate', 'Loop'}
nodesize=800

jsonfile = None
#tsvfile = None

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Input a tsv or json edge-file and output an .svg format visualisatoin of hte network to the images subdirectory')

    parser.add_argument('--tsv', dest='tsvfile', type=str, help='name of tsv-file to visualise')
    parser.add_argument('--json', dest='jsonfile', type=str, help='name of json-file to visualise')

    args = parser.parse_args()
    jsonfile = args.jsonfile
    tsvfile = args.tsvfile

def set_plt(G, scale=1, height=3):
    plt.figure(figsize=(3, height))
    ax = plt.gca()
    ax.set_axis_off()
    return nx.circular_layout(MDG, scale)

def draw_this(MDG, p, colour, node_list=None):
    nx.draw_networkx_nodes(MDG, p, nodelist=node_list, node_size=nodesize, node_color=colour, node_shape='h')
    nx.draw_networkx_labels(MDG, p, font_size=8, font_family='sans-serif', font_color='white')

def draw_arrows(MDG, p, edge_list=None, style='arc3,rad=0.1'):
    nx.draw_networkx_edges(MDG, p, edgelist=edge_list, width=1, node_size=nodesize, arrowsize=24, arrowstyle='simple', connectionstyle=style, zorder=3)

if jsonfile:
    edges = pd.read_json(jsonfile, lines=True)
    edges = edges.rename(columns={'_key': 'edge', 'from': 'source', 'to': 'target'})
    edges['wayid'] = edges['wayids'].apply(lambda x: x[0])

    df1 = edges[['source', 'target', 'segment']]
    df2 = df1.copy().rename(columns={'target': 'source', 'source': 'target'})
    df3 = df1.append(df2, sort=False).sort_values(['source','target']).reset_index(drop=True)
    l = df3.groupby('source').size().reset_index().set_index('source').to_dict()[0]

    for wayid in edges['wayid'].tolist():
        this_graph = [tuple(i) for i in edges[edges['wayid'] == wayid][['source', 'target']].values.tolist()]
        if not this_graph:
            continue

        green_nodes = {j for i in this_graph for j in i if l[j] > 1}
        red_nodes = {j for i in this_graph for j in i if l[j] == 1}

        MDG = nx.MultiDiGraph(this_graph)

        green_list = [(u, v) for (u, v, d) in MDG.edges(data=True) if l[u] > 1 and l[v] > 1]
        green_set = {j for i in green_list for j in i}

        red_list = [(u, v) for (u, v, d) in MDG.edges(data=True) if v not in green_set]
        red_set = {j for i in red_list for j in i}
        if len(green_set) + len(red_set) == 2:
            p = set_plt(MDG, height=1)
        else:
            p = set_plt(MDG)
        draw_this(MDG, p, 'red', red_nodes)
        draw_arrows(MDG, p, edge_list=red_list, style=None)
        draw_this(MDG, p, 'green', green_nodes)
        draw_arrows(MDG, p, edge_list=green_list)
        plt.savefig('images/{}FB.svg'.format(wayid), format='svg')
        plt.close()

        if len(green_set) + len(red_set) == 2:
            p = set_plt(MDG, height=1, scale=-1)
        else:
            p = set_plt(MDG, scale=-1)
        draw_this(MDG, p, 'red', red_nodes)
        draw_arrows(MDG, p, edge_list=red_list, style=None)
        draw_this(MDG, p, 'green', green_nodes)
        draw_arrows(MDG, p, edge_list=green_list)
        plt.savefig('images/{}RB.svg'.format(wayid), format='svg')
        plt.close()

        #nx.drawing.nx_agraph.write_dot(MDG, 'graphviz/{}FY.dot'.format(wayid))

if tsvfile:
    edges = pd.read_csv(tsvfile, delimiter='\t')

    edges = edges.rename(columns={'_key': 'edge', 'from': 'source', 'to': 'target'})


    for wayid in edges['wayid'].tolist():
        this_graph = [tuple(i) for i in edges[edges['wayid'] == wayid][['source', 'target']].values.tolist()]

        blue_nodes = {j for i in this_graph for j in i}
        if not this_graph:
            continue

        MDG = nx.MultiDiGraph(this_graph)

        if len(blue_nodes) == 2:
            p = set_plt(MDG, height=1)
        else:
            p = set_plt(MDG)

        if wayid in wayid_list:
            draw_arrows(MDG, p)
        else:
            draw_arrows(MDG, p, style=None)
        draw_this(MDG, p, 'blue')
        plt.savefig('images/{}FA.svg'.format(wayid), format='svg')
        plt.close()

        if len(blue_nodes) == 2:
            p = set_plt(MDG, height=1, scale=-1)
        else:
            p = set_plt(MDG, scale=-1)

        if wayid in wayid_list:
            draw_arrows(MDG, p)
        else:
            draw_arrows(MDG, p, style=None)
        draw_this(MDG, p, 'blue')
        plt.savefig('images/{}RA.svg'.format(wayid), format='svg')
        plt.close()

        #nx.drawing.nx_agraph.write_dot(MDG, 'graphviz/{}FX.dot'.format(wayid))

