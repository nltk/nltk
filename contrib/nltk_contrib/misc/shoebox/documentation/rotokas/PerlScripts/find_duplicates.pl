#!/usr/bin/perl -w

use English;
use strict;

my $file = $ARGV[0] or die "Usage: $PROGRAM_NAME <file>\n";
open(FILE, $file) or die "Couldn't open `$file' for reading.\n";
my $last_line = "";
for my $line (<FILE>) {
  print $line if $line eq $last_line;
  $last_line = $line;
}
close(FILE) or warn "Couldn't close `$file'.\n";
exit;