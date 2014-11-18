#!/usr/bin/env python
# File written by pyctools-editor. Do not edit.

import argparse
import logging
from pyctools.core.compound import Compound
import pyctools.components.io.dumpmetadata
import pyctools.components.io.imagedisplay
import pyctools.components.io.imagefilereader
import pyctools.components.example.zigzag

class Network(object):
    def __init__(self):
        self.components = \
{   'display': {   'class': 'pyctools.components.io.imagedisplay.ImageDisplay',
                   'config': '{}',
                   'pos': (400.0, 100.0)},
    'metadata': {   'class': 'pyctools.components.io.dumpmetadata.DumpMetadata',
                    'config': '{}',
                    'pos': (550.0, 100.0)},
    'reader': {   'class': 'pyctools.components.io.imagefilereader.ImageFileReader',
                  'config': "{'path': '/home/jim/Documents/projects/pyctools/master/src/doc/images/editor_8.png'}",
                  'pos': (100.0, 100.0)},
    'zigzag': {   'class': 'pyctools.components.example.zigzag.Zigzag',
                  'config': '{}',
                  'pos': (250.0, 100.0)}}
        self.linkages = \
{   ('display', 'output'): ('metadata', 'input'),
    ('reader', 'output'): ('zigzag', 'input'),
    ('zigzag', 'output'): ('display', 'input')}

    def make(self):
        comps = {}
        for name, component in self.components.items():
            comps[name] = eval(component['class'])()
            cnf = comps[name].get_config()
            for key, value in eval(component['config']).items():
                cnf[key] = value
            comps[name].set_config(cnf)
        return Compound(linkages=self.linkages, **comps)

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)
    comp = Network().make()
    cnf = comp.get_config()
    parser = argparse.ArgumentParser()
    cnf.parser_add(parser)
    args = parser.parse_args()
    cnf.parser_set(args)
    comp.set_config(cnf)
    comp.start()
    comp.join()
