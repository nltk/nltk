#!/usr/bin/perl -w

use English;
use strict;
use vars qw( %parts_of_speech );
use POSIX;

main();

sub main {
  my $file = $ARGV[0] or die "Usage: $PROGRAM_NAME <FILE>\n";
  open(FILE, $file) or die "Couldn't open `$file' for reading.\n";
  for my $line (<FILE>) {
    if ($line =~ /^\\ps/) {
      my ($marker, $data) = $line =~ /^(\\ps)(.*)$/;
      if (defined $data) {
        if (exists $parts_of_speech{$data}) {
          $parts_of_speech{$data} += 1;
        } else {
          $parts_of_speech{$data} = 1;
        }
      }
    }
  }
  close(FILE) or warn "Couldn't close `$file'.\n";

  print_results();

  exit;
}

sub print_results {
  my $current_date = strftime("%c", localtime);
  print "$current_date\n\n";
  
  for my $ps (sort keys %parts_of_speech) {
     my $i = $parts_of_speech{$ps};
     print "$ps\t$i\n";
  }
}
