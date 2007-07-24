from qt import Qt

__all__ = ["AccelKeyHandler"]

class AccelKeyHandler:
    """ Per-widget accel key handler mixin.

    While QAccel permits only application level key-bindings,
    AcceKeyHandler allows to define key-bindings on widget level.
    This is useful when the action of the key binding should
    affect only the currently focused widget.

    To use it, add AccelKeyHandler to the bases of the class that you
    are deriving from another Qt widget.  Name the actions to be
    associated with key bindings.  Then, implement methods that
    take the actions that you just have named.  The name of these
    methods are the action names prefixed with "accel_".  Finally,
    call the setKeyBindings method with a dictionary of key sequences
    and action names.  The following code snippet illustrate the usage::

        class MyWidget(QWidget,AccelKeyHandler):
            def __init__(self, parent=None):
                QWidget.__init__(self, parent)
                self.setKeyBindings({"Ctrl+A":"myAction"})
                ...
            
            def accel_myAction(self):
                ...

    The values of the key binding dictionary passed to setKeyBindings
    can also be callables.  For example, the following code has the
    same effect as the one above:

        class MyWidget(QWidget,AccelKeyHandler):
            def __init__(self, parent=None):
                QWidget.__init__(self, parent)
                self.setKeyBindings({"Ctrl+A":self.accel_myAction})
                ...
            
            def accel_myAction(self):
                ...
                
    """

    KeyAliases = {
        'Ctrl':'Control',
        'Del':'Delete',
        'Ins':'Insert'
        }

    def setKeyBindings(self, keyBindings):
        """ Set key-bindings for the widget.

        Key-bindings are specified by a dictionary of key sequence
        string and the action name.

        Key sequence is a list of sub-sequences delimited by comma (,).
        A sub sequence consists of a key name optionally prefixed by
        modifier key names. Some examples are::

          "K"
          "Ctrl+K"
          "Ctrl+Alt+K"
          "Alt+X,Ctrl+K"

        @type keyBindings: dict
        @param keyBindings: Key-bindings specified by a dictionary of
        key sequences and action names.

        """
        bindings = {}
        for keyseq,binding in keyBindings.items():
            seq = []
            for subkeyseq in keyseq.split(','):
                a = []
                for key in subkeyseq.split('+'):
                    key = key.strip()
                    key = key[0].upper() + key[1:].lower()
                    if key in self.KeyAliases:
                        key = self.KeyAliases[key]
                    a.append(key)
                state = Qt.NoButton
                for key in a[:-1]:
                    state |= eval("Qt.%sButton" % key)
                seq.append((state,eval("Qt.Key_%s"%a[-1])))

            b = bindings
            for e in seq[:-1]:
                if e in b:
                    b = b[e]
                else:
                    b[e] = {}
                    b = b[e]
            b[seq[-1]] = self.translateToBindingName(binding)
            
        self.AKH_keyBindings = bindings
        self.AKH_keyBindingsWaiting = {}

    def keyPressEvent(self, e):
        """ This implements the host class' keyPressEvent method.

        If the key event is a part of a key sequence that is set by
        setKeyBindings call, the event will be processed and accepted.
        Otherwise, the keyPressEvent method of the host class' base
        class will be called in turn.
        
        If the host class explicitly re-implements the keyPressEvent,
        this method will be overridden by it.

        @param e: Keyboard Event.
        @type e: QKeyEvent
        """
        if self.processKeyPressEvent(e):
            e.accept()
        elif hasattr(self, "_keyHandlerBase"):
            self._keyHandlerBase.keyPressEvent(self,e)
        else:
            c = list(self.__class__.__bases__)
            while AccelKeyHandler not in c:
                d = []
                for x in c:
                    d += list(x.__bases__)
                c = d
            self._keyHandlerBase = c[0]
            self._keyHandlerBase.keyPressEvent(self,e)
            #self.__class__.__base__.keyPressEvent(self,e)

    def processKeyPressEvent(self, e):
        """ Process the current keyboard event.

        If the key event is a part of a key sequence that is set by
        setKeyBindings call, the event will be processed and True
        will be returned. Otherwise, False will be returned.
        
        @param e: Keyboard Event.
        @type e: QKeyEvent
        @return: True if the event if processed, False if the event is
        rejected.
        """
        
        event = (e.state(),e.key())
        if event in self.AKH_keyBindingsWaiting:
            found = self.AKH_keyBindingsWaiting[event]
        elif event in self.AKH_keyBindings:
            found = self.AKH_keyBindings[event]
        else:
            key = event[1]
            if key!=Qt.Key_Control and key!=Qt.Key_Alt and key!=Qt.Key_Shift:
                self.AKH_keyBindingsWaiting = {}
            return False
        if type(found) == dict:
            self.AKH_keyBindingsWaiting = found
        else:
            found()
        return True

    def translateToBindingName(self, action):
        """ Translates the action name to the bound method name.

        @param action: action name (str) or a callable
        @type actionName: str/callable
        @return: method bound to the action if action is a string,
        or action itself if it is a callable
        @rtype: callable
        """
        if type(action) == str:
            return eval("self.accel_%s" % action)
        else:
            return action

