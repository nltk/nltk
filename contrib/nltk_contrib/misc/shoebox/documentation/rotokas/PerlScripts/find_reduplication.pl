#!/usr/bin/perl -w

#----------------------------------------------------------------
# AUTHOR:      Stuart Robinson
# DATE:        14 May 2003
# DESCRIPTION: This program searches a Shoebox dictionary for
#              every lexeme (\lx ...) and prints out those that
#              are fully reduplicated (e.g., itoito, oaoa, etc).
#----------------------------------------------------------------

use English;
use strict;

main();

#----------------------------------------------------------------
# SUBROUTINES
#----------------------------------------------------------------

sub main {
  my $file = $ARGV[0] or die "Usage: $PROGRAM_NAME <file>\n";
  my @lexs = get_lexs($file);
  find_redup_lex(\@lexs);
  exit;
}

# Extract all the \lx entries
sub get_lexs {
  my $file = shift;
  my @lexemes;
  my $lex;
  open(FILE, $file) or die "Couldn't open `$file' for reading.\n";
  for my $line (<FILE>) {
    if ($line =~ /^\\lx/) {
      ($lex) = $line =~ /^\\lx *(.*) *$/;
      push(@lexemes, $lex);
    }
  }
  close(FILE) or warn "Couldn't close `$file'.\n";
  return @lexemes;
}

# Iterate over entries, see if they're fully reduplicated
sub find_redup_lex {
  my $raLexs = shift;
  for my $lex (@$raLexs) {
    my $cc = scalar(split('', $lex));
    if (($cc % 2) == 0) {
      my $n = $cc / 2;
      #print "$lex | $cc | $n\n";
      my $half1 = substr($lex, 0, $n); 
      my $half2 = substr($lex, $n, $cc);
      print "$lex\n" if $half1 eq $half2;
    }
  }
}