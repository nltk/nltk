# 9xx : file io error
ERR_TDF_IMPORT = 900
ERR_TDF_EXPORT = 901
ERR_TRANS_IMPORT = 910
ERR_TRANS_EXPORT = 911
ERR_TYP_IMPORT = 920
ERR_TXT_EXPORT = 931

ERRORS = {
    900:"tdf file import error",
    901:"tdf file export error",
    910:"transcriber file import error",
    911:"transcriber file export error",
    920:"typ file import error",
    931:"cts-style txt file export error",
    }

class Error:
    def __init__(self, errno, msg=None):
        if errno in ERRORS:
            self.errno = errno
        else:
            self.errno = None
        self.msg = msg

    def errstr(self):
        if self.errno in ERRORS:
            return ERRORS[self.errno]
        else:
            return "Unknown error"

    def __str__(self):
        if self.msg:
            return self.msg
        elif self.errno in ERRORS:
            return ERRORS[self.errno]
        else:
            return "Unknown error"
        
