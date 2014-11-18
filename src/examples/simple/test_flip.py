#!/usr/bin/env python
# File written by pyctools-editor. Do not edit.

import argparse
import logging
from pyctools.core.compound import Compound
import pyctools.components.io.imagedisplay
import pyctools.components.io.imagefilereader
import pyctools.components.example.flip

class Network(object):
    def __init__(self):
        self.components = \
{   'display': {   'class': 'pyctools.components.io.imagedisplay.ImageDisplay',
                   'config': '{}',
                   'pos': (500.0, 250.0)},
    'flip': {   'class': 'pyctools.components.example.flip.Flip',
                'config': '{}',
                'pos': (350.0, 250.0)},
    'reader': {   'class': 'pyctools.components.io.imagefilereader.ImageFileReader',
                  'config': "{'path': '/home/jim/Documents/projects/pyctools/master/src/doc/images/editor_8.png'}",
                  'pos': (200.0, 250.0)}}
        self.linkages = \
{   ('flip', 'output'): ('display', 'input'),
    ('reader', 'output'): ('flip', 'input')}

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
