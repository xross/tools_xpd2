#!/usr/bin/python
from stat import ST_MODE
from stat import S_IWRITE

from optparse import OptionParser

from typing import List, Dict, Tuple, Union
from pathlib import Path

import os, sys, re
import difflib
import zipfile
import tempfile
import shutil
from copy import copy
from xpd.xpd_data import Repo_, Release_, Version, Dependency
#from xpd.xpd_data_new import Repo_
from xpd.xpd_data import AllSoftwareDescriptor, SoftwareDescriptor
from xpd.xpd_data import DocMap, Doc
from xpd.xpd_data import changelog_str_to_version, normalize_repo_url
from xpd.xpd_dp import init_dp_sources, init_dp_branch, init_dp_backup
import xpd.check_project
import xmlobject
from xpd import templates
import cognidox

import cognidox
from xpd.docholder import DocumentHolder, DHSection, DHDocumentLink
from xmos_logging import log_error, log_warning, log_info, log_debug, configure_logging, print_status_summary
import subprocess
from xmos_subprocess import call, call_get_output, Popen, platform_is_windows
from urllib.error import HTTPError

import github_api.github_api as ghapi
from github_api.github_api import GitHubConnection

from infr_scripts_py.release_to_github import make_release
from pathlib import Path
import glob

class GitHubError(Exception):
    pass

ALLOWED_SCOPES=["Roadmap", "Example", "Early Development", "General Use"]

xdoc = None
xmossphinx = None
xmos_xref = None

def samefile(fileA, fileB):
    try:
        return os.path.samefile(fileA, fileB)
    except AttributeError:
        return os.path.abspath(fileA).lower() == os.path.abspath(fileB).lower()

def confirm(msg, default=False):
    """ Prompt the user and expect as yes/no answer. Return the default
        specified if no input is given, or the response given by the user.
        If no sensible response is found, prompt again.
    """
    while True:
        x = input(msg + " (y/n) [%s]? " % ("y" if default else "n"))
        if not x:
            return default
        if x.upper() in ["N", "NO"]:
            return False
        if x.upper() in ["Y", "YES"]:
            return True

def get_all_dep_versions(repo, ignore_missing=False):
    ''' Get the set of all versions of a repo there are expected in the dependencies.
    '''
    deps = {}
    for dep in repo.get_all_deps(ignore_missing=ignore_missing):
        version = dep.version if dep.version else dep.githash

        name = dep.repo_name
        existing = deps.get(name, set())
        deps[name] = existing | set([version])

    return deps

def get_all_repos_using_dep_version(repo, dep_name, expected):
    repos = set()
    for dep in repo.dependencies:
        repo.assert_exists(dep)
        repos |= get_all_repos_using_dep_version(dep.repo, dep_name, expected)

        if dep.repo_name != dep_name:
            continue

        version = dep.version_str if dep.version_str else dep.githash
        if version != expected:
            continue

        repos.add(repo.name)

    return repos

def get_multiple_version_errors(repo, print_help=True):
    errors = 0
    for (dep_name, expected) in list(get_all_dep_versions(repo).items()):
        if len(expected) != 1:
            dep_list = get_dep_list(repo)
            for depname, dep in dep_list:
                if dep_name == depname:
                    repo.assert_exists(dep)
                    if dep.version_str:
                        expected_release = dep.version_str
                    else:
                        expected_release = dep.githash
                    if dep.repo:
                        if dep.repo.current_release():
                            actual = str(dep.repo.current_release().version)
                        else:
                            actual = dep.repo.current_githash()
                    if dep.version_str and dep.repo.current_release():
                        if expected_release > actual:
                            log_error('%s : %s used by %s' % (dep_name, expected_release, ', '.join(get_all_repos_using_dep_version(repo, dep_name, expected_release))))
                            log_info("ERROR: Instead use actual version %s" %(actual))
                            errors += 1
                    else:
                        expected_date = get_date(dep.repo, dep.githash)
                        actual_date =  get_date(dep.repo, dep.repo.current_githash())
                        if expected_date > actual_date:
                                log_error('%s : %s used by %s' % (dep_name, expected_release, ', '.join(get_all_repos_using_dep_version(repo, dep_name, expected_release))))
                                log_info("ERROR: Latest version not actually used, version currently checked out is %s" % (actual))
                                errors += 1
            expected_list = list(expected)
            count_error = 0
            count_warning = 0
            error_message = ''
            warning_message = ''
            for e in range(len(expected_list)-1):
                point_diff = False
                try:
                    version = Version(version_str=expected_list[e])
                    point_diff = version.equals_excluding_point(Version(version_str=expected_list[e+1]))
                except:
                      pass

                if point_diff:
                    count_warning += 1
                    if e == 0:
                        warning_message += '\n           %s by %s' % (expected_list[e], ', '.join(get_all_repos_using_dep_version(repo, dep_name, expected_list[e])))
                    warning_message += '\n           %s by %s' % (expected_list[e+1], ', '.join(get_all_repos_using_dep_version(repo, dep_name, expected_list[e+1])))
                else:
                     count_error += 1
                     if e == 0:
                         error_message += '\n           %s by %s' % (expected_list[e], ', '.join(get_all_repos_using_dep_version(repo, dep_name, expected_list[e])))
                     error_message += '\n           %s by %s' % (expected_list[e+1], ', '.join(get_all_repos_using_dep_version(repo, dep_name, expected_list[e+1])))

            if count_error > 0:
                log_error("Multiple major or minor versions of %s are used:%s" % (dep_name, error_message))
                errors += 1
                count_error = 0
            elif count_warning > 0:
                log_warning("Multiple point versions of %s are used:%s" % (dep_name, warning_message))
                count_warning = 0

    if errors and print_help:
        log_info("Use 'xpd show_deps' to determine the cause of these multiple versions")

    return errors



def get_deps_repos(repo, strings, indent, prefix):

    strings += "\n" + ("%s%s%s:%s" % (indent, prefix, repo.name, " has no dependencies" if not repo.dependencies else ''))

    for dep in repo.dependencies:
        repo.assert_exists(dep)

        if dep.version:
            actual_version = dep.version
        else:
            actual_version = dep.githash

        required_version = None

        local_mod = ""
        actual = "???"
        if dep.repo:
            rel = dep.repo.current_release()
            if dep.repo.has_local_modifications(is_dependency=True):
                local_mod = "(local modifications)"

        # Show what version of the dep we require
        # TODO this searching is not okay..
        for l in repo.get_libs():
            for d in l.dependencies:
                if d.module_name == dep.repo_name:
                    required_version = d.required_version

        # Show what version of the repo we have
        strings += "\n" + ("%s%s  +- %s %s (required: %s) %s" % (indent, prefix, dep.repo_name, actual_version, required_version, local_mod))

        space = ' '*len(dep.repo.name)
        strings = get_deps_repos(dep.repo, strings, indent, '%s  %s%s' % (prefix, ' ' if dep == repo.dependencies[-1] else '|', space))

    return strings

def xpd_show_deps(repo, options, args):

    log_info("\nDEPENDENCIES (REPOS):\n")

    strings = get_deps_repos(repo, "", '  ', '')

    if not options.github:
        get_multiple_version_errors(repo, print_help=False)

    log_info(strings)

def xpd_dump_deps(repo, options, args):
    outfile = open("deps.txt", 'w')
    outfile.write("\nDEPENDENCIES (REPOS):\n")
    strings = get_deps_repos(repo, "", '  ', '')
    outfile.write(strings)
    outfile.close()

#def find_components(repo, is_update=True):
#    components = repo.get_software_blocks(ignore_xsoftip_excludes=True, is_update=is_update)
#    used_modules = set()
#    for comp in components:
#        used_modules = used_modules | set([dep.module_name for dep in comp.dependencies])
#
#    return components


def find_current_dependencies(repo, is_update=False):
    components = repo.get_software_blocks(is_update=is_update)
    used_modules = set()
    for comp in components:
        used_modules = used_modules | set([dep.module_name for dep in comp.dependencies])

    repos = set([])
    for m in used_modules:
        repo_name = repo.find_repo_containing_module(m)

        # Don't become dependent on self
        if repo_name == repo.name:
            continue

        if repo_name:
            repos.add(repo_name)
        else:
            log_warning("Can't find repo for %s" % m)

    return repos

#def xpd_add_dep(repo, options, args):
#    if len(args) < 1:
#        log_error("required repo name")
#        sys.exit(1)
#
#    return repo.add_dep(args[0])

def get_date(repo, githash):
    try:
        (stdout_lines, stderr_lines) = call_get_output(
             ['git', 'show', '-s', '--pretty=%at', githash], cwd=repo.path)
        date = int(stdout_lines[0])
    except:
        log_warning("%s: Failed to determine date of githash '%s'" % (repo.name, githash))
        date = 0
    return date

def check_dependency_versions(repo, is_rc):

    def cdv_message(message, is_rc):
        if is_rc:
            log_error(message)
            return 1
        else:
            log_warning(message)
            return 0

    errors = 0

    for dep in repo.get_all_deps_once():
        dep_master = Repo_(dep.repo.path, parent=dep.parent, master=True)
        rel = dep_master.current_release()

        if not rel:
            if not repo.get_branched_from_version():
              errors += cdv_message("Dependency '%s' is not on a specified version (found githash %s)" % (
                                    dep_master.name, dep_master.current_version_or_githash()), is_rc)
        elif is_rc and not (rel.version.is_rc() or rel.version.is_full()):
            errors += cdv_message("Dependency '%s' is not an rc or release" % dep_master.name, is_rc)

        # Check whether the repo is publicly visible (commit is not still local)
        (stdout_lines, stderr_lines) = call_get_output(
             ['git', 'log', 'origin/master..master'], cwd=dep_master.path)

        if any([line for line in stdout_lines if dep.githash in line]):
            errors += cdv_message('%s of dependency %s has not been pushed yet' % (
                                    str(dep.version) if dep.version else dep.githash, dep_master.name), is_rc)

    for m in repo.get_modules():
        for d in m.dependencies:
            if not d.version:
                    #TODO check hash?
                    errors += 1
                    log_error("Dependency %s does not meet requirement %s" %(d, d.required_version))
            elif d.repo and not d.required_version.met_by(d.version):
                    errors += 1
                    log_error("Dependency %s does not meet requirement %s" %(d, d.required_version))

    return errors

