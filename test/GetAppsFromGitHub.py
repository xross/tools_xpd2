from github import Github
import os

tests_top = os.getcwd()

github = Github()
org = github.get_organization("Xcore")
repos = org.get_repos("public")
for repo in repos:
    test_name = "test_" + repo.name
    test_folder = os.path.join(test_name, repo.name)

    if os.path.exists(test_folder):
        print "Updating %s" % repo.name
        os.chdir(test_folder)
        os.system('git pull')

    else:
        print "Cloning %s" % repo.name
        if not os.path.exists(test_name):
            os.mkdir(test_name)
        os.chdir(test_name)
        os.system('git clone ' + repo.clone_url)

    os.chdir(tests_top)

