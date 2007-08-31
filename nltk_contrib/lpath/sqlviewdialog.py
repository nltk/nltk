from qt import *
import lpath

class SqlViewDialog(QDialog):
    def __init__(self, lpql=None, parent=None, name=None,
                 modal=False, wflag=0):
        QDialog.__init__(self, parent, name, modal, wflag)

        layout = QGridLayout(self)
        text = QTextEdit(self)
        if lpql is not None:
            sql,_ = lpath.translate2(lpql)
            stat =  " query tokenization: %6.3fs\n"
            stat += "    grammar parsing: %6.3fs\n"
            stat += "      chart parsing: %6.3fs\n"
            stat += "        translation: %6.3fs\n"
            stat = stat % lpath.get_profile()
            text.setText(str(sql))
            font = QFont("Courier")
            font.setBold(True)
            text.setCurrentFont(font)
            text.append("\n\n" + stat)
        layout.addWidget(text,0,0)

        buttons = QHBox(self)
        self.btnDismiss = QPushButton("&Dismiss", buttons)
        layout.addMultiCellWidget(buttons, 1,1,0,0)

        layout.setMargin(5)
        layout.setSpacing(5)
        buttons.setMargin(10)
        buttons.setSpacing(10)
        self.resize(600,300)

        self.connect(self.btnDismiss, SIGNAL("clicked()"), self.accept)