def xpd_check_deps(repo, options, args, return_current_ok=False, allow_updates=False, is_rc=False, update_uri=False):
    deps = [d.repo_name for d in repo.dependencies]
    repos = find_current_dependencies(repo, is_update=allow_updates)

    current_ok = True
    update = False
    for dep_repo in repos - set(deps):
        if allow_updates:
            repo.add_dep(dep_repo)
            update = True
        else:
            log_warning("Dependency %s is missing" % dep_repo)
            current_ok = False

    for dep_repo in set(deps) - repos:
        if allow_updates:
            repo.remove_dep(dep_repo)
            update = True
        else:
            log_warning("Dependency %s is no longer required" % dep_repo)
            current_ok = False

    for dep in [d for d in repo.dependencies if d.repo]:
        dep_master = Repo_(dep.repo.path, parent=dep.parent, master=True)
        rel = dep_master.current_release()
        if dep.githash != dep_master.current_githash() or \
           (rel and str(dep.version) != str(rel.version)):
            if allow_updates:
                from_date = get_date(dep_master, dep.githash)
                to_date = get_date(dep_master, dep_master.current_githash())

                message = 'Dependency %s: moving from %s to %s' % (dep_master.name,
                                 dep.version_str if dep.version_str else dep.githash,
                                 str(rel.version) if rel else dep_master.current_githash())
                if from_date > to_date:
                    log_warning(message + ' (moving backwards)')
                else:
                    log_info(message)

                dep.githash = dep_master.current_githash()
                if rel:
                    dep.version_str = str(rel.version)
                else:
                    dep.version_str = None
                update = True
            else:
                log_warning("Dependency %s is not up to date" % dep.repo_name)
                current_ok = False

        if update_uri:
          dep.uri = dep_master.uri()

    if not current_ok:
        log_info("Something has gone wrong with deps")

    errors = check_dependency_versions(repo, is_rc=is_rc)
    if errors:
        current_ok = False

    if not allow_updates and not options.github:
        errors = get_multiple_version_errors(repo)
        if errors:
            current_ok = False

    if return_current_ok:
        return current_ok
    else:
        return update

def xpd_list(repo, options, args):
    rels = repo.releases
    rels.sort()
    rels.reverse()

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

def xpd_upgrade_rc(repo, options, args):
    if len(args) < 1:
        log_error("Requires version number.")
        sys.exit(1)

    version = Version(version_str=args[0])

    version.rtype = ''
    version.rnumber = 0

    if repo.get_release(version):
        log_error("Version already exists.")
        sys.exit(1)

    rc = repo.latest_release(release_filter=lambda r: r.version.match_modulo_rtype(version) and r.version.rtype=='rc')

    if not rc:
        log_error("Cannot find rc.")
        sys.exit(1)

    if not confirm("Upgrade %s to %s. Are you sure" % (rc.version, version), default=True):
        return False

    release = copy(rc)
    release.version = version

    repo.releases.append(release)
    repo.save()
    repo.record_release(release)

    ref = repo.current_gitref()

    if ref == "master":
        log_info("xpd data updated. Please commit to complete upgrade of rc.")
        return True

    return False

def branch_candidates(repo):
    candidates = []
    latest = repo.latest_full_release()
    if latest:
        candidates.append(latest)
    latest_pre = repo.latest_pre_release()
    if latest_pre and (not latest or latest_pre > latest):
        candidates.append(latest_pre)
    return candidates

def build_sw(repo, options):
    if options.nobuild:
        log_warning("Skipping build")
        return
    log_info("Building repo sw")
    ret = call(["xmake", "NO_IGNORE_ERRORS=1", "all"], cwd=repo.path, silent=False)
    if ret != 0 and not options.force:
        log_error("Build failed")
        sys.exit(1)
    log_info("Building repo sw ok")

def xpd_build(repo, options, args):

    log_info("Building sw")
    build_sw(repo, options)
    log_info("building docs")
    xpd_build_docs(repo, options, args)

# TODO if a pre-release check this is mentioned in the release notes
def xpd_create_release(repo, options, args):

    #TODO FIXME set github based on repo url
    if options.github:
        errors = False
    else:
        errors = get_multiple_version_errors(repo)


    if errors and not options.force:
        sys.exit(1)

    if repo.is_detached_head():
        log_error("Cannot create release from detached head.")
        sys.exit(1)

    # Do some checks
    local_mod = False
    for r in repo.all_repos():
        if r.has_local_modifications(is_dependency=(False if r == repo else True)):
            log_warning("%s has local modifications" % r)
            local_mod = True

    if local_mod and not options.force:
        log_error("Cannot create release: uncommitted modifications")
        sys.exit(1)

    repo.git_fetch()
    if repo.behind_upstream() and not options.force:
        log_error("Upstream changes not merged in. Cannot create release")
        log_error("Try a 'git pull'")
        sys.exit(1)

    branched_from_version = repo.get_branched_from_version()

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

    notes = repo.changelog_entries
    if not notes and not options.force:
        log_error("No versions found in CHANGELOG.rst, please update file first")
        sys.exit(1)

    (latest_in_changelog, items) = notes[0]

    if hasattr(options, 'release_version') and options.release_version:
        print('release_version: ' + str(options.release_version))
        version = Version(version_str=options.release_version)
    else:
        latest = repo.latest_full_release()
        if latest:
            print(("Latest release: %s" % latest.version))
            latest_version = latest.version
        else:
            print("There is no full release yet")
            latest_version = Version(0, 0, 0, 0)

        print(("    Next major: %s" % latest_version.major_increment()))
        print(("    Next minor: %s" % latest_version.minor_increment()))
        print(("    Next point: %s" % latest_version.point_increment()))

        latest_pre = repo.latest_pre_release()
        if latest_pre and (not latest or latest_pre > latest):
            print(("Latest pre-release: %s" % latest_pre.version))

        version = None
        while True:
            x = input("Enter version number [%s]:" % latest_in_changelog)
            if not x:
                x = latest_in_changelog

            try:
                version = Version(version_str=x)
                break
            except:
                log_error("Invalid version number '%s'" % x)

    print(str(branched_from_version))
    if branched_from_version:
        version.rtype = branched_from_version.rtype
        version.rnumber = branched_from_version.rnumber
        version.branch_name = repo.current_gitbranch()
        version.branch_rtype = rtype
        version.set_branch_rnumber(repo.releases)
    else:
        version.rtype = rtype
        version.set_rnumber(repo.releases)

    if not confirm("Create release %s. Are you sure" % version, default=True):
        return False

    (stdout_lines, stderr_lines) = call_get_output(["git", "tag"], cwd=repo.path)
    for line in stdout_lines + stderr_lines:
              line = line.replace('v','').replace('\n','')
              if str(version) == line:
                  log_error("Cannot create release with this version number - a tagged version is already present in your local repo.")
                  log_error("Do 'git tag -d v<version number>' to delete that tag and try again")
                  sys.exit(1)

    current_ok = xpd_check_deps(repo, options, args, return_current_ok=True, allow_updates=True, is_rc=version.is_rc())

    if not current_ok and not options.force and not options.github:
        log_error("Cannot create release - errors detected with dependencies")
        sys.exit(1)

    xpd_update_changelog(repo, options, args)
    repo.git_add('CHANGELOG.rst')
    repo.git_commit_if_changed("xpd: Patched changelog with dependency changes")

    fstr = version.final_version_str()
    found = False
    changelog_items = []
    release_notes = ""
    for (notes_version, changelog_items) in notes:
        if notes_version == fstr:
            found = True
            print(("RELEASE NOTES FOR %s:" % fstr))
            print("----")
            for item in changelog_items:
                print(item)
                release_notes = release_notes + item
            print("----")
            if not confirm("Are these notes up to date", default=True):
                print("Please update notes and try again")
                return True

    if not found:
        log_error("Cannot find release notes for %s, please update CHANGELOG.rst" % fstr)
        return True

    release = Release_()
    release.version = version
    release.notes = release_notes

    print(release_notes)

    log_info("Running checks")

    xpd_check_all(repo, options, [])

    xpd_check_info(repo, options, args)

    ok = xpd.check_project.check_makefiles(repo)

    if not ok:
        log_error("Updates required to Makefiles.")
        log_error("Update files (or commit automatic changes) and try again.")
        return True

    log_info("Checking xSOFTip block information")
    ok = xpd_check_swblocks(repo, options, args, return_valid=True, validate=True)

    if not ok:
        log_error("---------------------------")
        log_error("Problem with xSOFTip Blocks")
        log_error("Either update README.rst files and metainfo files")
        log_error("... or add a <xsoftip_exclude> element to xpd.xml for the offending dir")
        return True

    repo.git_commit_if_changed("xpd: Updated build/project files")

    patched_files = repo.patch_version_defines(version)
    if patched_files:
        log_info("Adding patched files:")
        for f in patched_files:
            log_info("  %s" % f)
            repo.git_add(f)
        repo.git_commit_if_changed("xpd: Patched version number")

    modified_files = r.get_local_modifications(unstaged_only=True)
    if modified_files:
        log_info("Adding files with whitespace changes:")
        for f in modified_files:
            log_info("  %s" % f)
            repo.git_add(f)
        repo.git_commit_if_changed("xpd: Cleaned up whitespace")

    log_info("Creating sandbox and checking build")
    repo.move_to_temp_sandbox()
    build_sw(repo, options)
    repo.delete_temp_sandbox()

    release.parenthash = repo.current_githash()

    repo.releases.append(release)

    log_info("Created release %s" % str(release.version))

    xpd_update_readme(repo, options, [], xmos_package=repo.is_xmos_repo(), new_release=release)
    repo.git_add('README.rst')

    # Build docs must happen after readme update
    # TODO this should in in a temp sandbox?
    xpd_build_docs(repo, options, args)

    repo.commit_release(release)

    release.githash = repo.get_child_hash(release.parenthash)

    repo.git_tag(str(version))

    if confirm("Do you want to push the commit of this release upstream", default=True):
        repo.git_push()

        xpd_create_github_release(repo, options, args, release = release)

    return False

def xpd_find_assets(repo, options, args, release=None):

    assets = []

    if "github" not in repo.location:
        log_error(f"Can only upload assets to github repos ({repo.location})")
        exit(1)

    if not options.nodocs:

        # Find build pdf in all doc dirs
        for docdir in repo.docdirs:
            docdir = os.path.join(docdir, "pdf")

            if not os.path.exists(os.path.join(repo.path, docdir)):
                log_error("%s: docdir '%s' does not exist. Are docs built?" % (repo.path, docdir))
                exit(1)
                break

            pdf_files = glob.glob(os.path.join(repo.path, docdir, "*.pdf"))

            for p in pdf_files:
                assets.append(Path(p))
                log_info(f'Found doc asset: {p}')

    # For sw_ repos upload a zip
    if repo.name.startswith("sw_"):

        release = repo.current_release()
        if release:
            version_string = str(release.version)
        else:
            log_error("Repository not at specific version point in git. Cannot publish.")
            sys.exit(1)

        zip_name = repo.name + "_" + version_string + ".zip"
        zip_path = Path(os.path.join(repo.path, zip_name))

        assets.append(zip_path)

        if not os.path.exists(zip_path):
            log_error(f'Cannot find zip asset: {zip_name}')
            sys.exit(1)
        else:
            log_info(f'Found zip asset: {zip_name}')

    return assets

