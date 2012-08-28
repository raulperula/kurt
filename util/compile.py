#coding=utf8

# Copyright © 2012 Tim Radvan
# 
# This file is part of Kurt.
# 
# Kurt is free software: you can redistribute it and/or modify it under the 
# terms of the GNU Lesser General Public License as published by the Free 
# Software Foundation, either version 3 of the License, or (at your option) any 
# later version.
# 
# Kurt is distributed in the hope that it will be useful, but WITHOUT ANY 
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR 
# A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more 
# details.
# 
# You should have received a copy of the GNU Lesser General Public License along 
# with Kurt. If not, see <http://www.gnu.org/licenses/>.

"""Compiles a folder structure generated by decompile.py to a Scratch project.
Imports PNG or JPG images.
Scripts must be scratchblocks format txt files.

    Usage: compile.py "path/to/project files/"
"""

import time
import os, sys
from os.path import join as join_path
from os.path import split as split_path

import codecs
def open(file, mode="r"):
    return codecs.open(file, mode, "utf-8")


try:
    import kurt
except ImportError: # try and find kurt directory
    path_to_file = join_path(os.getcwd(), __file__)
    path_to_lib = split_path(split_path(path_to_file)[0])[0]
    sys.path.append(path_to_lib)

from kurt import *



IGNORED_NAMES = [".DS_Store"]


class InvalidFile(Exception):
    def __init__(self, path, error):
        self.path = path
        self.error = error
        
        message = ("%s\n" % path) + unicode(error)
        Exception.__init__(self, message)

class FileNotFound(Exception):
    pass
    
class FileExists(Exception):
    pass

class ParseError(Exception):
    pass



last_had_newline = True
def log(msg, newline=True):
    global last_had_newline
    if newline:
        if not last_had_newline:
            print
        print msg
    else:
        print msg, 
    last_had_newline = newline


def split_filename_number(filename, path=None):
    parts = filename.split(' ')
    try:
        number = int(parts[0])
    except ValueError:
        if path:
            path = os.path.join(path, filename) 
        else:
            path = filename
        raise InvalidFile(path, "Name must start with number")
    
    name = " ".join(parts[1:])
    
    return (number, name)


def read_costume_file(path):
    try:
        f = open(path)
    except IOError:
        return []
    
    line_count = 0
    costumes = []
    while 1:
        line = f.readline()
        line_count += 1
        if not line:
            return costumes
        
        line = line.strip()
        if line:
            filename = line.strip()
            costume = {
                "filename": filename,
                "rotationCenter": None,
            }
            
            while 1:
                line = f.readline()
                
                if not line.startswith("#"):                    
                    line_count += 1
                    if not line:
                        return costumes
                    
                    line = line.strip()
                    if not line:
                        break
                                        
                    parts = line.split(":")
                    if len(parts) == 2:
                        (key, value) = parts
                        costume[key] = value
                    elif len(parts) == 1:
                        key = parts[0]
                        costume[key] = None
                    else:
                        raise InvalidFile(path, "Line %i" % line_count)

            costumes.append(costume)
    



def read_script_file(morph, path):
    file = open(path)
    
    settings = {
        "pos": "(20, 20)",
    }
    
    while 1:
        try:
            line = file.readline()
        except EOFError:
            raise InvalidFile(path, "no blocks found")
        line = line.strip()
        
        if line:
            try:
                (name, value) = line.split(":")
            except ValueError:
                raise InvalidFile(path, "invalid line: "+line)
            
            name = name.strip().lower()
            value = value.strip()
            for setting in settings.keys():
                if name.startswith(setting):
                    settings[setting] = value
                    break
            else:
                settings[name] = value
        
        else:
            break
    
    pos = Point.from_string(settings["pos"])

    data = ""
    while 1:
        more_data = file.read()
        if not more_data: break
        data += more_data    
    
    data = unicode(data)
    data = data.replace('\r\n', '\n')
    data = data.replace('\r', '\n')
    
#     try:
    script = parse_scratchblocks(data)
#     except SyntaxError, e:
#         raise InvalidFile(path, e)
#     except BlockError, e:
#         raise InvalidFile(path, e)
    
    script = Script(pos, script.blocks)
    script.morph = morph
    # TODO: move position info inside parser?

    file.close()
    
    return script



