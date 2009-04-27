# Natural Language Toolkit: TextGrid analysis
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Margaret Mitchell <itallow@gmail.com>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import sys
import re

class Tier(object):
    """
    Class to manipulate the TextGrid format used by Praat.
    """

    def __init__(self, fid):
        """
        Takes filename as input, separates out each tier.
        """

        self.read_file = open(fid, "r").read()
        self.readl_file = open(fid, "r").readlines()
        self.num_tiers = 0
        self.xmin = 0
        self.xmax = 0
        self.check_type()
        self.tiers = self.find_tiers()

    def check_type(self):
        """
        Figures out what sort of TextGrid format the file is.
        """
        
        type_id = self.readl_file[0].strip()
        if type_id == "File type = \"ooTextFile\"":
            if self.readl_file[3].split()[0] != "xmin":
                self.TextGridType = "oldooTextFile"
            else:
                self.TextGridType = "ooTextFile"
        elif type_id == "\"Praat chronological TextGrid text file\"":
            self.TextGridType = "ChronTextFile"
        elif type_id == "the other one":
            self.TextGridType = "OtherTextFile"
	
    def find_tiers(self):
        """
        Organizes the information from each tier.
        """

        tier_hash = {}
        if self.TextGridType == "ooTextFile":
            tmp1 = self.readl_file[3].split()
            self.xmin = tmp1[2]
            tmp2 = self.readl_file[4].split()
            self.xmax = tmp2[2]
            tmp3 = self.readl_file[6].split()
            self.num_tiers = int(tmp3[2])
            headers = re.findall(" *item \[\d+\]:[\r\n]+", self.read_file)
        elif self.TextGridType == "ChronTextFile":
            tmp1 = self.readl_file[1].split() 
            (self.xmin, self.xmax) = (tmp1[0], tmp1[1])
            tmp2 = self.readl_file[2].split()
            self.num_tiers = int(tmp2[0])
            headers = re.findall("\"\S+\" \".*\" \d+\.?\d* \d+\.?\d*", \
                                 self.read_file)
        elif self.TextGridType == "oldooTextFile":
            self.xmin = self.readl_file[3].strip()
            self.xmax = self.readl_file[4].strip()
            self.num_tiers = int(self.readl_file[6].strip())
            headers = re.findall("(\".*\")[\r\n]+\".*\"", self.read_file)
        x = 0
        while x < len(headers):
            header = headers[x]
            try:
                end = self.readl_file.index(headers[x + 1])
            except IndexError:
                end = len(self.readl_file)
            if self.TextGridType == "ooTextFile":
                idx = self.readl_file.index(header)
                classid = self.readl_file[idx + 1].split()[2][1:-1]
                nameid = self.readl_file[idx + 2].split()[2][1:-1]
                xmin = self.readl_file[idx + 3].split()[2]
                xmax = self.readl_file[idx + 4].split()[2]
                _trans = self.readl_file[idx + 6:end]
                transcript = self._make_ootrans(_trans, classid)
            elif self.TextGridType == "ChronTextFile":
                idx = self.readl_file.index(header + "\n")
                info_line = self.readl_file[idx].split()
                classid = info_line[0][1:-1]
                nameid = info_line[1][1:-1]
                (xmin, xmax) = (info_line[2], info_line[3])
                _trans = self.readl_file[idx + 1:end]
                transcript = self._make_chtrans(_trans)
            elif self.TextGridType == "oldooTextFile":
                idx = self.readl_file.index(header + "\n")
                classid = self.readl_file[idx].strip()[1:-1]
                nameid = self.readl_file[idx + 1].strip()[1:-1]
                xmin = self.readl_file[idx + 2].strip()
                xmax = self.readl_file[idx + 3].strip()
                _trans = self.readl_file[idx + 5:end]
                transcript = self._make_oldootrans(_trans, classid)
            x += 1
            tier_hash[str(x)] = \
              {"class":classid, \
               "name":nameid, \
	           "xmin":xmin, "xmax":xmax, \
	           "transcript":transcript}
        return tier_hash 

    def get_tier(self, tiernum):
        """
        Given a tier number, returns the information on that tier.
        """

        tiernum = str(tiernum)
        try:
            entry = self.tiers[tiernum]
        except KeyError:
            sys.stderr.write("Error - Can't find tier " + str(tiernum) + "!\n")
            return False
        return entry

    def get_transcript(self, tiernum):
        """
        Returns the transcript of the tier, separated by utterance.
        """
       
        tiernum = str(tiernum)
        transcript = []
        try:
            entry = self.tiers[tiernum]
            trans_info = entry["transcript"]
        except KeyError:
            sys.stderr.write("Error - Can't find tier " + str(tiernum) + "!\n")
            return False
        for utt in sorted(trans_info):
            transcript += [trans_info[utt]]
        return transcript

    def get_time(self, tiernum, non_speech_char="."):
        """
        Returns the utterance time of a given tier.
        Screens out entries that begin with a non-speech marker.	
        """

        tiernum = str(tiernum)         	
        try:
            tier = self.tiers[tiernum]
        except KeyError:
            sys.stderr.write("Error - Can't find tier " + str(tiernum) + "!\n")
            return False
        time = 0.0
        x = 0
        trans_info = tier["transcript"]
        if tier["class"] == "IntervalTier":
            for i in trans_info:
                (xmin, xmax) = i
                text = trans_info[i]
                if text and text[0] != non_speech_char:
                    tmp_time = float(xmax) - float(xmin)
                    time += tmp_time
        else:
            i = 1
            sorted_info = sorted(trans_info)
            while i < len(sorted_info):
                if sorted_info[i][0] != non_speech_char:
                    xmin = sorted_info[i-1]
                    xmax = sorted_info[i]
                    tmp_time = float(xmax) - float(xmin)
                    time += tmp_time
                i += 1
                    
        return time

    def get_tier_num(self, tiername):
        """
        Returns the tier number of a tier with a given name.
        """

        for tier in self.tiers:
            name_tmp = self.tiers[tier]["name"].split(" = ")
            name = name_tmp[1].strip("\"")
            if name == tiername:
                return tier
        sys.stderr.write("No tier found by tiername ")
        sys.stderr.write("\"" + str(tiername) + "\"\n")
        return False

    def get_tier_name(self, tiernum):
        """
        Returns the tier name of a tier with a given number.
        """

        tiernum = str(tiernum)
        try:
            return self.tiers[tiernum]["name"]
        except KeyError:
            sys.stderr.write("No tier numbered \"" + tiernum + "\"\n")
            return False
        return False

    def get_class(self, tiernum):
        """
        Returns the type of transcription on tier:  interval or point.
        """

        tiernum = str(tiernum)
        try:
            return self.tiers[tiernum]["class"]
        except KeyError:
            sys.stderr.write("No tier numbered \"" + str(tiernum) + "\"\n")
            return False
        return False

    def get_min_max(self, tiernum):
        """
        Returns xmin and xmax for a given tier.
        """

        tiernum = str(tiernum)
        try:
            xmin = self.tiers[tiernum]["xmin"]
            xmax = self.tiers[tiernum]["xmax"]
            return (xmin, xmax)
        except KeyError:
            sys.stderr.write("No tier numbered \"" + str(tiernum) + "\"\n")
            return False
        return False

    def _make_chtrans(self, _trans):
        i = 0
        _trans_hash = {}
        while i < len(_trans):
            _trans_tmp = _trans[i:i+2]
            _line = _trans_tmp[0]
            _tmp = _line.split()
            _xmin = _tmp[1]
            _xmax = _tmp[2]
            _text = _trans_tmp[1].strip()[1:-1]
            i += 2
            _trans_hash[(_xmin, _xmax)] = _text
        return _trans_hash

    def _make_ootrans(self, _trans, _classid):
        i = 0
        _trans_hash = {}
        if _classid == "TextTier" or _classid == "PointTier":
            while i < len(_trans):
                tmp1 = _trans[i+1].split()
                _time = tmp1[2]
                tmp2 = _trans[i+2].split()
                _text = " ".join(tmp2[2:])[1:-1]
                _trans_hash[_time] = _text
                i += 3
        elif _classid == "IntervalTier":
            while i < len(_trans):
                tmp1 = _trans[i+1].split()
                _xmin = tmp1[2]
                tmp2 = _trans[i+2].split()
                _xmax = tmp2[2]
                tmp3 = _trans[i+3].split()
                _text = " ".join(tmp3[2:])[1:-1]
                i += 4
                _trans_hash[(_xmin, _xmax)] = _text
        else:
            sys.stderr.write("Unrecognized TextGrid format: "+_classid+"\n")
        return _trans_hash

    def _make_oldootrans(self, _trans, _classid):
        i = 0
        _trans_hash = {}
        if _classid == "TextTier" or _classid == "PointTier":
            while i < len(_trans):
                _time = _trans[i].strip()
                _text = _trans[i+1].strip()[1:-1]
                _trans_hash[_time] = _text
        if _classid == "IntervalTier":
            while i < len(_trans):
                _xmin = _trans[i].strip()
                _xmax = _trans[i+1].strip()
                _text = _trans[i+2].strip()[1:-1]
                i += 3
                _trans_hash[(_xmin, _xmax)] = _text
        else:
            sys.stderr.write("Unrecognized TextGrid format: "+_classid+"\n")
        return _trans_hash


def demo(filename):
    print "** This is a demo of how to use this class.\t     **"
    print "** Given a filename, for example, 'Subj34.TextGrid', **"
    print "** set a variable x = textgrid.Tier(filename).\t     **\n"
    fid = Tier(filename)
    if fid.num_tiers == 1:
        print "There is 1 tier in this file"
    else:
        print "There are " + str(fid.num_tiers) + " tiers in this file"
    x = 0
    while x < fid.num_tiers:
        x += 1
        tiername = fid.get_tier_name(x)
        print "The name of tier " + str(x) + " is: " + tiername
        classid = fid.get_class(x)
        print "This tier is of type:  " + classid
        min_max = fid.get_min_max(x)
        print "Minimum and maximum times of this tier are as follows:"
        print min_max
        transcript = fid.get_transcript(x)
        print "The transcript from this tier is:"
        print transcript
        time = fid.get_time(x)
        print "The total utterance time on this is:"
        print str(time) + " seconds"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Demo usage:  python textgrid.py filename.extension"
	sys.exit()
    demo(sys.argv[1])