def xpd_create_github_release(repo, options, args, dest=None, release=None):

    if not release:
        release = repo.current_release()
        if not release:
            log_error("Repository not at specific version point in git. Cannot publish.")
            sys.exit(1)

    version_str=str(release.version)

    log_info(f"Creating github release for {version_str}")

    log_info(f"Creating zip file")
    xpd_make_zip(repo, options, args)

    assets = xpd_find_assets(repo, options, args, release)

    make_release(None, "github.com", repo.github_user, repo.name, str(release.version), "".join(release.notes), None, assets, None)

def do_exports(repo):
    for export in repo.exports:
        log_info("Exporting %s" % export)
        call(["xmake", "export"], cwd=os.path.join(repo.path, export), silent=True)
    return repo.exports

def xpd_make_zip(repo, options, args, dest=None):
    # Do some checks
    alternate_name = False

    local_mod = False
    for r in repo.all_repos():
        if r and r.has_local_modifications(is_dependency=(False if r == repo else True)):
            log_warning("%s has local modifications" % r)
            local_mod = True

    if local_mod and not options.force:
        log_error("Cannot make zip: uncommitted modifications")
        sys.exit(1)

    current_ok = xpd_check_deps(repo, options, args, return_current_ok=True, allow_updates=False)

    if not current_ok:
        log_warning("Current dependency versions do not match meta-data")
        alternate_name = True

    release = repo.current_release()
    if release:
        version_string = str(release.version)
    else:
        if options.upload:
            log_error("Repository not at specific version point in git. Cannot publish.")
            sys.exit(1)
        version_string = repo.current_githash()[:8]

    if alternate_name and not dest:
        version_string = eval(input("Please give a name for this snapshot: "))

    name = repo.name + "_" + version_string

    update = False

    log_info("Creating temporary sandbox")
    repo.move_to_temp_sandbox()
    if repo.include_binaries:
        build_sw(repo, options)

    xpd_check_infr(repo, options, args)

    xpd_build_docs(repo, options)

    exports = []
    exports += do_exports(repo)
    for dep in repo.get_all_deps_once():
        exports += do_exports(dep.repo)

    for component in repo.components:
        component.local = "false"

    if dest:
        fname = dest
    else:
        fname = name + ".zip"

    log_info("Creating %s" % fname)

    f = zipfile.ZipFile(fname, "w")

    zip_repo(repo, f, exports, include_binaries=repo.include_binaries, force=options.force)

    for dep in repo.get_all_deps_once():
        zip_repo(dep.repo, f, exports, force=options.force, no_app_projects=True)

    if not options.nodocs:
        for docdir in repo.docdirs:
            insert_doc(repo.name, os.path.join(repo.path, docdir), f, is_xmos_repo=repo.is_xmos_repo(),
                   repo=repo, base=docdir)

        for block in repo.components:
            src = os.path.join(repo.path, block.path, '_build', 'text', 'README.txt')
            if not os.path.isfile(src):
                log_warning("repo %s vendor is not XMOS and does not come from github" % repo.path)
                log_warning("so there will be no README.txt for block %s" % block.path)
            else:
                arcname = os.path.join(repo.name, block.path, 'README.txt')
                f.write(src, arcname=arcname)
        #FIXME
        #if not options.github:
        #    insert_topdoc(repo, f)

        '''
        xref = xmos_xref.XRefInfo('xpd')

        for dep in repo.get_all_deps_once():
            if dep.repo.subpartnumber and dep.repo.is_xmos_repo():
                if not dep.repo.current_release():
                    log_warning("Dependency %s is not on a released version." % dep.repo.name)
                    continue

                version = dep.repo.current_version_or_githash()
                log_info("Trying to find version %s of %s in cognidox" % (version, dep.repo.name))
                m = re.match('(.*)(rc|beta|alpha)\d*$', version)
                if m:
                    version = m.groups(0)[0]
                try:
                    cogfile = cognidox.fetch_version(dep.repo.subpartnumber, version)
                except:
                    log_warning("Cannot connect to cognidox")
                    cogfile = None

                if cogfile:
                    tmpfile = tempfile.TemporaryFile()
                    tmpfile.write(cogfile.read())
                    insert_dep_docs_to_zip(f, tmpfile, dep.repo.name)
                    for docdir in dep.repo.docdirs:
                        docdir = os.path.join(dep.repo.path, docdir)
                        docinfo = xref.get_or_create_docinfo_from_dir(docdir,
                                                                      topdir = dep.repo.name)
                        swlink = docinfo.get_swlink(repo.partnumber)
                        base = os.path.basename(docdir)
                        if base == 'doc':
                            base = dep.repo.name
                        swlink.path = '%s/doc/%s' % (dep.repo.name, base)
                        swlink.version = repo.current_version_or_githash()
                        swlink.subversion = dep.repo.current_version_or_githash()
                        swlink.title = repo.longname
                        swlink.repo_name = dep.repo.name
                        swlink.primary = "False"
                        swlink.subpartnumber = dep.repo.subpartnumber

                    cogfile.close()
                    tmpfile.close()
                else:
                    log_warning("Cannot find relevant version of %s is cognidox. DEPENDENCIES SHOULD BE OFF RELEASED VERSIONS OF COMPONENTS" % dep.repo.name)
        '''

    info_string = "<zipinfo>\n"
    info_string += "   <main>%s</main>\n" % repo.name
    if not alternate_name:
        info_string += "   <version>%s</version>\n" % version_string
    info_string += "</zipinfo>"

    f.writestr('.zipinfo', info_string)

    dep_info = get_deps_repos(repo, "", '  ', '')
    f.writestr('/deps.txt', dep_info)

    f.close()
    log_info("Created %s" % fname)

    if repo.snippets:
        log_info("Creating individual swblock zipfiles")
        zips_path = os.path.join(repo.path, "swblock_zips")
        log_info(zips_path)
        if not os.path.exists(zips_path):
            os.makedirs(zips_path)
        swblock_zips = {}
        swblock_zip_paths = {}
        for block in repo.components:
            swblock_zip_paths[block.id] = os.path.join(zips_path, block.id + ".zip")
            swblock_zips[block.id] = \
                zipfile.ZipFile(os.path.join(zips_path, block.id + ".zip"), "w")

        f = zipfile.ZipFile(fname, "r")
        for name in f.namelist():
            m = re.match("[^/]*/([^/]*)/(.*)$".replace('/', re.escape(os.path.sep)), name)
            if not m:
                continue
            id = m.groups(0)[0]
            rest = m.groups(0)[1]
            if not id in swblock_zips:
                continue
            block_zip = swblock_zips[id]
            path = "%s/%s" % (id, rest)
            block_zip.writestr(path, f.open(name).read())
        f.close()
        for block in repo.components:
            swblock_zips[block.id].close()
            if options.upload:
                docinfo = xref.get_or_create_docinfo(os.path.join(repo.name, block.path, "zip"))
                partnum = docinfo.partnum
                if not partnum:
                    partnum = cognidox.query_and_create_document('/Projects/Tools',
                                                   default_title=block.id,
                                                   doctype='SM',
                                                   auto_create=True)
                    docinfo.partnum = partnum
                    xref.update()

                if not block.zip_partnumber:
                    update = True

                block.zip_partnumber = partnum
                version = cognidox.get_next_doc_version_tag(partnum, version_string)
                cognidox.doCognidoxCheckIn(partnum,
                                   swblock_zip_paths[block.id],
                                   version = version,
                                   draft=False)
                if repo.licence_is_general():
                    cognidox.assign_license(partnum, 'General Public', comment="Assigned by xpd")
                    cognidox.assign_license_agreement(partnum, "End User Licence Agreement", comment="Assigned by xpd")

        if options.upload:
            f = open(os.path.join(repo.path, "docmap.xml"), 'wb')
            f.write(xpd_make_docmap(repo, [], [], return_str = True))
            f.close()

            docinfo = xref.get_or_create_docinfo(os.path.join(repo.name, block.path, "docmap"))
            partnum = docinfo.partnum
            if not partnum:
                partnum = cognidox.query_and_create_document('/Projects/Tools',
                                                   default_title="%s document info" % repo.name,
                                                   doctype='UN',
                                                   auto_create=True)
                docinfo.partnum = partnum
                xref.update()

            if not repo.docmap_partnumber:
                update = True

            repo.docmap_partnumber = partnum
            version = cognidox.get_next_doc_version_tag(partnum, version_string)
            cognidox.doCognidoxCheckIn(partnum,
                                       os.path.join(repo.path, "docmap.xml"),
                                       version = version,
                                       draft=False)

    #if options.upload:
    # FIXME
    if False:
        log_info("Uploading zip file to cognidox part number %s" % repo.subpartnumber)
        m = re.match('(.*)rc(\d+)$', version_string)
        if m:
            zip_vstr = m.groups(0)[0]
        else:
            zip_vstr = version_string
        cognidox.doCognidoxCheckIn(repo.subpartnumber,
                                   fname,
                                   version=zip_vstr,
                                   draft=False)
        if repo.licence_is_general():
            log_info("Assigning Licence Info")
            cognidox.assign_license(repo.subpartnumber, 'General Public', comment="Assigned by xpd")
            cognidox.assign_license_agreement(repo.subpartnumber, "End User Licence Agreement", comment="Assigned by xpd")
        else:
            log_info("Restricted Licence: not assigning licence info")

        log_info("Creating document holder")
        xpd_make_docholder(repo, options, args, to_file=".docholder.xml")
        log_info("Uploading document holder")
        cognidox.doCognidoxCheckIn(repo.partnumber,
                                   ".docholder.xml",
                                   version=version_string,
                                   draft=True)
        os.remove(".docholder.xml")

    log_info("Tidying up")

    repo.delete_temp_sandbox()

    if os.path.exists(os.path.join(repo.path, '_build')):
        shutil.rmtree(os.path.join(repo.path, '_build'))
    #if not options.nodocs:
    #    xref.update()

    return update

def find_files(path):
    fs = []
    for root, dirs, files in os.walk(path):
        for f in files:
            fs.append(os.path.relpath(os.path.join(root, f), path))

    return fs

