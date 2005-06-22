#!/usr/bin/perl -w

use English;
use strict;
use vars qw( %duplicates @duplicates);

main();

# ----------------------------------------------------------------
# SUBROUTINES
# ----------------------------------------------------------------

sub main {
  # Find the duplicates
  my $file = $ARGV[0] or die "Usage: $PROGRAM_NAME <file>\n";
  open(FILE, $file) or die "Couldn't open `$file' for reading.\n";
  for my $line (<FILE>) {
    my ($entry) = $line =~ /\\lx +(.*)/;
    if (defined $entry) {
      #print "$entry\n";
      if (exists $duplicates{$entry}) {
        push(@duplicates, $entry);
        $duplicates{$entry} += 1; 
      } else {
        $duplicates{$entry} = 0; 
      }
    }
  }
  close(FILE) or warn "Couldn't close `$file'.\n";

  # Now print out the duplicates
  print_duplicates();
  exit;
}

sub print_duplicates {
  for my $dup (@duplicates) {
    print "$dup\t$duplicates{$dup}\n";
  }
}