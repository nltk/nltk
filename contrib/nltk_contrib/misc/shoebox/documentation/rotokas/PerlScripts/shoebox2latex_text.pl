#!/usr/bin/perl -w

# --------------------------------------------------------------
# Author:        Stuart P. Robinson
#
# Date:          7 May 2003
#
# Description:   This program takes a Shoebox text and converts
#                it into a LaTeX document. The expected input
#                format is the following:
#  
#                -----------------------------------
#                -                                 -
#                -                                 -
#                -                                 -
#                -                                 -
#                -                                 -
#                -----------------------------------
#  
#                The output format is the following:
#  
#                -----------------------------------
#                -                                 -
#                -                                 -
#                -                                 -
#                -                                 -
#                -                                 -
#                -----------------------------------
#  
# Likely Errors: Because the program uses double carriage
#                returns in order to parse the lines of the
#                text, stray carriage returns can wreak havoc.
#                Make sure that the only double carriage
#                returns are those separating the end of one
#                line of text from another.
# --------------------------------------------------------------

use English;
use strict;
use Getopt::Long;
use vars qw( $opt_verbose $opt_debug );

# --------------------------------------------------------------

main();

# --------------------------------------------------------------
# SUBROUTINES
# --------------------------------------------------------------

sub main {
    handle_options();
    my $file = $ARGV[0] or usage();
    my $file_contents = dewindoze(slurp($file));
    my %hLines = parse_lines($file_contents);
    print_latex(\%hLines);
    exit;
}

sub print_latex {
    my $rhLines = shift;
    
    print "\\documentclass[11pt, a4paper]{article}\n\n";
    print "\\usepackage{gloss}\n";
    print "\\usepackage{cm-lingmacros}\n\n";
    print "\\begin{document}\n\n";
    for my $key (sort keys %$rhLines) {
    	my $t = $rhLines->{$key}->{'t'};
    	my $m = $rhLines->{$key}->{'m'};
    	my $g = $rhLines->{$key}->{'g'};
    	my $f = $rhLines->{$key}->{'f'};
    
        $t =~ s/[ \t]+/ /g;        
        $m =~ s/[ \t]+/ /g;
        $m =~ s/- +/-/g;
        $m =~ s/ +-/-/g;
        $g =~ s/[ \t]+/ /g;
        $g =~ s/- +/-/g;
        $g =~ s/ +-/-/g;
        
        print "\\begin{example} \\label{$key}\n";
        print "\\dgloss $t\n";
        print "$m\n";
        print "$g\n";
	print "\\uGlossed{``$f''}\n";
        print "\\end{example}\n\n";
    }
    print "\\end{document}\n";
}

sub parse_lines {
    my $fc = shift;
    $fc .= "\n\n"; # make sure regex grabs last line
    my @aLines = $fc =~ m/\\ref\s+(.*?)\n\n/gsm;
    my $hLines = {}; # anonymous hash
    for my $r (@aLines) {
        # Extract ref number
        my ($ref_num) = $r =~ /^([0-9]+)/;
        $r =~ s/^[0-9]+\n//ms;
        $ref_num = sprintf "%0.3d", $ref_num; # pad to 3 digits

        # Now pull out each line of the ref
        $r .= "\n"; # make sure regex grabs last line
        for my $l (split("\n", $r)) {
            my ($field_marker, $field_data) = $l =~ /^\\([a-zA-Z0-9]+)\s+(.*)$/;
            #print "$field_marker###$field_data\n";
            $hLines->{$ref_num}->{$field_marker} = $field_data;
        }
    }
    return %$hLines;
}

sub usage {
    warn "Usage:\n";
    warn "  $PROGRAM_NAME [OPTIONS] <FILE>\n";
    warn "Options:\n";
    warn "  -v     Provide verbose output\n";
    exit;
}

sub handle_options {
    GetOptions('v' => \$opt_verbose,
               'd' => \$opt_debug);
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

sub latex_escape {
    my $input = shift;
    $input =~ s/_/\\_/g;
    return $input;
}