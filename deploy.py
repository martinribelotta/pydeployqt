#! /usr/bin/env python3
"""pyWindeployqt

This is a wrapper for  mingw32 objdump replacing windeployqt which is missing from MXE
I don't know why they disabled it, but here it is.

Example:
./deploy.py --build=~/ClionProjects/project/build/ \
--objdump=/home/user/mxe/usr/bin/i686-w64-mingw32.shared-objdump \
~/ClionProjects/project/build/project.exe;

"""

__author__ = 'Alexey Elymanov (strangeqargo@gmail.com)'

import subprocess
import os
import sys
import re
import os.path

import argparse
parser = argparse.ArgumentParser()

parser.add_argument("--build", help="where to place libraries, optional, files will go to target location by default")
parser.add_argument("--objdump", help="objdump executable (/home/user/mxe/usr/bin/i686-w64-mingw32.shared-objdump)")
parser.add_argument("--libs", help="where to search for libraries (optional) infers from objdump")
parser.add_argument("--extradll", help="Extra list of dll")
parser.add_argument("--qmake", help="qmake to use")
parser.add_argument("target")

args = parser.parse_args()
if len(sys.argv) == 1 or not (args.libs or args.objdump):
    parser.print_help()
    sys.exit(1)

target = os.path.expanduser(args.target)
objdump_path = os.path.expanduser(args.objdump)
qmake_path = os.path.expanduser(args.qmake)
if not qmake_path:
    qmake_path = "qmake"

if not args.build:
    build_path = os.path.expanduser(os.path.dirname(args.target)) + "/"
else:
    build_path = os.path.expanduser(args.build)

libs = args.libs
if not args.libs:
    libs = objdump_path.replace('/bin', '').replace('-objdump','')

extras = args.extradll.split(':')
if not extras:
    extras = []
    
# build_path = "/home/user/ClionProjects/project/build/"
# libs = "/home/user/mxe/usr/i686-w64-mingw32.shared"
# objdump_path = "/home/user/mxe/usr/bin/i686-w64-mingw32.shared-objdump"
# target = "project.exe"


def run_check():
    return subprocess.getoutput("wine project.exe")


def find_dll(dll):
    out = ""
    for l in libs.split(':'):
        out += subprocess.getoutput("find " + l + " | grep '" + dll+"$'")
    return out.strip('\n')


def library_install_exe(out=''):
    out = run_check().splitlines()
    for line in out:
        # err = re.search('(err:module:import_dll (Library |Loading library)) (.*?\.dll) ', line)
        err = re.search('([^ ]+\.dll) \(which', line)
        if err is not None:

            dll = err.group(1)
            dll = find_dll(dll)
            if dll is not None:
                copy_command = "cp " + dll + " " + build_path
                print("copy: ", copy_command)
                subprocess.getoutput(copy_command)
            library_install_exe(out)


def library_install_objdump(path, level):
    if path in skip_libs or path in done:
        return

    if level > 0:
        lib = find_dll(path)
        if lib == "":  # not found
            skip_libs.append(path)
            print("Not found: " + path)
            return
        print(lib)
        subprocess.getoutput("cp " + lib + " " + build_path)

    else:
        print("Processing target " + path)
        lib = path

    done.append(path)

    command = objdump_path + " -p " + lib + " | grep -o ': .*\.dll$'"
    res = subprocess.getstatusoutput(command)
    if (res[0] > 0):
        print("Error: objdump failed with {}: {}".format(lib, res[1]))
    else:
        dlls = subprocess.getoutput(command).split("\n")
        for line in dlls:
            dll = (line.split(": "))[1]
            if dll not in done and dll not in skip_libs:
                level += 1
                library_install_objdump(dll, level)

skip_libs = list()
done = list()
export_plugins = [
    "bearer",
    "generic",
    "iconengines",
    "imageformats",
    "platforms",
    "platformthemes",
    "printsupport",
    "styles"
]

def main():

    os.chdir(build_path)

    #library_install_exe(target)
    library_install_objdump(target, 0)
    for e in extras:
        lib = find_dll(e)
        if lib == "":  # not found
            print("Not found: " + e)
            return
        print(lib)
        e, o = subprocess.getstatusoutput("cp " + lib + " " + build_path)
        if e != 0:
            print("Exit code of cp is {}: {}", e, o)
    # /usr/lib/mxe/usr/i686-w64-mingw32.shared/qt5/bin/qmake -query|grep PLUGINS
    o = subprocess.getoutput("{} -query | grep PLUGINS".format(qmake_path))
    plugindir = o.split(':')[1]
    for name in export_plugins:
        path = os.path.join(plugindir, name)
        e, o = subprocess.getstatusoutput("cp -rf " + path + " " + build_path)
        if e != 0:
            print("Exit code of cp is {}: {}", e, o)
    pass

main()