def zip_repo(repo, zipfile, exports, include_binaries=False, force=False, no_app_projects=False):

    log_info(f'zip_repo({str(repo)})')

    repo_files = find_files(repo.path)
    excludes = []

    # Exclude docs from release zips
    for docdir in repo.docdirs:
        excludes.append(docdir + re.escape(os.path.sep) + '*')

    excludes.append('Jenkinsfile')
    excludes.append('*_build' + re.escape(os.path.sep) + '*')
    excludes.append('__*')
    excludes.append('*app_description')
    excludes.append('*module_description')
    excludes.append('.zipinfo')
    excludes.append('requirements.txt')
    excludes.append('*.DS_Store')
    excludes.append('*issue.zip')
    excludes.append('*.build_*')
    excludes.append('*.build' + re.escape(os.path.sep) + '*')
    excludes.append('*tests' + re.escape(os.path.sep) + '*')
    excludes.append('input_doc_map.xml')
    excludes.append('*' + re.escape(os.path.sep) + '__*')

    # When exporting git info do not exclude readme rst files - otherwise git status will not be clean
    # TODO FIXME Since we are not currently rendering readme files then include RST files for now in all cases
    if False and not repo.git_export:
        for component in repo.components:
            excludes.append('*' + component.path + re.escape(os.path.sep) + 'README.rst')

    #if xpd.check_project.flat_projects:
    #    excludes.append('.cproject')
    #    excludes.append('.project')

    for f in repo_files:
        f = f.rstrip()
        ok = True

        for export in exports:
            # Need to test against the export with trailing separator to prevent
            # modules that are simply longer folder names being affected
            # (e.g. module_usbhost and module_usbhost_epmanager)
            i = export + os.path.sep
            if not re.match('.*\.project|.*\.cproject|.*\.xproject|.*\.makefile', f):
                if os.path.commonprefix([f, i]) == i:
                    ok = False

        # Ignore all git files for now
        if re.match(".*\.git", f):
            ok = False

        # If we are exporting git allow through .gitignore
        if repo.git_export and re.match(".*\.gitignore", f):
            ok = True

        for pattern in excludes:
            pattern = pattern.replace(".", "\.")
            pattern = pattern.replace("*", ".*")
            pattern = pattern + "$"
            if re.match(pattern, f):
                ok = False

        if no_app_projects:
            if re.match('app_.*', f):
               ok = False

        if ok and f != "xpd.xml":
            arcname = os.path.join(repo.name, f)

            if re.match('.*Makefile$', f):
                if os.path.exists(os.path.join(repo.path, f)):
                    fh = open(os.path.join(repo.path, f))
                    makefile_str = fh.read()
                    fh.close()
                    makefile_str = xpd.check_project.patch_makefile(makefile_str)
                    zipfile.writestr(arcname, makefile_str)
            elif re.match('(.*)' + re.escape(os.path.sep) + '\.xproject', f):
                m = re.match('(.*)' + re.escape(os.path.sep) + '\.xproject', f)
                dirname = os.path.basename(m.groups(0)[0])
                lines = open(os.path.join(repo.path, f)).readlines()
                new_xproject = ''.join(lines)
                for comp in repo.components:
                    if comp.id == dirname:
                        if comp.docPartNumber:
                            xml = "\n<docPartNumber>%s</docPartNumber>\n" % comp.docPartNumber
                            xml += "<docVersion>%s</docVersion>\n" % comp.docVersion
                            new_xproject = new_xproject.replace("<xproject>",
                                                                "<xproject>" + xml)
                zipfile.writestr(arcname, new_xproject)
            elif f == 'README.rst':
                lines = xpd_update_readme(repo, [], [],
                                          write_back=False,
                                          xmos_package=repo.is_xmos_repo(),
                                          use_current_version=True)
                new_readme = ''.join(lines)
                zipfile.writestr(arcname, new_readme)
            else:
                try:
                    zipfile.write(os.path.join(repo.path, f), arcname=arcname)
                except:
                    pass

    for export in exports:
        export_path = os.path.join(repo.path, export)
        export_path = os.path.join(export_path, "export")
        for root, dirs, files in os.walk(export_path):
            for f in files:
                fullpath = os.path.join(root, f)
                arcname = os.path.relpath(fullpath, export_path)
                arcname = os.path.join(repo.name, arcname)

                zipfile.write(fullpath, arcname=arcname)

    if repo.git_export:
        log_info("exporting git")
        for root, dirs, files in os.walk(os.path.join(repo.path, ".git")):
            for f in files:
                fullpath = os.path.join(root, f)
                arcname = os.path.join(repo.name, os.path.relpath(root, repo.path))
                arcname = os.path.join(arcname, f)
                zipfile.write(fullpath, arcname=arcname)

    #if repo.partnumber and repo.current_release():
    #    publishinfo = \
#"""<publishinfo>
#    <partnum>%s</partnum>
#    <version>%s</version>
#</publishinfo>
#""" % (repo.partnumber, str(repo.current_release().version))
#        zipfile.writestr(os.path.join(repo.name, ".publishinfo"), publishinfo)

#    xpd_dom = repo.todom("xpd")

    '''
    if not repo.git_export:
        # Explicitly add version
        rootelem = xpd_dom.getElementsByTagName("xpd")[0]
        elem = xpd_dom.createElement("version")
        rel = repo.current_release()
        if rel:
            rel = str(rel.version)
        else:
            rel = str(repo.current_githash())
        text = xpd_dom.createTextNode(rel)
        elem.appendChild(text)
        rootelem.appendChild(elem)

    if options.github:
        comp_elems = xpd_dom.getElementsByTagName("component")
        for comp in comp_elems:
            comp.setAttribute("scope", "Open Source")
            comp.setAttribute("type", "communityCode")

    rootelem = xpd_dom.getElementsByTagName("xpd")[0]
    xpd_str = '<?xml version=\"1.0\" ?>\n' + xmlobject.pp_xml(xpd_dom, rootelem).strip()

    zipfile.writestr(os.path.join(repo.name, "xpd.xml"), xpd_str)
    '''

    if include_binaries:
        for root, dirs, files in os.walk(os.path.join(repo.path)):
            for f in files:
                if re.match('.*\.xe$', f):
                    fullpath = os.path.join(root, f)
                    arcname = os.path.relpath(root, repo.path)
                    arcname = os.path.join(repo.name, arcname)
                    arcname = os.path.join(arcname, f)
                    zipfile.write(fullpath, arcname=arcname)

def insert_dep_docs_to_zip(main_zipfile, sub_zipfile, repo_name):
    log_info("Extracting docs from %s zipfile" % repo_name)
    dep_zip = zipfile.ZipFile(sub_zipfile, mode='r')
    existing = main_zipfile.namelist()
    for name in dep_zip.namelist():
        m = re.match(repo_name + re.escape(os.path.sep) + 'doc' + re.escape(os.path.sep) + '.*', name)
        if m or name == repo_name + os.path.sep + 'README.html':
            zfile = dep_zip.open(name)
            s = zfile.read()
            zfile.close()
            if not name in existing:
                main_zipfile.writestr(name, s)
    dep_zip.close()

def insert_topdoc(repo, zipfile):
    if repo.is_xmos_repo():
        htmlpath='xdehtml'
    else:
        htmlpath='html'

    htmlpath = os.path.join(repo.topdoc_path, '_build', htmlpath)
    zipdocpath = os.path.join(repo.name, 'doc')
    fs = find_files(htmlpath)
    for f in fs:
        if not re.match('sphinx.output|\.doctree.*|objects.inv|.buildinfo', f):
            src = os.path.join(htmlpath, f)
            dst = os.path.join(zipdocpath, f)
            dst = dst.replace('_static', '.static')
            if re.match('[^' + re.escape(os.path.sep) + ']*.html', f):
                index_str = open(src).read()
                index_str = index_str.replace('_static', '.static')
                if f == 'index.html':
                    rel = repo.current_release()
                    if repo.is_xmos_repo() and repo.subpartnumber and rel:
                        xde_comment = '\n<!--XDE partnum="%s" version="%s"-->\n' % (repo.subpartnumber, str(rel.version))
                        index_str = index_str.replace('<html', '%s<html' % xde_comment)

                zipfile.writestr(dst, index_str)

                readme = ''.join(open(src).readlines())
                readme = readme.replace('"_static', '"doc' + os.path.sep + '.static')
                readme = readme.replace('"././', '"doc/')
                if f == 'index.html':
                    zipfile.writestr(os.path.join(repo.name, 'README.html'), readme)
                else:
                    zipfile.writestr(os.path.join(repo.name, f), readme)
            else:
                zipfile.write(src, arcname=dst)

def insert_doc(repo_name, path, zipfile, base=None, insert_pdf=True,
               is_xmos_repo=True, repo=None):

    #FIXME
    return

    import_xdoc()
    config = xdoc.get_config(path)
    pdfname = config['SPHINX_MASTER_DOC'] + '.pdf'

    pdfpath = os.path.join(path, '_build', 'xlatex', pdfname)
    if not base:
        base = os.path.basename(path)
        if base == 'doc':
            base = repo_name

    if base == '':
        base = repo_name
    arcpdfname = base + '.pdf'
    zipdocpath = os.path.join(repo_name, 'doc', base)
    if insert_pdf:
        zipfile.write(pdfpath, arcname=os.path.join(repo_name, 'doc', arcpdfname))
    if is_xmos_repo:
        htmlpath=os.path.join(path, '_build', 'xdehtml')
    else:
        htmlpath=os.path.join(path, '_build', 'html')

    fs = find_files(htmlpath)

    for f in fs:
        if not re.match('sphinx.output|\.doctree.*|.buildinfo|objects.inv', f):
            src = os.path.join(htmlpath, f)
            dst = os.path.join(zipdocpath, f)
            x = open(src)
            src_str = x.read()
            x.close()
            src_str = src_str.replace('_static', '.static')
            dst = dst.replace('_static', '.static')
            zipfile.writestr(dst, src_str)

def xpd_status(repo, options, args):
    rel = repo.current_release()
    if rel:
        version = str(rel.version)
    else:
        version = str(repo.current_githash())

    log_info("INFO:\n")
    log_info("              Name: %s" % repo.longname)
    log_info("           Version: %s" % version)
    log_info("          Location: %s" % repo.location)
    log_info("       Description: %s" % repo.description)
    log_info("       Maintainers: %s" % repo.maintainers)

    if repo.git_export != None:
        log_info("   Export git info: %s" % repo.git_export)

    if repo.docdirs != []:
        log_info("     Documentation: %s" % repo.docdirs[0])
        for doc in repo.docdirs[1:]:
            log_info("                    %s" % doc)

    log_info("\nSOFTWARE BLOCKS\n")

    log_info("Apps:\n")

    def print_software_block_details(swblock):
        print((swblock.name))
        if not swblock.has_readme():
            log_warning("Missing README.rst")
        log_info("       Name: %s" % swblock.name)
        log_info("      Scope: %s" % swblock.scope)
        log_info("Description: %s" % swblock.description)
        log_info("   Keywords: %s" % ','.join(swblock.keywords))
        log_info("  Published: %s" % swblock.is_published())
        log_info("       Deps:")
        for d in swblock.dependencies:
            if d.required_version:
                log_info("             %s (required: %s)" % (d.module_name, d.required_version))
            else:
                log_info("             %s" % d.module_name)
        log_info("")

    for app in repo.get_apps():
        print_software_block_details(app)

    log_info("\nLibraries:\n")

    for module in repo.get_modules():
        print_software_block_details(module)

    xpd_show_deps(repo, options, args)

    if repo.exports != []:
        log_info("\nEXPORTS:\n")
        for export in repo.exports:
            log_info("     %s" % export)

