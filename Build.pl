#!/usr/bin/perl
use warnings;
use strict;

use Carp;
use SetupEnv;
use File::Copy;
use File::Path;
use XmosBuildLib;
use XmosArg;

my $MAKE_FLAGS;
my $CONFIG;
my $HOST;
my $DOMAIN;
my $BIN;

my %ALIASES =
  (
	  'all' => ['build','install'],
  );

my %TARGETS =
  (
   'clean' => [\&DoClean, "Clean"],
   'build' => [\&DoBuild, "Build"],
   'install' => [\&DoInstall, "Install packaged binaries"],
  );

sub main
{
  my $xmosArg = XmosArg::new(\@ARGV);
  SetupEnv::SetupPaths();

  my @targets =
    sort { XmosBuildLib::ByTarget($a, $b) }
      (@{ $xmosArg->GetTargets() });

  $MAKE_FLAGS = $xmosArg->GetMakeFlags();
  $CONFIG = $xmosArg->GetOption("CONFIG");
  $DOMAIN = $xmosArg->GetOption("DOMAIN");
  $HOST = $xmosArg->GetOption("HOST");
  $BIN = $xmosArg->GetBinDir();

  foreach my $target (@targets) {
    DoTarget($target);
  }
  return 0;
}

sub DoTarget
{
  my $target = $_[0];
  if ($target eq "list_targets") {
    ListTargets();
  } else {
    my $targets = $ALIASES{$target};
    if (defined($targets)) {
      # Target is an alias
      foreach my $target (@$targets) {
        DoTarget($target);
      }
    } else {
      my $function = $TARGETS{$target}[0];
      if (defined($function)) {
        print(" ++ $target\n");
        &$function();
      }
    }
  }
}

sub ListTargets
{
  foreach my $target (keys(%TARGETS)) {
    print("$target\n");
  }
  foreach my $alias (keys(%ALIASES)) {
    print("$alias\n");
  }
}

sub DoBuild
{
  print("$BUILDPATH");
  system("python $TOOLS_PYINSTALLER/pyinstaller.py xpd.spec");
}

sub DoClean
{
  print("$BUILDPATH");
  File::Path::rmtree('dist');
  File::Path::rmtree('build');

#  chdir("auto_proj") or die("oops");
#  system("make clean")
}

sub DoInstall
{
  chdir($BUILDPATH) or die("oops");
  # Rename doxygen to avoid clash with version supplied with OS
  XmosBuildLib::InstallFile($DOMAIN, "dist", "xpd.exe");
  XmosBuildLib::InstallxSOFTipToolsFile($DOMAIN, "dist", "xpd.exe", "bin");
}

main()
