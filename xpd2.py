#!/usr/bin/python

VERSION = "2.0"

from xmos_logging import log_error, log_warning, log_info, log_debug, configure_logging, print_status_summary
from optparse import OptionParser
import sys, os
from xpd2.xpd_data import Repo_, Sandbox_
from pathlib import Path


common_commands =  [
                    ("status", "Show current status (can also use show or info)"),
                    ("list", "List releases"),
                    ]

other_commands = []

hidden_commands = []

WIP_commands = [
    ("update","update %prog to latest version"),
    ("show_deps", "Show dependencies"),
]

def xpd_status(repo, options, args):

    print("XPD_STATUS")

    repo.print()

    pass

def xpd_list(repo, options, args):

    rels = repo.releases

    number_to_show = 10
    if len(rels) > number_to_show and not options.show_all:
        log_info("Only showing %d most recent releases. Use 'xpd list --all' to see all releases" % number_to_show)

    for i,rel in enumerate(rels):
        if i == number_to_show and not options.show_all:
            break

        if rel.virtual == "True":
            log_info("%s (unknown git location)" % str(rel.version))
        else:
            #log_info(str(rel.version) + " parenthash: " + str(rel.parenthash))
            log_info(str(rel.version))
            if rel.notes:
                for n in rel.notes:
                    log_info(str(n))

def main():
    configure_logging()
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

    optparser.add_option("--all", dest="show_all", action="store_true", default=False, help="Show all options")


    (options, args) = optparser.parse_args()
    if len(args) < 1:
        optparser.error("Please specify a command")

    command = args[0]

    if command == "help":
        optparser.print_help()
        sys.exit(0)


    repo_path = Path(os.getcwd())

    print("top level repo:" +str(repo_path))

    sandbox = Sandbox_(repo_path)

    command_fn = eval("xpd_%s" % command)
    command_fn(sandbox, options, args)

    args = args[1:]

if __name__ == "__main__":
    main()
