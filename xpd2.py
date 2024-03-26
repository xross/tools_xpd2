#!/usr/bin/python

VERSION = "2.0"

from optparse import OptionParser


common_commands =  []

other_commands = []

hidden_commands = []

WIP_commands = [
    ("update","update %prog to latest version"),
    ("show_deps", "Show dependencies"),
]

def main():
    usage = "usage: %prog command [options]"
    usage += "\n\nMost useful commands:\n\n"
    for c in common_commands:
        usage += "%20s: %s\n" % (c[0], c[1])

    usage += "\n\nOther commands:\n\n"
    for c in other_commands:
        usage += "%20s: %s\n" % (c[0], c[1])
    
    usage += "\n\nWIP commands\n::WARNING:: these may work, work partially, do nothing, or break something\n\n"
    for c in WIP_commands:
        usage += "%20s: %s" % (c[0], c[1])

    optparser = OptionParser(usage=usage,version=f"\%prog {VERSION}")
    (options, args) = optparser.parse_args()
    if len(args) < 1:
        optparser.error("Please specify a command")

if __name__ == "__main__":
    main()