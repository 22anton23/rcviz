# rcviz : a small recursion call graph vizualization decorator
# Copyright (c) Ran Dugal 2014
# Licensed under the GPLv2, which is available at
# http://www.gnu.org/licenses/gpl-2.0.html

import copy
import inspect
import logging

from pygraphviz import AGraph


class callgraph(object):
    def __init__(self):
        self.callers = {}  # caller_fn_id : node_data
        self.frames = []   # keep frame objects reference
        self.depth = 0     # stack depth

    def clear(self):
        self.callers.clear()
        self.frames.clear()
        self.depth = 0

    def render(self, filename):
        g = AGraph(strict=False, directed=True)

        # create nodes
        for frame_id, node in self.callers.items():
            label = "{ %s(%s) | ret: %s }" % \
                (node.f_name, node.argstr(), node.ret)
            g.add_node(frame_id, shape='Mrecord', label=label,
                       fontsize=13, labelfontsize=13)

        # create edges
        for frame_id, node in self.callers.items():
            child_nodes = []
            for child_id in node.child_methods:
                child_nodes.append(child_id)
                g.add_edge(frame_id, child_id)

            # order edges l to r
            if len(child_nodes) > 1:
                sg = g.add_subgraph(child_nodes, rank='same')
                sg.graph_attr['rank'] = 'same'
                prev_node = None
                for child_node in child_nodes:
                    if prev_node:
                        sg.add_edge(prev_node, child_node, color="#ffffff")
                    prev_node = child_node

        g.layout()
        g.draw(path=filename, prog='dot')

        print("callviz: rendered to %s" % filename)
        self.clear()


class node_data(object):
    def __init__(self, args, kwargs, f_name, ret, child_methods):
        self.args = args
        self.kwargs = kwargs
        self.f_name = f_name
        self.ret = ret
        self.child_methods = child_methods

    def __str__(self):
        return "%s -> child_methods: %s" % (self.nodestr(), self.child_methods)

    def nodestr(self):
        return "{0.ret} = {0.fn_name}{1}".format(self, self.argstr())

    def argstr(self):
        s_args = ", ".join(map(str, self.args))
        s_kwargs = ", ".join(
            "{0}={1}".format(k, v) for k, v in self.kwargs.items())
        return s_args + s_kwargs


class viz(object):
    '''decorator to construct the call graph with args and return values
    as labels'''

    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.verbose = False
        self.cg = callgraph()

    def __call__(self, *args, **kwargs):
        g_callers = self.cg.callers
        g_frames = self.cg.frames

        # find the caller frame, and add self as a child node
        caller_frame_id = None

        fullstack = inspect.stack()

        if self.verbose:
            logging.debug("full stack: %s" % str(fullstack))

        if len(fullstack) > 2:
            caller_frame_id = id(fullstack[2][0])
            if self.verbose:
                logging.debug("caller frame: %s %s" %
                              (caller_frame_id, fullstack[2]))

        this_frame_id = id(fullstack[0][0])
        if self.verbose:
            logging.info("this frame: %s %s" % (this_frame_id, fullstack[0]))

        if this_frame_id not in g_frames:
            g_frames.append(fullstack[0][0])

        if this_frame_id not in g_callers:
            g_callers[this_frame_id] = node_data(
                args, kwargs, self.wrapped.__name__, None, [])

        if caller_frame_id in g_callers:
            g_callers[caller_frame_id].child_methods.append(this_frame_id)

        self.cg.depth += 1
        ret = self.wrapped(*args, **kwargs)
        self.cg.depth -= 1

        if self.verbose:
            logging.debug('unwinding frame id: %s' % this_frame_id)

        g_callers[this_frame_id].ret = copy.deepcopy(ret)

        if not self.cg.depth:
            self.cg.render(self.wrapped.__name__ + ".png")

        return ret
