#!/usr/bin/env python


# Copyright (C) 2009, Mathieu PASQUET <mpa@makina-corpus.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

__docformat__ = 'restructuredtext en'

import sys
from copy import copy
import os
import logging

import pkg_resources

from zc.buildout.easy_install import Installer

from minitage.recipe.egg import Recipe as Egg
from minitage.recipe import common
from minitage.recipe.scripts import Recipe as Script
from minitage.recipe.cmmi import Recipe as Cmmi
from minitage.recipe.scripts import parse_entry_point

__log__ = logging.getLogger('buildout.minitagificator')

def activate(ws):
    for entry in ws.entries:
        if not entry in sys.path:
            sys.path.append(entry)

def monkey_patch_recipes(buildout):
    # try to patch zc.recipe.egg
    # and be kind on API Changes
    __log__.info('Minitaging some recipes')
    try:
        import zc.recipe.egg
        if getattr(zc.recipe.egg, 'Egg', None):
            __log__.debug('Patched zc.recipe.egg.Egg')
            zc.recipe.egg.Egg = Script
        else:
          __log__.debug('!!!! Can\'t patch zc.recipe.egg.Egg')
        if getattr(zc.recipe.egg, 'Eggs', None):
            __log__.debug('Patched zc.recipe.egg.Eggs')
            zc.recipe.egg.Eggs = Egg
        else:
          __log__.debug('!!!! Can\'t patch zc.recipe.egg.Eggs')
        if getattr(zc.recipe.egg, 'Scripts', None):
            __log__.debug('Patched zc.recipe.egg.Scripts')
            zc.recipe.egg.Scripts = Script
        else:
            __log__.debug('!!!! Can\'t patch zc.recipe.egg.Scripts')
    except Exception, e:
        __log__.debug('!!!! Can\'t patch zc.recipe.egg.(Scripts|Eggs): %s' % e)
    try:
        import zc.recipe.egg.custom
        if getattr(zc.recipe.egg.custom, 'Custom', None):
            __log__.debug('Patched zc.recipe.egg.custom')
            zc.recipe.egg.custom = Egg
        else:
            __log__.debug('!!!! Can\'t patch zc.recipe.egg.custom.Custom')
    except:
        __log__.debug('!!!! Can\'t patch zc.recipe.egg.custom.Custom')
    try:
        import zc.recipe.cmmi
        if getattr(zc.recipe.cmmi, 'Recipe', None):
            __log__.debug('Patched zc.recipe.cmmi')
            zc.recipe.cmmi.Recipe = Cmmi
        else:
            __log__.debug('!!!! Can\'t patch zc.recipe.cmmi')
    except:
        __log__.debug('!!!! Can\'t patch zc.recipe.cmmi')

def monkey_patch_buildout_installer(buildout):
    __log__.info('Minitagiying Buidout Installer')
    dexecutable = buildout['buildout']['executable']
    def install(specs, dest,
                links=(), index=None,
                executable=dexecutable, always_unzip=None,
                path=None, working_set=None, newest=True, versions=None,
                use_dependency_links=None, allow_hosts=('*',)):
        if not '/' in executable:
            executable = common.which(executable)
        opts = copy(buildout['buildout'])
        opts['executable'] = executable
        r = Egg(buildout, 'foo', opts)
        r.eggs = specs
        r._dest = dest
        if not r._dest:
            r._dest = buildout['buildout']['eggs-directory']
        if links:
            r.find_links = links
        if index:
            r.index = index
        if always_unzip:
            r.zip_safe = not always_unzip
        caches = []
        if path:
            if not isinstance(path, str):
                caches.extend([ os.path.abspath(p) for p in path])
            else:
                caches.append(os.path.abspath(path))
        for cache in caches:
            if not (cache in r.eggs_caches):
                r.eggs_caches.append(cache)
        if not versions:
            versions = buildout.get('versions', {})
        ## which python version are we using ?
        #r.executable_version = os.popen(
        #    '%s -c "%s"' % (
        #        executable,
        #        'import sys;print sys.version[:3]'
        #    )
        #).read().replace('\n', '')
        r.inst = easy_install.Installer(
            dest=None,
            index=r.index,
            links=r.find_links,
            executable=r.executable,
            always_unzip=r.zip_safe,
            newest = newest,
            versions = versions,
            use_dependency_links = use_dependency_links,
            path=r.eggs_caches,
            allow_hosts=allow_hosts,
        )
        reqs, working_set = r.working_set(working_set=working_set)
        return working_set
    from zc.buildout import easy_install
    easy_install.install = install

def monkey_patch_buildout_options(buildout):
    __log__.info('Minitaging Buidout Options')
    from zc.buildout.buildout import Options
    def _call(self, f):
        monkey_patch_recipes(buildout)
        Options._buildout = buildout
        return Options._old_call(self, f)
    Options._old_call = Options._call
    Options._call = _call

def monkey_patch_buildout_scripts(buildout):
    __log__.info('Minitagiying Buidout scripts')
    def scripts(reqs,
                working_set,
                executable,
                dest,
                scripts=None,
                extra_paths=(),
                arguments='',
                interpreter='',
                initialization='',
                relative_paths=False,
               ):
        if not '/' in executable:
            executable = common.which(executable)
        if not scripts:
            scripts = []
        if (not relative_paths) or (relative_paths == 'false'):
            relative_paths = 'false'
        else:
            relative_paths = 'true'
        if not interpreter:
            interpreter = ''
        options = {}
        options['eggs'] = ''
        options['entry-points'] = ''
        options['executable'] = executable
        options['scripts'] = '\n'.join(scripts)
        options['extra-paths'] = '\n'.join(extra_paths)
        options['arguments'] = arguments
        options['interpreter'] = interpreter
        options['initialization'] = initialization
        options['relative-paths'] = relative_paths
        for req in reqs:
            if isinstance(req, str):
                if parse_entry_point(req):
                    options['entry-points'] += '%s\n' % req
                else:
                    options['scripts'] += '%s\n' % req
            elif isinstance(req, tuple):
                options['entry-points'] += '%s=%s:%s' % req
        r = Script(buildout, 'foo', options)
        r._dest = dest
        res = r.install(working_set=working_set)
        return res
    from zc.buildout import easy_install
    easy_install.scripts = scripts


def install(buildout=None):
    monkey_patch_buildout_installer(buildout)
    monkey_patch_buildout_scripts(buildout)
    monkey_patch_buildout_options(buildout)
    monkey_patch_recipes(buildout)

# vim:set et sts=4 ts=4 tw=80:

