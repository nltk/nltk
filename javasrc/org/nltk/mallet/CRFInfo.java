/*
 * Copyright (C) 2001-2012 NLTK Project
 * Author: Edward Loper <edloper@gradient.cis.upenn.edu>
 * URL: <http://www.nltk.org/>
 * For license information, see LICENSE.TXT
 */

package org.nltk.mallet;

import javax.xml.parsers.*;
import java.util.*;
import java.util.regex.Pattern;
import org.w3c.dom.*;
import org.xml.sax.*;
import java.io.*;
import java.util.logging.Logger;
import edu.umass.cs.mallet.base.util.MalletLogger;
import edu.umass.cs.mallet.base.fst.CRF4;

public class CRFInfo
{
    private static Logger logger =
        MalletLogger.getLogger(CRFInfo.class.getName());

    public String uri="?";

    /** The variance for the gaussian prior that is used to regularize
     * weights. */
    public double gaussianVariance = 1.0;

    /** The 'default' label, which is used as history when no label is
     * actually available (e.g., at the beginning of an instance). */
    public String defaultLabel = "O";

    /** The maximum number of iterations for training. */
    public int maxIterations = 500;

    /** If stateInfoList is null, then this can be used to pick a 
     * structure for the CRF states. */
    public int stateStructure = FULLY_CONNECTED_STRUCTURE;

    static public int FULLY_CONNECTED_STRUCTURE = 0;
    static public int HALF_CONNECTED_STRUCTURE = 1;
    static public int THREE_QUARTERS_CONNECTED_STRUCTURE = 2;
    static public int BILABELS_STRUCTURE = 3;
    static public int ORDER_N_STRUCTURE = 4;

    /** If stateStructure is ORDER_N_STRUCTURE, then these can be used
     * to customize the structure: (not impl yet) */
    public int[] orders = null;
    public boolean[] defaults = null;
    public String start = null;
    public Pattern forbidden = null;
    public Pattern allowed = null;
    public boolean fullyConnected = false;

    /** List of StateInfo objects. */
    public List<StateInfo> stateInfoList;

    /** List of all weight groups. */
    public List<WeightGroupInfo> weightGroupInfoList;

    /** CRF4.transductionType */
    public int transductionType = CRF4.VITERBI;

    /** The Mallet model filename */
    public String modelFile = null;

    /** The feature detector function's name */
    public String featureDetectorName = null;

    /** Does NLTK add a start & end state? */
    public boolean addStartState = false;
    public boolean addEndState = false;

    public class StateInfo {
        public String name;
        public double initialCost=0;
        public double finalCost=0;
        public String[] destinationNames;
        public String[] labelNames;
        public String[][] weightNames;
    }

    public class WeightGroupInfo {
        public String name;
        public String featureSelectionRegex;
    }

    //////////////////////////////////////////////////////////////////////
    // Constructor (reads file)
    //////////////////////////////////////////////////////////////////////

    CRFInfo(String uri) throws ParserConfigurationException, SAXException,
                               java.io.IOException {
        this.uri = uri;
        // Load the DOM document builder
        DocumentBuilderFactory dbf =DocumentBuilderFactory.newInstance();
        DocumentBuilder db = dbf.newDocumentBuilder();
        // Parse the xml
        parse(db.parse(uri).getDocumentElement());
    }

    CRFInfo(File file) throws ParserConfigurationException, SAXException,
                              java.io.IOException {
        this.uri = file.getName();
        // Load the DOM document builder
        DocumentBuilderFactory dbf =DocumentBuilderFactory.newInstance();
        DocumentBuilder db = dbf.newDocumentBuilder();
        // Parse the xml
        parse(db.parse(file).getDocumentElement());
    }

    CRFInfo(InputStream stream) 
           throws ParserConfigurationException, SAXException,
                  java.io.IOException {
        // Load the DOM document builder
        DocumentBuilderFactory dbf =DocumentBuilderFactory.newInstance();
        DocumentBuilder db = dbf.newDocumentBuilder();
        // Parse the xml
        parse(db.parse(stream).getDocumentElement());
    }

