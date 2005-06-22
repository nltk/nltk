#!/usr/bin/perl -w

#----------------------------------------------------------------
# AUTHOR:      Stuart Robinson
# DATE:        14 May 2003
# DESCRIPTION: This program searches a Shoebox dictionary for
#              every lexeme (\lx ...) and lists them according
#              to their shape--i.e., VCV for 'ari', CVVCV for
#              'guato', etc. along with their English gloss.
#----------------------------------------------------------------

use English;
use strict;

main();

#----------------------------------------------------------------
# SUBROUTINES
#----------------------------------------------------------------

sub main {
  my $file = $ARGV[0] or usage();
  my @lexs = get_lexs($file);
  my $rhShapes = list_shapes(\@lexs);
  print_results($rhShapes, $file);
  exit;
}

# Print out results
sub print_results {
  my $rhShapes = shift;
  my $file = shift;
  
  print "# Automatically generated from $file by $PROGRAM_NAME\n\n";
  
  for my $s (sort keys %$rhShapes) {
    my $raLexs = $rhShapes->{$s};
    print "/$s/\n";
    for my $lx (@$raLexs) {
      print "$lx\n";
    }
    print "\n";
  }
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

# Iterate over entries, put into hash where
# key is shape, values is array of lexemes
sub list_shapes {
  my $raLexs = shift;
  my $rhShapes = {};
  for my $lex (@$raLexs) {
    next if $lex =~ /[\- ]/;
    # Ignore entries with spaces or dashes
    my $shape = get_shape($lex);
    if (!exists $rhShapes->{$shape}) {
      $rhShapes->{$shape} = [];
    }
    push(@{$rhShapes->{$shape}}, $lex);
  }
  return $rhShapes;
}

sub get_shape {
  my $lx = shift;
  my @chars = split('', $lx);
  for my $c (@chars) {
    if ($c =~ /[aeiou]/) {
      $c = 'V';
    } else {
      $c = 'C';
    }
  }
  return join('', @chars);
}

sub dewindoze {
    my $fc = shift;
    $fc =~ s/\cM//g;
    return $fc;
}

sub slurp {
    my $file = shift;
    open(FILE, "<$file") or 
      die "Can't open $file for reading: $!";
    my $contents = do { local $/, <FILE> };
    close(FILE) or warn $!;
    return $contents;
}

sub usage {
  print "Usage: $PROGRAM_NAME [-v] <FILE>\n";
  exit;
}