def remove_indent(xs):
    return [re.match(' *(.*)', x).groups(0)[0] for x in xs]

def add_indent(n, xs):
    indent = ''.join([' ' for x in range(n)])
    return [indent + s for s in xs]

def rst_make_title(title, ch):
    underline = ''.join([ch for x in title])
    return [title, underline, '']

def xpd_update_readme(repo, options, args,
                      xmos_package=True, write_back=True,
                      use_current_version=False, doclinks=False, new_release=None):
    """ Updates the README.rst and returns the contents.
    """
    log_info("Updating README in " + repo.name)

    try:
        with open(os.path.join(repo.path, 'README.rst')) as f:
            lines = f.readlines()
    except IOError:
        log_error("%s: Missing top-level README.rst (run 'xpd init' to create a default one)" % repo.name)
        return []

    remove_items = ['Latest release', 'Stable release', 'Maintainer', 'Description', 'Status', 'Required packages', 'Vendor', 'Version']

    remove_sections = ['Required Modules', 'Required Repositories', 'Required software (dependencies)','Required Software (dependencies)']
    if xmos_package:
        remove_sections += ['Support', 'Documentation']

    delete_until_next_section = False
    found_sections = 0
    section_indices = {}
    for i in range(len(lines)):
        line = lines[i]

        if xmos_package:
            line = line.replace('XCORE.com', 'XMOS')

        m = re.match(r':(.*): (.*)', line)
        if m:
            key = m.groups(0)[0]
            if key.upper() in [x.upper() for x in remove_items]:
                line = '-DELETED-\n'

        if xmos_package:
            if re.match(r'.*[D|d]ocumentation can be found.*', line):
                line = '-DELETED-\n'

        if i < len(lines)-1:
            m = re.match(xpd.check_project.rst_title_regexp, lines[i+1])
        else:
            m = None

        if m:
            found_sections += 1
            delete_until_next_section = False
            if line.strip().upper() in [x.upper() for x in remove_sections]:
                delete_until_next_section = True
            section_indices[found_sections] = i+1

        if delete_until_next_section:
            line = '-DELETED-\n'

        lines[i] = line

    if len(section_indices) < 1:
        return []

    heading = lines[:section_indices[1]+1]
    if 2 in section_indices:
        prologue = lines[section_indices[1]+1:section_indices[2]-1]
        lines = lines[section_indices[2]-1:]
    else:
        prologue = []
        lines = lines[section_indices[1]+1:]

    lines = [x for x in lines if x != '-DELETED-\n']

    new_header = "\n"

    version_string = None

    # Updating readme to a release we're creating but not commited yet
    if new_release:
        rel = new_release
    else:
        rel = repo.current_release()
        print(f"current_release: {rel}")

    if rel:
        version_string = str(rel.version)
    else:
        version_string = repo.current_githash()

    #if version_string and use_current_version:
    #    new_header += ":Version: %s\n" % version_string
    #elif repo.latest_release():
    #    new_header += ":Latest release: %s\n" % repo.latest_release().version

    # This seems more sensible than the above logic?
    if version_string:
        new_header += ":Version: %s\n" % version_string
    if version_string != str(repo.latest_release().version):
        new_header += ":Latest release: %s" % repo.latest_release().version

    if xmos_package and repo.vendor:
        new_header += ":Vendor: %s\n" % repo.vendor
    if not xmos_package and repo.maintainer:
        new_header += ":Maintainer: %s\n" % repo.maintainer

    if repo.description:
        desc = repo.description.split('\n')
        new_header += ':Description: %s\n' % desc[0]
        for x in desc[1:]:
            new_header += '  %s' % x

    lines += ['\n', 'Required Software (dependencies)\n', '================================\n', '\n']

    if repo.dependencies == []:
        lines += ['  * None\n']
    else:
        for dep in repo.get_all_deps_once():
            if not dep.repo:
                continue

            if dep.repo.name == 'xcommon':
                lines += ['  * xcommon (if using development tools earlier than 11.11.0)\n']
            else:
                # Always giving uri seems more useful now everything on github?
                # if xmos_package or not dep.uri:
                if not dep.uri:
                    lines += ['  * %s\n' % dep.repo.name]
                else:
                    lines += ['  * %s (%s)\n' % (dep.repo.name, normalize_repo_url(dep.uri))]
    lines += ['\n']

    doc_header = ''
    if xmos_package:
        if repo.docdirs:
            if doclinks:
                import_xdoc()
                doc_header += '\n\nSoftware Blocks\n===============\n\n\n'
                components = sorted(repo.components, key=lambda x:x.id)
                for comp in components:
                    doc_header += '%s (%s)\n %s\n' % (comp.name, comp.id, comp.description)

                doc_header += '\n\nDocumentation\n===============\n\n\n'
                for docdir in repo.docdirs:
                    title = xdoc.get_title(os.path.join(repo.path, docdir))
                    base = docdir
                    if base == '':
                        base = repo.name
                    doc_header += '  * `%s <././%s/index.html>`_' % (title, base)
                    doc_header += ' `PDF <././%s.pdf>`_ \n' % (base)

                doc_header += '  * `Release Notes <././changelog.html>`_\n'
                doc_header += '\n\n'
            else:
                lines += ['Documentation\n', '=============\n', '\n',
                          'You can find the documentation for this software in the /doc directory of the package.\n\n']

        support = ['Support\n', '=======\n', '\n', 'This package is supported by XMOS Ltd. Issues can be raised against the software at: http://www.xmos.com/support\n']

        lines += support

    new_header = new_header.rstrip()
    new_header = [x + '\n' for x in new_header.split('\n')]
    doc_header = [x + '\n' for x in doc_header.split('\n')]

    prologue[0] = '-DELETED-\n' #hack
    lines = heading + new_header + prologue + doc_header + lines

    for i in range(len(lines)-1):
        if lines[i] == '\n' and lines[i+1] == '\n':
            lines[i] = '-DELETED-\n'

    lines = [x for x in lines if x != '-DELETED-\n']

    if write_back:
        with open(os.path.join(repo.path, "README.rst"), 'w') as f:
            for line in lines:
                f.write(line)

    return lines

def check_swblock(repo, options, args, comp, verbose=True):
    valid = True
    if verbose:
        log_info(comp.id)
        log_info("   Name: %s" % comp.name)
        log_info("   Type: %s" % comp.type)
        log_info("   Dependencies:")
        for d in comp.dependencies:
            log_info("      "+str(d))
        log_info("")

    if not comp.has_readme():
        log_error("Software block %s has no README.rst" % comp.path)
        valid = False
        log_info("Creating and adding new template %s" % comp.readme_path())
        f = open(comp.readme_path(), 'wb')
        f.write(templates.swblock_readme)
        f.close()
        repo.git_add(comp.readme_path())
    else:
        if comp.name=='' or comp.name[0] == '<':
           log_error("Software block %s title not specified, update README.rst" % comp.path)
           valid = False
        if comp.description[0]=='<' or re.match('Software Block:', comp.description):
           log_error("Software block %s description not specified, update README.rst" % comp.path)
           valid = False

        if comp.scope not in ALLOWED_SCOPES:
           log_error("Software block %s invalid scope: (%s)" % (comp.path, comp.scope))
           log_info("Update README to set scope to one of:")
           for scope in ALLOWED_SCOPES:
               log_info("         " + scope)
           log_info("")
           valid = False

        if comp.type == "component" and not comp.metainfo_path and comp.scope != "Example":

           if comp.scope == "Roadmap":
               log_error("Roadmap software block %s must have metainfo" % comp.path)
           else:
               log_error("Software block %s without metainfo must have scope 'Example'" % comp.path)
           valid = False

        if comp.keywords_text and comp.keywords_text[0]=='<':
           log_error("%s keywords field as template, update README.rst to specify keywords or delete the line" % comp.path)
           valid = False

        if comp.boards_text and comp.boards_text[0]=='<':
           log_error("%s boards field as template, update README.rst to specify keywords or delete the line" % comp.path)
           valid = False

        comp.local = "false"

        if repo.snippets and not comp.description.startswith("How to"):
           log_error("%s snippet example title should start with 'How to'" % comp.path)
           valid = False

    return valid

def find(f, xs):
        for x in xs:
            if f(x):
                return x


def xpd_check_swblocks(repo, options, args, return_valid=False, verbose=True, validate=False):
    valid = True
    def find(f, xs):
        for x in xs:
            if f(x):
                return x

    current_blocks = repo.components
    actual_blocks = repo.get_software_blocks()
    for comp in repo.components:
        if not find(lambda x: x.id == comp.id, actual_blocks):
            log_info("Removing old swblock: " + comp.id)

    repo.components = actual_blocks

    deps = repo.get_project_deps()

    to_remove = set()
    for comp in repo.components:
        if comp.id in deps:
            comp.dependencies = deps[comp.id][1]
        comp_valid = check_swblock(repo, options, args, comp, verbose=verbose)
        if not comp_valid:
            to_remove.add(comp)
            valid = False

    for comp in to_remove:
        repo.components.remove(comp)

    #if repo.no_xsoftip:
    #    repo.components = []

    if validate:
        log_info("Running validate script on all swblocks")
        ret = xpd_validate_swblock(repo, options, ["all"], return_valid=True)
        valid = valid and ret

    if return_valid:
        return valid

    return True

