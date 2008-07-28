"""
Basic state machine class
"""
class StateMachine(object):
    """
    A basic but flexible state machine
    """
    def __init__(self):
        """
        Initialize and return the object
        """
        self.nodes = list()
        self.start_state = None
        self.end_states = list()

    def addstate(self, node, end_state=False):
        """
        Add a function that represents a state within the machine
        """
        self.nodes.append(node)
        if end_state:
            self.end_states.append(node)

    def setstart(self, node): 
        """
        Mark a given state as a starting state
        """
        self.start_state = node

    def run(self, tokens=None):
        """
        Invoke the machine

        @param tokens: list of tokens
        @type tokens: list
        """
        if self.start_state is None:
            raise RuntimeError("No start state defined")
        if not self.end_states:
            raise RuntimeError("No end states defined")
        node = self.start_state
        while True:
            tup = node(tokens)
            (new_node, tokens) = tup
            #(new_node, tokens) = node(tokens)
            if new_node in self.end_states:
                new_node(tokens)
                break 
            elif new_node not in self.nodes:
                raise RuntimeErrror, "Invalid target %s", new_state
            else:
                node = new_node

class PushDownMachine(StateMachine):
    """
    State machine that uses and additional stack.
    """

    def __init__(self):
        """
        Initialize and return the object
        """
        StateMachine.__init__(self)
        self.stack = []

    def push(self, token):
        """
        Push a value onto the stack

        @param token: A token to be pushed onto the stack
        @type token: object
        """

        self.stack.append(token)

    def pop(self):
        """
        Remove an object from the top of the stack.

        @return: The token on the top of the stack
        """
        self.stack.pop()

    def run(self, tokens=None):
        """
        Process all the tokens with the machine

        @param tokens: The list of tokens
        @type tokens: list

        @return: The stack after the machine had finished processing the tokens
        """
        super(PushDownMachine, self).run(tokens)
        return self.stack
