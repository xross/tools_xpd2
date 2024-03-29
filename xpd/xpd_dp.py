import errno
import os
import re
import sys

from xmos_logging import log_error, log_warning, log_info, log_debug
from xpd.xpd_data import Repo_
from xmos_subprocess import call, platform_is_windows

def mkdir_p(path):
  try:
    os.makedirs(path)
  except OSError as exc: # Python >2.5
    if exc.errno == errno.EEXIST and os.path.isdir(path):
      pass
    else:
      raise

def init_dp_sources(repo_url, customer, project, release_name):
  project_path = os.path.join(customer, project)

  if not os.path.exists(project_path):
    mkdir_p(project_path)

  # Extract the repo name from URL
  m = re.match(r'^.*/([^/.]+)(\.git)?$', repo_url)
  if not m:
    log_error("Failed to extract repo name from URL (%s)" % repo_url)
    return

  repo_name = m.group(1)

  repo_path = os.path.join(project_path, repo_name)
  if os.path.exists(repo_path):
    log_error("Repo %s already exists in %s" % (repo_name, project_path))
    sys.exit(1)

  # Clone the repository
  retval = call(["git", "clone", repo_url], cwd=project_path)
  if retval:
    log_error("Failed to clone %s" % repo_url)
    sys.exit(1)

  repo = Repo(repo_path)
  repo.clone_deps(release_name)

  # Do this again now that the dependency files exist
  repo = Repo(repo_path)
  return repo

def repo_init_remote_and_branch(repo, customer, project):
  backup_path = "git://git/ce/derived_products/%s/%s/%s.git" % (customer, project, repo.name)
  log_info("%s: setting remote to %s" % (repo.name, backup_path))
  call(["git", "remote", "rename", "origin", "upstream"], cwd=repo.path)
  call(["git", "remote", "add", "origin", backup_path], cwd=repo.path)

  branch_name = "%s_%s" % (customer, project)
  log_info("%s: creating and moving to branch %s" % (repo.name, branch_name))
  call(["git", "checkout", "-b", branch_name], cwd=repo.path)

def init_dp_branch(repo, customer, project, release_name):
  vrepo = repo.checkout(release_name)
  if not vrepo:
    sys.exit(1)

  repo_init_remote_and_branch(vrepo, customer, project)
  for dep in vrepo.get_all_deps_once():
    repo_init_remote_and_branch(dep.repo, customer, project)

  return vrepo

def remote_call(user, host, commands):
  tmp_file = '.remote_commands.txt'
  if platform_is_windows():
    with open(tmp_file, 'w') as f:
      f.write('\n'.join(commands))
      f.write('\n')
    args = ['plink.exe','-ssh', '-noagent', '-m', tmp_file, user + "@" + host]

  else:
    args = ['ssh', '-q', user + "@" + host] + ['; '.join(commands)]

  retval = call(args)

  if platform_is_windows():
    os.remove(tmp_file)

  return retval

def create_repo_command(repo):
  return ['~/scripts/create_repo.sh %s git "Fork of %s"' % (repo.name, repo.name)]

def init_dp_backup(repo, customer, project):
  git_folder = 'git/ce/derived_products/%s/%s' % (customer, project)
  commands  = ['if [ -e %s ] ; then exit 1 ; fi' % git_folder ]
  commands += ['mkdir -p %s' % git_folder]
  commands += ['cd %s' % git_folder]
  commands += create_repo_command(repo)
  for dep in repo.get_all_deps_once():
    commands += create_repo_command(dep.repo)

  retval = remote_call('git', 'git', commands)
  if retval:
    log_error("Failed to create repos on git server - check they don't already exist")
    log_info("Commands that were being run:\n  %s" % '\n  '.join(commands))
    return

  repo.git_push_to_backup()
  for dep in repo.get_all_deps_once():
    dep.repo.git_push_to_backup()

