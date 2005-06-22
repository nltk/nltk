#!/usr/bin/perl -w

# --------------------------------------------------------------
# Author:        Stuart P. Robinson
# Date:          27 May 2003
# Description:   This program takes a Shoebox dictionary and
#                does stuff that I'm too tired to describe.
# --------------------------------------------------------------

use English;
use strict;
use vars qw( %verbs );
use POSIX;

main();

# --------------------------------------------------------------
# SUBROUTINES
# --------------------------------------------------------------

sub main {
  my $file = $ARGV[0] or die "Usage: $PROGRAM_NAME <FILE>\n";
  my $fc = slurp(dewindoze($file));
  my @entries = collapse_entries($fc);
  my $ahHits = search_entries(\@entries);
  print_results($ahHits);
  exit;
}

sub print_results {
  my $ahHits = shift;

  my $current_date = strftime("%c", localtime);
  print "$current_date\n\n";

  for my $suffix (sort keys %$ahHits) {
    print "\n\nSUFFIX: $suffix\n";
    my @hits = @{$ahHits->{$suffix}};
    for my $e (@hits) {
      my ($lx) = $e =~ /\\lx(.*?)\\/;
      my ($ps) = $e =~ /\\ps(.*?)\\/;
      my ($gl) = $e =~ /\\ge(.*?)\\/;
      my ($ex) = $e =~ /\\ex(.*?)\\/;
      my ($tr) = $e =~ /\\xe(.*?)$/;
      
      $lx =~ s/ *(.*) */$1/;
      $ps =~ s/ *(.*) */$1/;
      $gl =~ s/ *(.*) */$1/;
      $ex =~ s/ *(.*) */$1/;
      $tr =~ s/ *(.*) */$1/;
      
      print "  $lx [$ps] `$gl'\n";
      print "  $ex\n";
      print "  $tr\n\n";
    }
  }
}

sub search_entries {
  my $rEntries = shift;
  my $ahHits = {};
  for my $e (@$rEntries) {
    if ($e =~ /\\ex.*(RE|VA|IA)/) {
      #print "$1"; # DEBUG
      push(@{$ahHits->{$1}}, $e);
    }
  }
  return $ahHits;
}

sub collapse_entries {
  my $fc = shift;
  $fc .= "\n\n"; # gotta catch last entry
  $fc =~ s/\n{2,}/\n\n/g;
  $fc =~ s/\n\n/###/g;
  $fc =~ s/\n/ /g;
  my @entries = split("###", $fc);
  return @entries;
}

sub dewindoze {
    my $fc = shift;
    $fc =~ s/\cM//g;
    return $fc;
}

sub slurp {
    my $file = shift;
    open(FILE, "<$file") or die "Can't open $file for reading: $!";
    my $contents = do { local $/, <FILE> };
    close(FILE) or warn $!;
    return $contents;
}