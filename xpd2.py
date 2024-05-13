#!/usr/bin/python

VERSION = "2.0"

from xmos_logging import (
    log_error,
    log_warning,
    log_info,
    log_debug,
    configure_logging,
    print_status_summary,
)
from optparse import OptionParser
import sys, os
from xpd2.xpd_data import Repo, Sandbox
from pathlib import Path
from xpd2.xpd_version import Version, VersionParseError


common_commands = [
    ("status", "Show current status"),
    ("list", "List releases of current repo"),
    ("create_release", "Create a release"),

]

other_commands = [    ("check_sandbox", "Checks a sandbox for errors"),
]

hidden_commands = []

WIP_commands = [
    ("update", "update %prog to latest version"),
]


def xpd_check_sandbox(sandbox, options, args):

    errors = 0
    warnings = 0

    # TODO Check sandbox for errors here:
    # - Check if we're tracking a branch the lastest version is present

    # Do some basic checking for now
    # Check we have the version of a repo we specify in the dependencies
    for repo in sandbox._repos:
        for dep in repo.dependencies:
            dep_repo = sandbox.find_repo_by_name(dep.name)
            if dep_repo.version:
                if dep.version:
                    if dep_repo.version != dep.version:
                            errors += 1
                            log_error('%s : %s used by %s' % (dep_repo.name, dep.version, repo.name))
                            log_info("ERROR: Instead use actual version %s" %(dep_repo.version))
            else:
                # TODO properly deal with githash case
                log_warning(f"{dep_repo} is not on a version but on hash: {dep_repo.current_version_or_githash(short=True)}")
                warnings += 1

        if repo.behind_upstream and not options.force:
            log_error(f"{repo.name}: Upstream changes not merged in. Cannot create release")
            log_error("Try a 'git pull'")
            errors += 1

    return (errors, warnings)

def xpd_create_release(sandbox, options, args):

    local_mod = False
    for r in sandbox._repos:
        if r.has_local_modifications:
            log_warning(f"{r} has local modifications")
            local_mod = True

    if local_mod and not options.force:
        log_error("Cannot create release: uncommitted modifications")
        sys.exit(1)

    (errors, warnings) = xpd_check_sandbox(sandbox, options, args)

    if errors or warnings:
        log_error(f"Fix the {errors + warnings} detected problem(s) before making a release")
        sys.exit(1)

    if hasattr(options, 'release_type') and options.release_type:
        rtype = options.release_type
    else:
        rtype = None
        while True:
            x = input("Enter release type (a=alpha,b=beta,rc=rc,r=release): ")
            if x in ['a', 'alpha']:
                rtype = 'alpha'
            elif x in ['b', 'beta']:
                rtype = 'beta'
            elif x in ['rc', 'c']:
                rtype = 'rc'
            elif x in ['r']:
                rtype = ''

            if rtype or rtype == '':
                break
            else:
                # No need to make an error that is logged
                print(("ERROR: Unknown release type '%s'" % x))

    #TODO handle branched from case?

    # Check for changelog
    repo = sandbox._repos[0]
    notes = repo.changelog_entries
    if not notes and not options.force:
        log_error("No versions found in CHANGELOG.rst, please update file first")
        sys.exit(1)

    # Get the version number we want to release
    (latest_in_changelog, items) = notes[0]

    if hasattr(options, 'release_version') and options.release_version:
        print('release_version: ' + str(options.release_version))
        version = Version(version_str=options.release_version)
    else:
        latest = repo.latest_full_release
        if latest:
            print(("Latest release: %s" % latest.version))
            latest_version = latest.version
        else:
            print("There is no full release yet")
            latest_version = Version(0, 0, 0, 0)

        print(f"    Next major: {latest_version.major_increment()}")
        print(f"    Next minor: {latest_version.minor_increment()}")
        print(f"    Next point: {latest_version.point_increment()}")

        latest_pre = repo.latest_pre_release
        if latest_pre and (not latest or latest_pre > latest):
            print(("Latest pre-release: %s" % latest_pre.version))

        version = None
        while True:
            x = input(f"Enter version number [{latest_in_changelog}]:")
            if not x:
                x = latest_in_changelog

            try:
                version = Version(version_str=x)
                break
            except:
                log_error("Invalid version number '%s'" % x)


def xpd_status(sandbox, options, args):

    sandbox.print()


def xpd_list(sandbox, options, args):

    # Assume first repo is the "top-level" repo
    rels = sandbox._repos[0].releases

    number_to_show = 10
    if len(rels) > number_to_show and not options.show_all:
        log_info(
            "Only showing %d most recent releases. Use 'xpd list --all' to see all releases"
            % number_to_show
        )

    for i, rel in enumerate(rels):
        if i == number_to_show and not options.show_all:
            break

        if rel.virtual == "True":
            log_info("%s (unknown git location)" % str(rel.version))
        else:
            # log_info(str(rel.version) + " parenthash: " + str(rel.parenthash))
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

    optparser = OptionParser(usage=usage, version=f"\%prog {VERSION}")

    optparser.add_option(
        "--all",
        dest="show_all",
        action="store_true",
        default=False,
        help="Show all options",
    )

    optparser.add_option(
        "--force",
        dest="force",
        action="store_true",
        default=False,
        help="Ignore safety checks",
    )

    optparser.add_option("-t", "--release-type", dest="release_type",
                         help="release type: release, alpha, beta or rc")

    (options, args) = optparser.parse_args()
    if len(args) < 1:
        optparser.error("Please specify a command")

    command = args[0]

    if command == "help":
        optparser.print_help()
        sys.exit(0)

    repo_path = Path(os.getcwd())

    sandbox = Sandbox(repo_path)

    command_fn = eval("xpd_%s" % command)
    command_fn(sandbox, options, args)

    args = args[1:]


if __name__ == "__main__":
    main()
