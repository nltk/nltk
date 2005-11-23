#!/usr/bin/perl -CSD

# @langcodes = {"HNG", "ICE", "RUM", "PQL", "FIN"};
$KEY = "TL8ZdoNQFHK8IIyd7f7oTaqLTJm1VANN";
$stop_words = "stop_words";


#foreach $langcode (@langcodes)
#{
#	open (infile, $langcode . "_swad");
#	$_ = <infile>;
#	exec "echo $_"
#	exec "/usr/local/java -cp googleapi.jar com.google.soap.search.GoogleAPIDemo $KEY $_"
#}



open (STOP_WORDS, $stop_words);

while (<STOP_WORDS>)
{
	unless (exists $stop_hash{$_}) {
		$stop_hash{$_} = "";
	}
}
close (STOP_WORDS);


# open (SEARCH_WORDS, "HNG_swad");
while (<STDIN>) 
{
	if (! (exists $stop_hash{$_}) && length($_) > 3) {
		print($_);
	}
}

# close(SEARCH_WORDS);
