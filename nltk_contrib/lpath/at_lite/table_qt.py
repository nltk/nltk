import tableproxy
from table import TableModel

__all__ = ['TableModel']

TableModel = tableproxy.getProxy(TableModel)
        
if __name__ == "__main__":
    tab = TableModel([('a',str),('b',str),('c',str)])
    tab.insertRow(0)
    tab.insertRow(1)
    tab[0][0] = "apple"
    tab[0][1] = 2
    tab[0][2] = 3
    tab[1][0] = "orange"
    tab[1][1] = 5
    tab[1][2] = 3
    tab.printTable()

    print

    tab.insertColumn(1,[("extra",int),10,9])
    tab.printTable()

    print

    c = tab.takeColumn(1)
    tab.insertColumn(3,c)
    tab.printTable()

    print

    r = tab.takeRow(0)
    tab.insertRow(1,r)
    tab.printTable()

    print
    
    tab.sort(1,2)
    tab.printTable()