def xpd_gen_readme(repo, options, args):
    sep = '.. seperator'
    latest = repo.latest_release(release_filter=lambda r: r.version.rtype=='rc')
    if latest:
        full_version = latest.version
        full_version.rtype=''
    header = ['.. class:: announce instapaper_body rst wikistyle readme.rst', '']

    header.extend(rst_make_title(repo.longname, '.'))

    if repo.description:
        header.extend(remove_indent(repo.description.split('\n')) + [''])

    if repo.vendor:
        header.extend([':Vendor: %s' % repo.vendor, ''])

    if repo.maintainer:
        header.extend([':Maintainer: %s' % repo.maintainer, ''])

    if latest:
        header.extend([':Cur. Release: %(ver)s' % {'ver':full_version}, ''])

    if repo.keywords and repo.keywords != []:
        keywords_str = ', '.join(repo.keywords)
        header.extend([':Keywords: %s' % keywords_str, ''])

    release_details = []
    if latest:
        release_title = 'Current Release: %s' % full_version

        release_details.extend(rst_make_title(release_title, '='))
        release_details.extend([':RC: %d'%latest.version.rnumber, '', sep, ''])

        rnotes = repo.get_release_notes(full_version)

        if not rnotes:
            notes = 'No release notes'
        else:
            notes = rnotes.wholeText

        release_details.extend([':Release Notes:', ''])
        release_details.extend(add_indent(1, remove_indent(notes.split('\n')) + ['']))
        release_details.extend([sep, ''])
        ## use cases

        for uc in repo.usecases:
            if uc.usecase_type == 'invalid':
                release_details.extend([':Invalid:', ''])
            else:
                release_details.extend([':Use Case:', ''])

            usecase_details = []
            usecase_title = '**'+uc.name
            if uc.usecase_type == 'general':
                usecase_title += " - Suitable for general purpose usage"
            elif uc.usecase_type == 'development':
                usecase_title += " - Suitable for development usage"
            usecase_title += '**'
            usecase_details.append(usecase_title)
            usecase_details.append('')

            if uc.toolchain and uc.toolchain.tools and uc.toolchain.tools != []:
                usecase_details.extend(['** Compatible Tools **', ''])
                usecase_details.extend([', '.join(uc.toolchain.tools), ''])

            if uc.devices and uc.devices.devices and uc.devices.devices != []:
                usecase_details.extend(['** Compatible Devices **', ''])
                usecase_details.extend([', '.join(uc.devices.devices), ''])

            release_details.extend(add_indent(4, usecase_details))

    changelog = []

    if repo.changelog != []:
        changelog = rst_make_title('Release History', '=')

        for x in sorted(repo.changelog):
            changelog.extend([':%s:'%x.version_str, ''])

            log = x.wholeText.rstrip().split('\n')

            changelog.extend(log+[''])

    log_info('\n'.join(header))
    log_info('\n'.join(release_details))
    log_info('\n'.join(changelog))

def xpd_checkout(repo, options, args):
  if not args:
    log_error("Please specify a version to checkout (use 'xpd list' to get available versions)")
    return False

  version_name = args[0]
  repo.checkout(version_name)
  return False

def xpd_get_deps(repo, options, args):
  if len(args) == 0:
    version_name = 'master'
  elif len(args) == 1:
    version_name = args[0]
  else:
    log_error("xpd get_deps [version]")
    sys.exit(1)

  repo.clone_deps(version_name)
  return False

def xpd_check_info(repo, options, args):
    update = False
    '''
    # TODO github API for description
    if repo.description==None or repo.description=="":
        print("The repo's description is one or two paragraphs description the contents of the repository.")
        if confirm("No description found. Add one", default=True):
            print("Enter paragraph description:\n")
            repo.description = input()
            update = True
    '''

    if False and repo.docdirs==[]:
        if confirm("No documentation path found. Add one", default=True):
            print("Enter documentation path: ")
            docdir = input()
            repo.docdirs.append(docdir)
            update = True

    if repo.vendor==None:
        print("If this repository is maintained by a organization or company that will package, release and support the code then the vendor field should be set with the organization's name.")
        if confirm("No vendor found. Add one", default=True):
            print("Enter vendor name: ")
            repo.vendor = eval(input())
            update = True

    if repo.maintainers==None:
        print("The repository's maintainer is a person who is reponsible for the repository. All repos should have at least one maintainer.")
        if confirm("No maintainer found. Add one", default=True):
            print("Enter maintainer github username: ")
            repo.maintainers = input()
            update = True

    #if not repo.xcore_repo and re.match('.*github.com', repo.location):
    #    repo.xcore_repo = "git://github.com/xcore/" + os.path.basename(repo.location)
    #    update = True

    update = update

    return update

def validate_version(version_string):
    try:
        version = Version(version_str=version_string)
        rel = repo.get_release(version)

        if not rel:
            log_error("Release '%s' not found" % version)
            sys.exit(1)
        githash = repo.get_child_hash(rel.parenthash)

        if not githash:
            log_error("Cannot find githash for version %s, maybe the git history has been modified" % str(version))
            sys.exit(1)
        return version, githash

    except xpd.xpd_data.VersionParseError:
        log_error("Unable to parse version '%s'" % version_string)
        sys.exit(1)

def get_dep_list(repo):
    dep_list = []
    for dep in repo.get_all_deps():
        dep_list.append((dep.repo.name, dep))
    return dep_list

def compare_lt(a, b):
    return a < b

def compare_gt(a, b):
    return a > b

def make_deps_unique(repo, dep_list, compare):
    """ Create a map of dependencies to a single version. Use the compare function
        argument to choose between versions when there are multiple versions with
        the same name.
    """
    common_deps = []
    unique_dep_map = {}

    for (name,dep) in dep_list:
        date = get_date(dep.repo, dep.githash)
        common_deps.append((name,dep,date))

    for key,dep,date in common_deps:
        if key not in unique_dep_map:
            unique_dep_map[key] = (key,dep,date)
        else:
            if compare(unique_dep_map[key][2], date):
                unique_dep_map[key] = (key,dep,date)

    return unique_dep_map

def get_dependency_map_of_version(repo):
    dep_map = {}
    for dep in repo.get_all_deps_once():
      dep_map[dep.repo.name] = dep
    return dep_map

def log_to_file(message, output_file):
    log_info(message)
    if output_file:
        output_file.write(message + '\n')

def xpd_diff(repo, options, args):
    common_dep_only_in_version1 = {}
    common_dep_only_in_version2 = {}
    if len(args) < 2:
        log_error("Requires 2 version numbers to give the difference")
        sys.exit(1)
    if args[0] == args[1]:
        print("No change in the version numbers provided")
        sys.exit(1)

    [version1, githash1] = validate_version(args[0])
    [version2, githash2] = validate_version(args[1])

    vrepo1 = repo.get_versioned_repo(version1)
    vrepo2 = repo.get_versioned_repo(version2)

    # Some dependency directories of older versions may not be present
    repo.clone_deps(args[0])
    repo.clone_deps(args[1])

    dep1_list = get_dep_list(vrepo1)
    unique_deps_version1 = make_deps_unique(vrepo1, dep1_list, compare_lt)
    dep2_list = get_dep_list(vrepo2)
    unique_deps_version2 = make_deps_unique(vrepo2, dep2_list, compare_gt)
    dep_map1 = get_dependency_map_of_version(vrepo1)
    dep_map2 = get_dependency_map_of_version(vrepo2)
    common_deps_of_two_versions = set(dep_map1.keys()) & set(dep_map2.keys())
    only_in_version1 = set(dep_map1.keys()) - set(common_deps_of_two_versions)
    only_in_version2 = set(dep_map2.keys()) - set(common_deps_of_two_versions)

    if options.output_file:
        output_file = open(options.output_file, 'w')
    else:
        output_file = None

    log_to_file("%s moved from %s to %s" % (vrepo1, version1, version2), output_file)
    repo.git_diff(githash1, githash2, output_file)

    # diff of common deps in both the versions, sorted out using their dates and
    # considered newest of version1 and oldest of version2
    for name in common_deps_of_two_versions:
        dep1 = unique_deps_version1[name][1]
        dep2 = unique_deps_version2[name][1]
        if dep1.githash != dep2.githash:
            log_to_file("%s moved from %s to %s" % (name,
                              dep1.version_str if dep1.version_str else dep1.githash,
                              dep2.version_str if dep2.version_str else dep2.githash),
                              output_file)
            dep1.repo.git_diff(dep1.githash, dep2.githash, output_file)
        else:
            log_to_file("%s: No change" % (name), output_file)

    for name in only_in_version2:
        dep = unique_deps_version2[name][1]
        log_to_file("%s(%s) added in version %s of %s" % (name,
              dep.version_str if dep.version_str else dep.githash,
              version2, vrepo2.name), output_file)

    for name in only_in_version1:
        dep = unique_deps_version1[name][1]
        log_to_file("%s(%s) removed in version %s of %s" % (name,
              dep.version_str if dep.version_str else dep.githash,
              version2, vrepo2.name), output_file)

    if output_file:
        output_file.close()

def construct_name(repo, args, type_of_name):
    prefix = type_of_name + '_'
    if not args:
        name = repo.name
        m = re.match(r'(lib_|proj_|sw_)(.*)', name)
        if m:
            name = m.groups(0)[1]
        name = prefix + name + '_example'
        sys.stdout.write('Enter %s name [%s]: ' % (type_of_name, name))
        x = eval(input())
        if x:
            name = x
    else:
        name = args[0]

    if not name.startswith(prefix):
        name = prefix + name

    return name

def xpd_create_app(repo, options, args):
    appname = construct_name(repo, args, 'app')

    log_info("Creating %s" % appname)
    os.mkdir(os.path.join(repo.path, appname))
    os.mkdir(os.path.join(repo.path, appname, 'src'))
    f = open(os.path.join(repo.path, appname, 'Makefile'), 'wb')
    f.write(templates.app_makefile)
    f.close()
    f = open(os.path.join(repo.path, appname, 'README.rst'), 'wb')
    f.write(templates.swblock_readme)
    f.close()
    return False

def xpd_create_lib(repo, options, args):
    modulename = construct_name(repo, args, 'lib')

    log_info("Creating %s" % modulename)
    os.mkdir(os.path.join(repo.path, modulename))
    os.mkdir(os.path.join(repo.path, modulename, 'src'))
    f = open(os.path.join(repo.path, modulename, 'module_build_info'), 'wb')
    f.write(templates.module_build_info)
    f.close()
    f = open(os.path.join(repo.path, modulename, 'README.rst'), 'wb')
    f.write(templates.swblock_readme)
    f.close()
    return False

def xpd_check_infr(repo, options, args, return_ok=False):
    ok = True
    makefiles_ok = xpd.check_project.check_makefiles(repo, force_creation=True)
    ok = ok and makefiles_ok
    changelog_ok = xpd.check_project.check_changelog(repo, force_creation=True)
    ok = ok and changelog_ok

    if return_ok:
        return ok
    else:
        return False

def xpd_check_makefiles(repo, options, args, return_ok=False):
    ok = xpd.check_project.check_makefiles(repo)
    if return_ok:
        return ok
    else:
        return False