    //////////////////////////////////////////////////////////////////////
    // Parsing
    //////////////////////////////////////////////////////////////////////

    void parse(Element root) {
        NodeList nodes = root.getChildNodes();
        for (int n=0; n<nodes.getLength(); n++) {
            Node node = nodes.item(n);
            if (node instanceof Element) {
                String tag = node.getNodeName();
                if (tag.equals("gaussianVariance")) {
                    gaussianVariance = getTextDouble((Element)node);
                } else if (tag.equals("defaultLabel")) {
                    defaultLabel = getText((Element)node);
                } else if (tag.equals("maxIterations")) {
                    maxIterations = getTextInt((Element)node);
                } else if (tag.equals("transductionType")) {
                    String ttype = getText((Element)node);
                    if (ttype.equalsIgnoreCase("VITERBI"))
                        transductionType = CRF4.VITERBI;
                    else if (ttype.equalsIgnoreCase("VITERBI_FBEAM"))
                        transductionType = CRF4.VITERBI_FBEAM;
                    else if (ttype.equalsIgnoreCase("VITERBI_BBEAM"))
                        transductionType = CRF4.VITERBI_BBEAM;
                    else if (ttype.equalsIgnoreCase("VITERBI_FBBEAM"))
                        transductionType = CRF4.VITERBI_FBBEAM;
                    else if (ttype.equalsIgnoreCase("VITERBI_FBEAMKL"))
                        transductionType = CRF4.VITERBI_FBEAMKL;
                    else
                        throw new RuntimeException("Bad transdutionType val");
                } else if (tag.equals("states")) {
                    readStates((Element)node);
                } else if (tag.equals("weightGroups")) {
                    readWeightGroups((Element)node);
                } else if (tag.equals("modelFile")) {
                    modelFile = getText((Element)node); 
                } else if (tag.equals("featureDetector")) {
                    featureDetectorName = getAttrib((Element)node, "name"); 
                } else if (tag.equals("addStartState")) {
                    addStartState = getTextBoolean((Element)node);
                } else if (tag.equals("addEndState")) {
                    addEndState = getTextBoolean((Element)node);
                }
                else
                    throw new RuntimeException("Unexpected tag "+tag);
            }
            else if (node instanceof Text)
                assertEmptyText(node);
        }
    }

    void readStates(Element statesNode) {
        stateInfoList = new ArrayList<StateInfo>();

        NodeList stateNodes = statesNode.getChildNodes();
        for (int i=0; i<stateNodes.getLength(); i++) {
            Node node = stateNodes.item(i);
            if (node instanceof Element) {
                String tag = node.getNodeName();
                if (tag.equals("state"))
                    stateInfoList.add(readState((Element)node));
                else
                    throw new RuntimeException("Unexpected tag "+tag);
            }
            else if (node instanceof Text)
                assertEmptyText(node);
        }

        if (stateInfoList.size() == 0) {
            stateInfoList = null;
            String stateStruct = getAttrib(statesNode, "structure");
            if (stateStruct.equalsIgnoreCase("FullyConnected"))
                stateStructure = FULLY_CONNECTED_STRUCTURE;
            else if (stateStruct.equalsIgnoreCase("HalfConnected"))
                stateStructure = HALF_CONNECTED_STRUCTURE;
            else if (stateStruct.equalsIgnoreCase("ThreeQuarterLabels"))
                stateStructure = THREE_QUARTERS_CONNECTED_STRUCTURE;
            else if (stateStruct.equalsIgnoreCase("BiLabels"))
                stateStructure = BILABELS_STRUCTURE;
        }
        else if (statesNode.hasAttribute("structure"))
            throw new RuntimeException("use structure or <state>s, not both");
    }

    StateInfo readState(Element stateNode) { 
        StateInfo stateInfo = new StateInfo();

        // Get the state's name.
        stateInfo.name = getName(stateNode);

        //...
        if (stateNode.hasAttribute("initialCost"))
            stateInfo.initialCost = getAttribDouble(stateNode, "initialCost");
        if (stateNode.hasAttribute("finalCost"))
            stateInfo.finalCost = getAttribDouble(stateNode, "finalCost");

        // Get all the other info.
        NodeList nodes = stateNode.getChildNodes();
        for (int n=0; n<nodes.getLength(); n++) {
            Node node = nodes.item(n);
            if (node instanceof Element) {
                String tag = node.getNodeName();
                if (tag.equals("initialCost")) {
                    stateInfo.initialCost = getTextDouble((Element)node);
                } else if (tag.equals("finalCost")) {
                    stateInfo.finalCost = getTextDouble((Element)node);
                } else if (tag.equals("transitions")) {
                    readTransitions((Element)node, stateInfo);
                } 
                else
                    throw new RuntimeException("Unexpected tag "+tag);
            }
            else if (node instanceof Text)
                assertEmptyText(node);
        }
        return stateInfo;
    }
                

    void readTransitions(Element transitionsNode, StateInfo stateInfo) {
        // Get a list of the transition nodes.
        NodeList transitions = transitionsNode.getElementsByTagName
            ("transition");

        // Allocate space for the transition info.
        stateInfo.destinationNames = new String[transitions.getLength()];
        stateInfo.labelNames = new String[transitions.getLength()];
        stateInfo.weightNames = new String[transitions.getLength()][];

        // Parse each transition node.
        for (int j=0; j<transitions.getLength(); j++) {
            Element transition = (Element) transitions.item(j);

            stateInfo.destinationNames[j] = getAttrib(transition, 
                                                      "destination");
            stateInfo.labelNames[j] = getAttrib(transition, "label");

            // Fill in the weight names.
            String wg = getAttrib(transition, "weightGroups");
            String[] wgs = wg.split("\\s+");
            stateInfo.weightNames[j] = new String[wgs.length];
            for (int k=0; k<wgs.length; k++) {
                stateInfo.weightNames[j][k] = wgs[k];
            }
        }
    }

    void readWeightGroups(Element weightGroupsNode) {
        weightGroupInfoList = new ArrayList<WeightGroupInfo>();

        NodeList weightGroupNodes = weightGroupsNode.getChildNodes();
        for (int i=0; i<weightGroupNodes.getLength(); i++) {
            Node node = weightGroupNodes.item(i);
            if (node instanceof Element) {
                String tag = node.getNodeName();
                if (tag.equals("weightGroup"))
                    weightGroupInfoList.add(readWeightGroup((Element)node));
                else
                    throw new RuntimeException("Unexpected tag "+tag);
            }
            else if (node instanceof Text)
                assertEmptyText(node);
        }
    }

    WeightGroupInfo readWeightGroup(Element weightGroupNode) {
        WeightGroupInfo weightGroupInfo = new WeightGroupInfo();
        weightGroupInfo.name = getName(weightGroupNode);
        weightGroupInfo.featureSelectionRegex = getAttrib(
            weightGroupNode, "features");
        return weightGroupInfo;
    }

    //////////////////////////////////////////////////////////////////////
    // Helper Methods
    //////////////////////////////////////////////////////////////////////

    private String getName(Element element) {
        return getAttrib(element, "name");
    }

    private String getAttrib(Element element, String attrib) {
        if (! (element.hasAttribute(attrib)) )
            throw new RuntimeException("Expected "+attrib+" for "+element);
        return element.getAttribute(attrib);
    }

    private int getAttribInt(Element element, String attrib) {
        try { return Integer.parseInt(getAttrib(element, attrib)); }
        catch (NumberFormatException e)
            { throw new RuntimeException("Bad value for "+attrib); }
    }

