import json
import pandas as pd
import numpy as np
import anytree as tree
from anytree import NodeMixin
import plotly.express as px
from plotly import colors
import os
import matplotlib.pyplot as plt

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


def get_default_allocation(name=None):
    PFIN_DIR = os.path.dirname(__file__)
    if os.path.isfile(os.path.join(PFIN_DIR, f'{name}_allocation.json')):
        return os.path.join(PFIN_DIR, f'{name}_allocation.json')
    else:
        return os.path.join(PFIN_DIR, 'pinwheel_allocation.json')


def read_allocation(file=None):
    if file is None:
        file = 'pinwheel_allocation.json'

    with open(file) as w:
        data = json.load(w)

    return AssetAllocation(json_data=data)


def normalize_L1(vals):
    sumvals = sum(vals)
    vals = [v / sumvals for v in vals]
    return vals, sumvals


class AssetNode(NodeMixin):

    type = ''
    name = ''
    allocation = 0.0
    total_allocation = 0.0

    def __init__(self, Type, Name, Allocation, parent=None, children=None):
        super(AssetNode, self).__init__()
        self.type = Type
        self.name = Name
        self.allocation = Allocation
        self.parent = parent
        if parent is None:
            self.total_allocation = 1.0
        else:
            self.total_allocation = parent.total_allocation * self.allocation
        if children:
            self.children = children


class AssetAllocation:

    def __init__(self, json_data=None):
        self.root = self.add_node_recursively(parent=None, json_data=json_data)
        for node in tree.LevelOrderIter(self.root):
            self.normalize_children(node)
        # TODO: error checking, for example make sure every "type" is the same across the same level
        # TODO: Enforce unique node names, or at least unique within a level or between siblings

    def add_node_recursively(self, parent, json_data):
        new_parent = AssetNode(**{x: json_data[x] for x in json_data if x != "Subclasses"}, parent=parent)
        if "Subclasses" in json_data.keys():
            for cl in json_data["Subclasses"]:
                self.add_node_recursively(parent=new_parent, json_data=cl)

        return new_parent

    def normalize_children(self, parent):
        vals, sumvals = normalize_L1([c.allocation for c in parent.children])
        for c, idx in zip(parent.children, range(len(parent.children))):
            c.allocation = vals[idx]
            if sumvals != 0:
                c.total_allocation = c.total_allocation / sumvals

    def dataframe(self):
        # every level below the root corresponds to a new column
        r = tree.Resolver('type')
        by_level = [children for children in tree.LevelOrderGroupIter(self.root)]
        level_titles = [nodelevel[0].type for nodelevel in by_level[1:]]
        node_data = {'Total Allocation %': []}
        for key in level_titles:
            node_data[key] = []

        w = tree.Walker()
        for leaf in self.root.leaves:
            leaf_path = w.walk(self.root, leaf)
            for level in leaf_path[-1]:
                node_data[level.type].append(level.name)
                if level.is_leaf:
                    node_data['Total Allocation %'].append(level.total_allocation)

            for item in node_data.keys():
                if len(node_data[item]) < len(node_data['Total Allocation %']):
                    node_data[item].append('N/A')

        return pd.DataFrame(node_data).set_index(level_titles)

    def __str__(self):
        treestr = ''
        for pre, _, node in tree.RenderTree(self.root):
            treestr += u"%s%s, %.02f%% of parent, %.02f%% of total\n" % (pre, node.name, 100*node.allocation, 100*node.total_allocation)

        return treestr


class Portfolio:

    has_allocation = False
    has_balance = False

    def __init__(self, investor_name, goal=None, months_to_goal=None, portfolio_name=None, allocation=None, allocation_file=None, balance_file=None):
        self.investor = investor_name
        self.goal = goal
        self.months_to_goal = months_to_goal
        if portfolio_name is None:
            self.portfolio_name = investor_name + "'s Portfolio"
        else:
            self.portfolio_name = portfolio_name

        if allocation is not None:
            self.allocation = allocation
            self.has_allocation = True
        else:
            if allocation_file is not None:
                self.allocation = read_allocation(allocation_file)
                self.has_allocation = True

        if balance_file is not None:
            self.balance = pd.read_csv(balance_file)
            self.has_balance = True

        # TODO: Error checking to make sure balance and allocation files match up
        # TODO: Method to write template file for balance/or allocation from the other

    def rebalance_monthly(self, outfile=None):
        bal_alloc = self.balance.groupby(['Asset Class', 'Asset Style', 'Ticker']).agg('sum')
        allo_df = self.allocation.dataframe()
        goals_df = bal_alloc.merge(allo_df, how='outer', left_index=True, right_index=True).fillna(0)
        goals_df['Goal Balance'] = goals_df['Total Allocation %'] * self.goal
        goals_df['Balance Change'] = goals_df['Goal Balance'] - goals_df['Initial Balance']
        goals_df['Per Month'] = goals_df['Balance Change'] / self.months_to_goal
        if outfile is not None:
            goals_df.to_csv(outfile)

        return goals_df

    def pie_simple(self, class_name='Root'):
        if class_name == 'Root':
            big_children = self.allocation.root.children
        else:
            big_children = tree.find(self.allocation.root, filter_=lambda node: node.name == class_name).children

        names = [child.name for child in big_children]
        allocs = [child.allocation for child in big_children]
        #plt.figure(1, figsize=(20, 10))
        #the_grid = GridSpec(2, 2)
        cmap = plt.get_cmap('Pastel1')
        colors = [cmap(i) for i in np.linspace(0, 1, 2*len(big_children))]
        # plt.subplot(the_grid[0, 1], aspect=1, title='Asset Allocation')
        type_show_ids = plt.pie(allocs, labels=names, autopct='%1.1f%%', shadow=True, colors=colors)
        plt.show()

    def sunburst(self, level_types, value_col, alternate_leaf_col=None, balance=True):
        if not balance:
            balance_data = self.allocation.dataframe().reset_index()
        else:
            balance_data = self.balance

        # rename leaves if necessary
        balance_data['Dupe'] = balance_data.duplicated(level_types[-1], keep=False)
        if alternate_leaf_col is not None:
            balance_data.loc[balance_data['Dupe'], level_types[-1]] = balance_data.loc[balance_data['Dupe'], alternate_leaf_col]
        else:
            balance_data.loc[balance_data['Dupe'], level_types[-1]] = None

        fig = px.sunburst(balance_data, path=level_types, values=value_col, color=level_types[0], color_discrete_sequence=colors.qualitative.Plotly)
        fig.update_traces(insidetextorientation='radial', sort=False)
        #fig.show()
        if balance:
            fig.write_html('balance.html', auto_open=True)
        else:
            fig.write_html('allocation_goal.html', auto_open=True)

        return fig