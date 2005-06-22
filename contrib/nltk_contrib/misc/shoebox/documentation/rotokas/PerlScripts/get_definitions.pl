#!/usr/bin/perl -w

# --------------------------------------------------
# AUTHOR: Stuart P. Robinson
# DATE:   20 August 2003
# NOTES:  This script will take a wordlist file
#           and find the definition for every word
#           in the Shoebox dictionary.
# --------------------------------------------------

use strict;
use English;

main();

sub main {
    my ($dict_file, $word_file) = @ARGV or usage();
    my @words = split("\n", slurp($word_file));
    my %dict = get_dict_entries(slurp($dict_file));
    for my $w (@words) {
	my $def = exists $dict{$w} ? $dict{$w} : "--";
	print "$w ``$def''\n";
    }
}

sub get_dict_entries {
    my $file_contents = shift;
    $file_contents .= "\n\n";
    my %dict;
    my @entries = split("\n\n", $file_contents);
    for my $e (@entries) {
	#print "ENTRY [$e]\n";
	my ($lex) = $e =~ /\\lx ([^\\\n]+)/;
	my ($def) = $e =~ /\\ge ([^\\\n]+)/;
	#print "[$lex] / [$def]\n";
	$dict{$lex} = $def;
    }
    return %dict;
}

sub usage {
    print STDERR "$PROGRAM_NAME <DICTIONARY FILE> <WORDLIST FILE>\n";
    exit;
}

sub slurp {
    my $file = shift;
    open(FILE, "<$file") or die "Can't open $file for reading: $!";
    my $contents = do { local $/, <FILE> };
    close(FILE) or warn $!;
    return $contents;
}