def xpd_check_partinfo(repo, options, args):
    update = False
    if not repo.partnumber:
        print("If this is an XMOS package or a github repo showing to the xsoftipexplorer, there should be an associated part number for the repository.")
        if confirm("No part number found. Add one", default=True):
            repo.partnumber = \
                cognidox.query_and_create_document('/Projects/Apps',
                                                   default_title=repo.longname,
                                                   doctype='DH',
                                                   auto_create=True)
            repo.subpartnumber = \
                cognidox.query_and_create_document('/Projects/Apps',
                                                   default_title=repo.name+".zip",
                                                   doctype='SM',
                                                   auto_create=True)
            update = True
    if repo.partnumber and not repo.subpartnumber:
        print("ERROR: there is a part number for the document holder but not for the zipfile. Something is quite wrong with the xpd.xml")
        sys.exit(1)
    # if not repo.partnumber:
    #     print "Cannot find a partnumber. If using cognidox, this should be the partnumber for the document holder *not* the zipfile itself. If a partnumber exists for the zipfile but not the document holder then please create a new partnumber"
    #     repo.partnumber = \
    #         cognidox.query_and_create_document('/Projects/Apps',
    #                                            default_title=repo.longname,
    #                                            doctype='DH')
    #     update = True
    # if not repo.subpartnumber:
    #     print "Need to create document for actual zipfile of software"
    #     repo.subpartnumber = \
    #         cognidox.query_and_create_document('/Projects/Apps',
    #                                            default_title=repo.name+".zip",
    #                                            doctype='SM')
    #     update = True
    log_info("Main part number = %s" % repo.partnumber)
    log_info("Zipfile part number = %s" % repo.subpartnumber)
    return update




# TODO we could use xdoc package. However, its in currently in py2.
# For the moment we will use xdoc as tool installed by xdoc_released
def xpd_build_docs(repo, options=None, args=None, buildlatex=True, local_only=False):

    errors = 0

    if options.nodocs:
        log_info("--nodocs. Skipping")
        return

    log_info(f"Building docs in {repo.path}")

    for docdir in repo.docdirs:

        if not os.path.exists(os.path.join(repo.path, docdir)):
            log_error("%s: docdir '%s' does not exist" % (repo.name, docdir))
            errors = errors + 1
            break

        log_info(f"    {docdir}")

        (stdout_lines, stderr_lines) = call_get_output(["xdoc", "xmospdf"], cwd=docdir)

        output = "".join(stdout_lines)
        output = output.join(stderr_lines)

        for line in output.lower():
            if "error" in line and "details of errors/warnings" not in line:
                    errors = errors + 1
            if "Traceback" in line:
                    errors = errors + 1

    if errors:
        log_error(f"Error building doc: {docdir}")
    else:
        log_info("Building docs ok")

def xpd_check_all(repo, options, args):
    ok = True
    if not (options.nocheckdep):
        res = xpd_check_deps(repo, options, args, return_current_ok=True, allow_updates=True)
        ok = ok and res
        if res:
            log_info("DEPENDENCIES OK")
    res = xpd_check_info(repo, options, args)
    if not res:
        log_info("METAINFORMATION OK")
    ok = ok and not res
    res = xpd_check_swblocks(repo, options, args, return_valid=True)
    if res:
        log_info("SWBLOCK INFORMATION OK")
    ok = ok and res
    res = xpd_check_infr(repo, options, args, return_ok=True)
    if res:
        log_info("MAKEFILE/PROJECT INFORMATION OK")
    ok = ok and res
    if not ok:
        log_info("")
        log_info("=================================================================")
        log_info("REPOSITORY UPDATED")
        log_info("=================================================================")
        log_info("Either there are errors in your repository structure or the")
        log_info("repository structure/meta-information has been updated (see previous output for details)")
        log_info("Try 'git status' and 'git diff' to see changes that have been made to repository")
        log_info("=================================================================")
    return True

#def xpd_update(repo, options, args):
#    return xpd_check_all(repo, options, args)

def xpd_init_dp_sources(repo, options, args):
  if len(args) != 4:
    log_error("init_dp_sources REPO_URL CUSTOMER PROJECT RELEASE")
    sys.exit(1)

  repo_url = args[0]
  customer = args[1]
  project = args[2]
  release_name = args[3]

  init_dp_sources(repo_url, customer, project, release_name)
  return False

def dp_update_repo(repo, options, repo_name, release_name):
  # Recreate the Repo so that branches of dependencies are re-read
  new_repo = Repo_(repo.path)

  # Set the branched_from attribute so that update checks are performed appropriately
  new_repo.set_branched_from(release_name)

  # Perform an update that also changes the uri so that clones work
  xpd_check_deps(new_repo, options, [], allow_updates=True, update_uri=True)
  new_repo.save()

  new_repo.git_add('xpd.xml')
  new_repo.git_commit_if_changed("'Created Derived Product from %s %s'" % (repo_name, release_name), is_dependency=True)

def add_changelog_header(repo, customer, project, release_name):
    changelog_path = os.path.join(repo.path, 'CHANGELOG.rst')
    with open(changelog_path) as f:
      lines = f.readlines()

    started = False
    done = False
    f = open(changelog_path, 'w')
    for line in lines:
        line = line.strip()

        if line:
            started = True

        if started and not done and not line:
            try:
                version = Version(version_str=release_name)
                header_line = "%s_%s_%s_0.0.1" % (version.final_version_str(), customer, project)
                f.write("\n%s\n" % header_line)
                f.write("%s\n" % ('-'*len(header_line)))
                f.write("   * Add release notes here\n")
                done = True
            except xpd.xpd_data.VersionParseError:
                log_error("add_changelog_header: unable to parse version %s" % release_name)
                sys.exit(1)

        f.write("%s\n" % line)
    f.close()

def notes_version_matches(notes_version_str, version):
    if notes_version_str == version.final_version_str():
        return True

    notes_version = changelog_str_to_version(notes_version_str)
    if not notes_version:
        return False
    return notes_version == version

def get_version_diff(repo, from_version, to_version):
    notes = repo.changelog_entries
    diff = []
    started = False
    for (notes_version, items) in notes:
        if notes_version_matches(notes_version, to_version):
            started = True
        if started:
            if notes_version_matches(notes_version, from_version):
                break
            diff.extend(items)

    return diff

def choose_oldest_release(expected):
    oldest = None
    for version_str in expected:
        try:
            rel = Version(version_str=version_str)
            if not oldest:
                oldest = rel
            elif rel < oldest:
                oldest = rel
        except xpd.xpd_data.VersionParseError:
            pass

    return oldest

def strip_existing_changes_lines(lines):
    new_lines = []
    ignore = False
    for line in lines:
        # Ignore a set of dependency changes (from start to new bullet starting with *)
        if ignore:
            if re.match('^\s*\*', line):
                ignore = False
            continue

        if re.match('.*Changes to dependencies:', line):
            ignore = True
            continue

        new_lines.append(line)

    return new_lines

def xpd_update_changelog(repo, options, args):
    ''' Detect all changes in dependencies and add their changes to the changelog.
    '''
    if not repo.changelog_entries or len(repo.changelog_entries) < 2:
        log_debug("update_changelog: not enough entries to have a diff")
        return

    (previous, items) = repo.changelog_entries[1]
    previous_rel = repo.latest_release(release_filter=lambda r: r.version.final_version_str() == previous)
    log_debug("update_changelog: previous version %s" % previous_rel)

    # Previous release in the release notes never actually was made - ignore
    if not previous_rel:
      return

    vrepo = repo.get_versioned_repo(previous_rel.version)

    diffs = {}
    versions = {}

    # Can't work in the state where there are multiple version of a dependency
    errors = get_multiple_version_errors(repo)
    if errors and not options.force and not options.github:
        sys.exit(1)

    to_releases = {}
    from_releases = {}

    for (dep_name, expected) in list(get_all_dep_versions(repo).items()):
        # Having run get_multiple_version_errors() there should now only be one version
        version_str = str(next(iter(expected)))
        try:
            rel = Version(version_str=version_str)
            to_releases[dep_name] = rel
        except xpd.xpd_data.VersionParseError:
            log_debug("update_changelog: can't determine current version dep for '%s'" % dep_name)

    # When cloning the old dependencies then ignore missing repos because they can only
    # be missing if they are no longer used - and therefore warrent a message in the changelog
    for (dep_name, expected) in list(get_all_dep_versions(vrepo, ignore_missing=True).items()):
        log_debug("update_changelog: choosing from old versions %s for '%s'" % (str(expected), dep_name))
        release = choose_oldest_release(expected)
        if release:
            log_debug("update_changelog: chose %s" % release)
            from_releases[dep_name] = release
        else:
            log_debug("update_changelog: can't determine previous version dep for '%s'" % dep_name)

    for dep in repo.get_all_deps_once():
        dep_name = dep.repo.name
        if dep_name not in to_releases:
            log_debug("update_changelog: ignore '%s' as not currently on a version" % dep_name)
            continue
        if dep_name not in from_releases:
            log_debug("update_changelog: ignore '%s' as could not determine previous version" % dep_name)
            continue

        vrel = from_releases[dep_name]
        rel = to_releases[dep_name]
        diff = get_version_diff(dep.repo, vrel, rel)
        if diff:
            diffs[dep.repo.name] = diff
            versions[dep.repo.name] = "%s -> %s" % (vrel, rel)

    if not diffs:
        log_debug("update_changelog: no changes detected")
        return

    # Add the changes to the dependencies latest version
    (version, items) = repo.changelog_entries[0]
    items[:] = strip_existing_changes_lines(items)
    items.append("  * Changes to dependencies:")
    for (dep, changes) in list(diffs.items()):
        items.append("\n    - %s: %s\n" % (dep, versions[dep]))
        changes = strip_existing_changes_lines(changes)
        for line in changes:
            # Only copy in lines which are bullet points (no blank lines)
            m = re.match('\s*[-*+] (.*)', line)
            if m:
                items.append("      + %s" % m.group(1))
            else:
                m = re.match('\s*(.+)$', line)
                if m:
                    items.append("        %s" % m.group(1))
    items.append("")

    # Write out the changelog with the changes to dependencies included
    changelog_path = os.path.join(repo.path, 'CHANGELOG.rst')
    with open(changelog_path, 'wb') as f:
        xpd.check_project.write_changelog_title(repo, f)

        for (version, items) in repo.changelog_entries:
            f.write(version + '\n')
            f.write('-'*len(version) + '\n')
            f.write(line)

            for item in items:
                f.write(item + '\n')

