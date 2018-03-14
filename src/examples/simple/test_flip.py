#!/usr/bin/env python
# File written by pyctools-editor. Do not edit.

import argparse
import logging
from pyctools.core.compound import Compound
import pyctools.components.io.imagedisplay
import pyctools.components.io.dumpmetadata
import pyctools.components.io.imagefilepil
import pyctools.components.example.flip

class Network(object):
    components = \
{   'display': {   'class': 'pyctools.components.io.imagedisplay.ImageDisplay',
                   'config': "{'outframe_pool_len': 3}",
                   'pos': (400.0, 100.0)},
    'flip': {   'class': 'pyctools.components.example.flip.Flip',
                'config': "{'outframe_pool_len': 3, 'direction': 'vertical'}",
                'pos': (270.0, 100.0)},
    'metadata': {   'class': 'pyctools.components.io.dumpmetadata.DumpMetadata',
                    'config': "{'outframe_pool_len': 3, 'raw': 0}",
                    'pos': (400.0, 210.0)},
    'reader': {   'class': 'pyctools.components.io.imagefilepil.ImageFileReaderPIL',
                  'config': "{'path': "
                            "'/home/jim/Documents/projects/pyctools/master/src/doc/images/editor_8.png'}",
                  'pos': (140.0, 100.0)}}
    linkages = \
{   ('flip', 'output'): [('metadata', 'input'), ('display', 'input')],
    ('reader', 'output'): [('flip', 'input')]}

    def make(self):
        comps = {}
        for name, component in self.components.items():
            comps[name] = eval(component['class'])(config=eval(component['config']))
        return Compound(linkages=self.linkages, **comps)

if __name__ == '__main__':

    comp = Network().make()
    cnf = comp.get_config()
    parser = argparse.ArgumentParser()
    cnf.parser_add(parser)
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='increase verbosity of log messages')
    args = parser.parse_args()
    logging.basicConfig(level=logging.ERROR - (args.verbose * 10))
    del args.verbose
    cnf.parser_set(args)
    comp.set_config(cnf)
    comp.start()

    try:
        comp.join(end_comps=True)
    except KeyboardInterrupt:
        pass

    comp.stop()
    comp.join()