    private double getAttribDouble(Element element, String attrib) {
        if (getAttrib(element, attrib).equals("+inf"))
            return Double.POSITIVE_INFINITY;
        try { return Double.parseDouble(getAttrib(element, attrib)); }
        catch (NumberFormatException e)
            { throw new RuntimeException("Bad value for "+attrib); }
    }

    private void assertEmptyText(Node node) {
        if (! node.getNodeValue().trim().equals("") )
            throw new RuntimeException("Unexpected text "+node);
    }
    
    private double getTextDouble(Node node) {
        try { return Double.parseDouble(getText(node)); }
        catch (NumberFormatException e)
            { throw new RuntimeException("Bad value for "+node); }
    }

    private int getTextInt(Node node) {
        try { return Integer.parseInt(getText(node)); }
        catch (NumberFormatException e)
            { throw new RuntimeException("Bad value for "+node); }
    }

    private boolean getTextBoolean(Node node) {
        try { return Boolean.parseBoolean(getText(node)); }
        catch (NumberFormatException e)
            { throw new RuntimeException("Bad value for "+node); }
    }

    private String getText(Node node) {
        if ( (node.getChildNodes().getLength() != 1) ||
             (node.getFirstChild() == null) ||
             (! (node.getFirstChild() instanceof Text) ) )
            throw new RuntimeException("Expected value for "+node);
            return ((Text) node.getFirstChild()).getNodeValue();
    }

    private Element getElementByTagName(Element elt, String name) {
        NodeList elts = elt.getElementsByTagName(name);
        if (elts.getLength() == 0)
            throw new RuntimeException("Expected to find "+name);
        else if (elts.getLength() == 1)
            return (Element)elts.item(0);
        else
            throw new RuntimeException("Multiple "+name+" elements");
    }

    private String ljust(String s, int width) {
        while (s.length() < width)
            s += " ";
        return s;
    }
    
    //////////////////////////////////////////////////////////////////////
    // Display
    //////////////////////////////////////////////////////////////////////

    void display(PrintStream out) {
        out.println("CRF ["+uri+"]");
        out.println("  gaussian variance  = " + gaussianVariance);
        out.println("  default label      = '" + defaultLabel+"'");

        Iterator iter = stateInfoList.iterator();
        out.println("\n  States & Transitions\n  ~~~~~~~~~~~~~~~~~~~~");
        while (iter.hasNext()) {
            StateInfo stateInfo = (StateInfo) iter.next();
            out.print("    "+ljust("["+stateInfo.name+"]", 22));
            out.print(" (initial cost = "+stateInfo.initialCost);
            out.println(", final cost = "+stateInfo.finalCost+")");
            for (int i=0; i<stateInfo.destinationNames.length; i++) {
                out.print("      -> ");
                out.print(ljust("["+stateInfo.destinationNames[i]+"]", 20));
                out.print(" (label='"+stateInfo.labelNames[i]+"'");
                out.print(", weightGroups=[");
                for (int j=0; j<stateInfo.weightNames[i].length; j++) {
                    out.print(stateInfo.weightNames[i][j]);
                    if (j < (stateInfo.weightNames[i].length-1))
                        out.print(", ");
                }
                out.println("])");
            }
        }

        iter = weightGroupInfoList.iterator();
        out.println("\n  Weight Groups\n  ~~~~~~~~~~~~~~~~~");
        while (iter.hasNext()) {
            WeightGroupInfo weightGroupInfo = (WeightGroupInfo) iter.next();
            out.print("    "+ljust(weightGroupInfo.name, 22));
            out.println(" (features=/"+
                        weightGroupInfo.featureSelectionRegex+"/)");
        }
            
    }

    //////////////////////////////////////////////////////////////////////
    // Test
    //////////////////////////////////////////////////////////////////////

    public static void main (String[] args) throws Exception
    {
        CRFInfo info = new CRFInfo(args[0]);
        info.display(System.out);
    }
}