def call_xsoftip(command, comp, repo):
    args = ['', '', '', '']
    tmp = tempfile.mkdtemp()
    package = xpd_install_local_xml(repo, tmp, doing_buildresults=True)

    args[0] = comp.id
    args[1] = os.path.join(repo.path, comp.metainfo_path)
    args[2] = os.path.join(tmp, package.id + ".xml")
    args[3] = repo.path

    cmd = ["xsoftip", command] + args
    process = Popen(cmd, cwd=repo.path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while True:
        line = process.stdout.readline()
        if not line:
            break

        if 'ERROR' in line:
            log_error('    ' + line.rstrip())
        elif 'Exception in thread' in line:
            log_error('    ' + line.rstrip())
        elif 'WARNING' in line:
            log_warning('    ' + line.rstrip())
        elif re.search('Configuration \d+/\d+', line):
            log_info('    ' + line.rstrip())
        else:
            log_debug('    ' + line.rstrip())

    return process.wait()


def xpd_validate_swblock(repo, options, args, return_valid=False):
    valid = True

    # Allow the user to have tab-completed - strip the path.sep
    swblock_id = args[0].rstrip(os.path.sep)

    xpd_check_swblocks(repo, options, args, verbose=False)

    component_names = [comp.name for comp in repo.components]

    sw_blocks = repo.get_software_blocks()
    if swblock_id != 'all' and not any([b for b in sw_blocks if b.id == swblock_id]):
        log_error('%s is not a software block' % swblock_id)
        return False

    #if not repo.no_xsoftip:
    if True:
      for comp in sw_blocks:
        if comp.id == swblock_id or swblock_id == 'all':
            if not comp.name in component_names:
                log_error("Can't check metadata until error found by check_swblocks are fixed")
                return False

            comp.init_from_path(repo, comp.path)
            check_swblock(repo, options, args, comp)
            if comp.metainfo_path:
                log_info("Validating metadata for %s" % comp.id)
                ret = call_xsoftip("validate", comp, repo)
                if ret != 0:
                    return False
            elif comp.type == "component":
                log_error("Cannot find metadata file for %s" % comp.id)
                return False

    if return_valid:
        return valid

    return False

def get_tools_version():
    try:
        (stdout_lines, stderr_lines) = call_get_output(["xcc", "--version"], ignore_exceptions=True)
    except OSError as e:
        if e.errno == 2:
            # "No such file or directory" error - will be handled below
            stdout_lines = None
        else:
            # Pass on unexpected error
            raise

    if not stdout_lines:
        log_error("Failed to determine tools version using 'xcc --version'")
        if platform_is_windows():
            ext = ".bat"
        else:
            ext = ".sh"
        log_error("To fix this, source the SetEnv%s setup script from your xTIMEcomposer installation" % ext)
        sys.exit(1)

    m = re.match("(\d+\.\d+\.\d+).*", stdout_lines[0])
    if m:
        log_info("Using tools verion:" + m.groups(1)[0])
        return m.groups(1)[0]

    return "development"

def xpd_install_local_xml(repo, cache_path, github=False, doing_buildresults=False):
    package = repo.create_dummy_package(repo.current_version_or_githash(short=True))
    for component in package.components:
        component.local = "true"
        component.docPartNumber = package.name + ".doc-" + component.id
        component.docVersion = "latest"
        if github:
            component.type = "communityCode"
            component.scope = "Open Source"
        if component.metainfo_path:
            shutil.copy(os.path.join(repo.path, component.metainfo_path),
                        os.path.join(cache_path, package.name + "-" + component.id + ".metainfo"))

        if component.buildresults_path and os.path.exists(os.path.join(repo.path, component.buildresults_path)):
            shutil.copy(os.path.join(repo.path, component.buildresults_path),
                        os.path.join(cache_path, package.name + "-" + component.id + ".buildresults"))
        elif component.buildresults_path:
            if not doing_buildresults and component.scope != "Roadmap":
                log_warning("%s has no buildresults!" % component.id)
            f = open(os.path.join(cache_path, package.name + "-" + component.id + ".buildresults"), 'wb')
            f.write("<buildresults></buildresults>");
            f.close()

    sw = SoftwareDescriptor()
    sw.id = package.id
    sw.toolsVersion = get_tools_version()
    sw.name = repo.longname
    sw.project = package.project
    sw.packages.append(package)
    f = open(os.path.join(cache_path, package.id + ".xml"), 'wb')
    f.write(sw.toxml("software"))
    f.close()

    all_software = AllSoftwareDescriptor()
    fpath = os.path.join(cache_path, 'OfflineOnlySoftware.xml')
    if os.path.exists(fpath):
        all_software.parse(fpath)
    for p in all_software.packages:
        if p.project == repo.name:
            all_software.packages.remove(p)
    all_software.toolsVersion = sw.toolsVersion
    all_software.packages.append(package)

    f = open(fpath, 'wb')
    f.write(all_software.toxml("software"))
    f.close()

    f = open(os.path.join(cache_path, package.name), 'wb')
    f.write("dummyzip")
    f.close()
    return package


def xpd_approve_latest(repo, options, args):
    if not repo.partnumber:
        return
    if not confirm("Approve latest version in cognidox. This may cause it to automatically appear on xmos.com", default=False):
        return
    f,_ = cognidox.fetch_latest(repo.partnumber)
    dom = xml.dom.minidom.parseString(f.read())
    docs = dom.getElementsByTagName('document')
    for doc in docs:
        partnum = doc.getAttribute('partnum')
        issue = doc.getAttribute('issue')
        log_info("Approving %s, issue %s" % (partnum, issue))
        #cognidox.set_approval_notification(partnum)
        cognidox.set_auto_update(partnum, True)
        cognidox.publish_doc(partnum, comment="Publish to extranet via xpd")
        cognidox.approve_doc(partnum, issue, comment="Bulk approve from xpd")

'''
def xpd_publish(repo, options, args):
    options.upload = True
    return xpd_make_zip(repo, options, args)

def xpd_publish_github(repo, options, args):
    options.upload = True
    options.github = True
    xpd_make_zip(repo, options, args)
'''

def xpd_show_project_deps(repo, options, args):
    deps = repo.get_project_deps()
    for proj, (repo, deps) in list(deps.items()):
        log_info(proj)
        log_info(deps)





common_commands =  [
            ("status", "Show current status (can also use show or info)"),
            ("list", "List releases"),
            ("show_deps", "Show dependencies"),
            ("create_release", "Create a release"),
            ("make_zip", "Make zipfile of release"),

            ]
other_commands =[
            ("check_deps", "Check dependencies of the current repository"),
            ("build", "Build sw and docs"),
            ("create_github_release", "Make a github release (DEBUG)"),
            ("build_docs", "Make docs (DEBUG)"),
            ("find_assets", "List the assets a release will upload (DEBUG)"),
            ("check_all", "Check all meta information and infrastructure"),
            ("check_infr", "Check infrastructure (Makefiles, eclipse projects)"),
            ("check_info", "Check related information"),
            ("check_swblocks", "Check swblocks"),
            ("create_app", "Create application within project"),
            ("create_lib", "Create lib within project"),
            ("update_changelog", "Update the CHANGELOG.rst as the release will (DEBUG)"),
            ("update_readme", "Update README.rst with latest metainformation"),
            ("check_makefiles", "Check makefiles"),
            ("check_partinfo", "Check part information (DEBUG)"),
            ("dump_deps", "Dump deps info to file (DEBUG)"),

            # TODO:

            ("checkout", "Checkout release"),
            ("validate_swblock", "Validate swblock"),
            ("get_deps", "Clone the dependencies of this repository. Optionally takes a version."),
            ("diff", "Shows difference between two versions"),
            ("show_project_deps", "Show app/modules dependencies (DEBUG)"),
            ]

hidden_commands = [("approve_latest", "Approved latest cognidox version")]


def get_git_dir(path):
    (stdout_lines, stderr_lines) = call_get_output(["git", "rev-parse", "--show-cdup"], cwd=path)

    if stdout_lines == []:
        git_dir = path
    else:
        git_dir = os.path.abspath(os.path.join(path, stdout_lines[0][:-1]))

    return git_dir

def create_repo(options, path, search_for_deps=True):

    repo__ = Repo_(path, git_export=options.gitexport)

    # Update component and repo dependencies
    repo__.components = repo__.get_software_blocks(is_update=True, search_for_deps = search_for_deps)

    for c in repo__.components:

        for d in c.dependencies:
            d_repo_path = repo__.find_repo_containing_module_path(str(d))

    if search_for_deps:
        for rd in repo__.dependencies:
            rd.repo = create_repo(options, rd.get_local_path())

    return repo__


if __name__ == "__main__":
    usage = "usage: %prog command [options]"
    usage += "\n\nMost useful commands:\n\n"
    for c in common_commands:
        usage += "%20s: %s\n" % (c[0], c[1])

    usage += "\n\nOther commands:\n\n"
    for c in other_commands:
        usage += "%20s: %s\n" % (c[0], c[1])

    optparser = OptionParser(usage=usage)

    optparser.add_option("-r", "--release-version", dest="release_version",
                         help="release version")

    optparser.add_option("-t", "--release-type", dest="release_type",
                         help="release type: release, alpha, beta or rc")

    optparser.add_option("--force", dest="force", action="store_true", default=False,
                         help="Ignore safety check")

    optparser.add_option("--upload", dest="upload", action="store_true", default=False,
                         help="Upload package to document management system")

    optparser.add_option("--nobuild", dest="nobuild", action="store_true", default=False,
                         help="Do not build when creating a release/package")

    # By default we do not export git history in release zips, however it is useful during debug to check
    # for any changes in the release zip
    optparser.add_option("--gitexport", dest="gitexport", action="store_true", default=False,
                         help="Export git info in release zips")

    optparser.add_option("--nodocs", dest="nodocs", action="store_true", default=False,
                         help="Do not build docs when creating a release/package")

    optparser.add_option("--nocheckdep", dest="nocheckdep", action="store_true", default=False,
                         help="Do not check repo dependencies on update")

    optparser.add_option("--github", dest="github", action="store_true", default=False,
                         help="Treat repo as an \"Open Source Community\" repo for publishing")

    optparser.add_option("--all", dest="show_all", action="store_true", default=False,
                         help="Show all options")

    optparser.add_option("-o", dest="output_file", default=None, help="Diff output file")

    default_logfile = 'run_xpd.log'
    optparser.add_option("--logfile", dest="logfile", default=default_logfile,
                         help="Log file to be used for xpd output (default=%s)" % default_logfile)

    (options, args) = optparser.parse_args()

    if len(args) < 1:
        optparser.error("Please specify a command")

    configure_logging(level_console='INFO', level_file='DEBUG', filename=options.logfile)

    command = args[0]

    search_for_deps = True

    if command in ["list", "find_assets", "build_docs"]:
        search_for_deps = False


    #FIXME
    #if command not in ["get_deps", "list", "create_dp", "init_dp_sources", "checkout"]:
    #    for dep in repo__.get_all_deps_once():
    #        if not os.path.exists(dep.get_local_path()):
    #            log_warning("Cannot find dependency: %s" % dep.repo_name)

    if command == "help":
        optparser.print_help()
        sys.exit(0)

    args = args[1:]

    commands = common_commands + other_commands + hidden_commands

    if command in [c[0] for c in commands]:
        if command == 'publish_github':
            options.github = True

        repo__ = create_repo(options, ".", search_for_deps)

        command_fn = eval("xpd_%s" % command)

        if command_fn(repo__, options, args):
            if options.github:
                repo__.leave_github_mode()

        print_status_summary()




    else:
        matches = difflib.get_close_matches(command, commands)
        sys.stderr.write("Unknown command %s\n" % command)
        if matches != []:
            sys.stderr.write("Did you mean one of:\n")
            for m in matches:
                sys.stderr.write("   %s\n" % m)

