#!/usr/bin/perl -w

use English;
use strict;

my $file = $ARGV[0] or die "Usage: $PROGRAM_NAME <file>\n";
open(FILE, $file) or die "Couldn't open `$file' for reading.\n";
for my $line (<FILE>) {
  if ($line =~ /^\\ps/) {
    my ($marker, $data) = $line =~ /^(\\ps)(.*)$/;
    if (defined $data) {
      $data = uc($data);
    } else {
      $data = "???";
    }
    $line = "$marker$data\n";
  } 
  print $line;
}
close(FILE) or warn "Couldn't close `$file'.\n";
exit;