def import_sprite(project_dir, sprite_name):
    sprite_dir = join_path(project_dir, sprite_name)
    is_stage = (sprite_name in ("Stage", "00 Stage"))
    if is_stage:    
        number = 0
    else:
        try:
            (number, sprite_name) \
                = split_filename_number(sprite_name, project_dir)
        except InvalidFile:
            number = None
            sprite_name = sprite_name
    
    log("* "+sprite_name, False)
    start_time = time.time()
    
    if is_stage:
        sprite = Stage()
        stage_background = sprite.backgrounds[0]
        sprite.backgrounds = []
    else:
        sprite = Sprite()
        sprite.name = sprite_name
    
    
    # Scripts
    scripts_dir = join_path(sprite_dir, "scripts")
    if os.path.exists(scripts_dir):
        script_names = os.listdir(scripts_dir)
        
        scripts = []
        for script_name in script_names:
            script_path = join_path(scripts_dir, script_name)
            script = read_script_file(sprite, script_path)
            scripts.append(script)
        
        scripts.sort(key=lambda script: script.pos.y)
        sprite.scripts = scripts
    
    
    # Costumes/Backgrounds
    if is_stage:
        costumes_dir = join_path(sprite_dir, "backgrounds")
    else:
        costumes_dir = join_path(sprite_dir, "costumes")
    
    costumes = []
    selected_costume = None
    if os.path.exists(costumes_dir):
        costume_file = costumes_dir+".txt"
        if os.path.exists(costume_file):
            costumes = read_costume_file(costume_file)
        
        found_costumes = os.listdir(costumes_dir)
        for ignore in IGNORED_NAMES:
            while ignore in found_costumes:
                found_costumes.remove(ignore)
        found_costumes.sort()
        
        remove_costumes = []
        for costume in costumes:
            costume_path = os.path.join(costumes_dir, costume["filename"])
            if ( costume["filename"] not in found_costumes or 
                 not os.path.exists(costume_path) ):
                log("Couldn't find costume "+costume_path)
                remove_costumes.append(costume)    
        for costume in remove_costumes:
            costumes.remove(costume)
            
        
        for filename in found_costumes:
            for other in costumes:
                if filename == other["filename"]:
                    break
            else:
                costumes.append({
                    "filename": filename,
                    "rotationCenter": None,
                })
        
        for costume in costumes:
            try:
                (number, name) = split_filename_number(costume["filename"])
                costume["number"] = number
            except InvalidFile:
                costume["number"] = None
        
        costumes.sort(key=lambda c: c["number"])
        costumes.sort(key=lambda c: c["number"] is None) # sort new costumes to end
        
        for costume_args in costumes:
            if "selected" in costume_args:
                selected_costume = costume
                costume_args.pop("selected")
    
            filename = costume_args["filename"]
            log("  - " + filename)
            
            costume_path = join_path(costumes_dir, filename)
            costume = ImageMedia.load(costume_path)
            if not costume:
                raise InvalidFile(costume_path, "Couldn't load image")
            
            if "name" in costume_args and costume_args["name"]:
                costume.name = costume_args["name"]
            else:
                try:
                    (_, costume.name) = split_filename_number(costume.name)
                except InvalidFile:
                    pass
            
            if costume_args["rotationCenter"]:
                costume.rotationCenter = Point.from_string(
                    costume_args["rotationCenter"])
            else:
                try:
                    size = costume.size
                except ValueError:
                    costume.rotationCenter = Point(0, 0)
                    size = None
                if size:
                    (width, height) = size
                    costume.rotationCenter = Point(int(width / 2), int(height / 2))
                
            sprite.images.append(costume)
    
    if is_stage and not costumes:
        sprite.backgrounds = [stage_background]
    
    if not selected_costume and costumes:
        selected_costume = costumes[0]
    
    
    # TODO: Variables
    var_list_path = join_path(sprite_dir, "variables.txt")
    var_file = open(var_list_path)
    for line in var_file:
        line = line.strip("\r\n")
        if line:
            parts = line.split(" = ")
            var_name = parts[0]
            value = " = ".join(parts[1:])        
            sprite.vars[var_name] = value
    
    
    # Lists
    lists_dir = join_path(sprite_dir, "lists")
    if os.path.exists(lists_dir):
        list_names = os.listdir(lists_dir)
        for list_name in list_names:
            if list_name in IGNORED_NAMES:
                continue
            list_path = os.path.join(lists_dir, list_name)
            
            if "." in list_name: # strip extension
                list_name = ".".join(list_name.split(".")[:-1])
            
            list_file = open(list_path)
            items = [line.strip("\r\n") for line in list_file.readlines()]
            sprite.lists[list_name] \
                = ScratchListMorph(name=list_name, items=items)
            list_file.close()
    
    sprite_save_time = time.time() - start_time
    log(sprite_save_time)
    
    return (number, sprite)




def compile(project_dir, debug=True): # DEBUG: set to false
    if project_dir.endswith(".sb"):
        project_dir = project_dir[:-3]
    
    if project_dir.endswith(" files"):
        project_path = project_dir[:-6]
        
    else:
        project_path = project_dir
        project_dir += " files"
    
    if not os.path.exists(project_dir):
        raise FileNotFound(project_dir)
    
    project = ScratchProjectFile.new(project_path)
    
    if os.path.exists(project.path):
        raise FileExists(project.path)
    
    log("Importing sprites...")
    
    sprite_names = os.listdir(project_dir)
    
    if "00 Stage" in sprite_names:
        stage_name = "00 Stage"
    elif "Stage" in sprite_names:
        stage_name = "Stage"
    else:
        stage_name = None
    
    if stage_name:
        sprite_names.remove(stage_name)
    
    for ignore in IGNORED_NAMES:
        while ignore in sprite_names:
            sprite_names.remove(ignore)
    
    if stage_name is not None:
        (_, stage) = import_sprite(project_dir, stage_name)
        project.stage = stage
    
    sprites = [import_sprite(project_dir, name) for name in sprite_names]
    sprites.sort(key=lambda (n, s): n)
    sprites.sort(key=lambda (n, s): n is None) # sort new sprites to end
    sprites = [sprite for (number, sprite) in sprites]
    project.sprites = sprites
    
    for sprite in sprites:
        for script in sprite.scripts:
            script.replace_sprite_refs(lookup_sprite_named = project.get_sprite)
    
    return project



if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print __doc__
        exit()

    else:
        path = sys.argv[1]
    
        if path.endswith(".sb"):
            path = path[:-3]
        if path.endswith(" files"):
            path = path[:-6]

        try:
            project = compile(path)
            print "Saving..."
            start_time = time.time()
            project.save()
            print time.time() - start_time
        
        except FileExists, e:
            print "File exists: %s" % unicode(e)
            exit(1)

        except InvalidFile, e:
            print
            print "Invalid file:", e
            print e.error
            exit(2)

        except FileNotFound, e:
            print "File missing: %s" % unicode(e)
            exit(2)