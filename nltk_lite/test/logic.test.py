# put this into unittest format

from nltk_lite.semantics import *

def runtests():
    # Test a beta-reduction which used to be wrong
    l = Parser(r'(\x.\x.(x x) 1)').next().simplify()
    id = Parser(r'\x.(x x)').next()
    assert l == id

    # Test numerals
    zero = Parser(r'\f x.x').next()
    one = Parser(r'\f x.(f x)').next()
    two = Parser(r'\f x.(f (f x))').next()
    three = Parser(r'\f x.(f (f (f x)))').next()
    four = Parser(r'\f x.(f (f (f (f x))))').next()
    succ = Parser(r'\n f x.(f (n f x))').next()
    plus = Parser(r'\m n f x.(m f (n f x))').next()
    mult = Parser(r'\m n f.(m (n f))').next()
    pred = Parser(r'\n f x.(n \g h.(h (g f)) \u.x \u.u)').next()
    v1 = ApplicationExpression(succ, zero).simplify()
    assert v1 == one
    v2 = ApplicationExpression(succ, v1).simplify()
    assert v2 == two
    v3 = ApplicationExpression(ApplicationExpression(plus, v1), v2).simplify()
    assert v3 == three
    v4 = ApplicationExpression(ApplicationExpression(mult, v2), v2).simplify()
    assert v4 == four
    v5 = ApplicationExpression(pred, ApplicationExpression(pred, v4)).simplify()
    assert v5 == two

    # betaConversionTestSuite.pl from
    # _Representation and Inference for Natural Language_
    #
    x1 = Parser(r'(\p.(p mia) \x.(walk x))').next().simplify()
    x2 = Parser(r'(walk mia)').next().simplify()
    assert x1 == x2

    x1 = Parser(r'some x.(and (man x) (\p.some x.(and (woman x) (p x)) \y.(love x y)))').next().simplify()
    x2 = Parser(r'some x.(and (man x) some y.(and (woman y) (love x y)))').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.(sleep a) mia)').next().simplify()
    x2 = Parser(r'(sleep mia)').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.\b.(like b a) mia)').next().simplify()
    x2 = Parser(r'\b.(like b mia)').next().simplify()
    assert x1 == x2

    x1 = Parser(r'\a.(\b.(like b a) vincent)').next().simplify()
    x2 = Parser(r'\a.(like vincent a)').next().simplify()
    assert x1 == x2

    x1 = Parser(r'\a.(and (\b.(like b a) vincent) (sleep a))').next().simplify()
    x2 = Parser(r'\a.(and (like vincent a) (sleep a))').next().simplify()
    assert x1 == x2
    
    x1 = Parser(r'(\a.\b.(like b a) mia vincent)').next().simplify()
    x2 = Parser(r'(like vincent mia)').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(p (\a.(sleep a) vincent))').next().simplify()
    x2 = Parser(r'(p (sleep vincent))').next().simplify()
    assert x1 == x2

    x1 = Parser(r'\a.(a (\b.(sleep b) vincent))').next().simplify()
    x2 = Parser(r'\a.(a (sleep vincent))').next().simplify()
    assert x1 == x2

    x1 = Parser(r'\a.(a (sleep vincent))').next().simplify()
    x2 = Parser(r'\a.(a (sleep vincent))').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.(a vincent) \b.(sleep b))').next().simplify()
    x2 = Parser(r'(sleep vincent)').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.(believe mia (a vincent)) \b.(sleep b))').next().simplify()
    x2 = Parser(r'(believe mia (sleep vincent))').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.(and (a vincent) (a mia)) \b.(sleep b))').next().simplify()
    x2 = Parser(r'(and (sleep vincent) (sleep mia))').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.\b.(and (\c.(c (a vincent)) \d.(probably d)) (\c.(c (b mia)) \d.(improbably d))) \e.(walk e) \e.(talk e)))').next().simplify()
    x2 = Parser(r'(and (probably (walk vincent)) (improbably (talk mia)))').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.\b.(\c.(c a b) \d.\e.(love d e)) jules mia)').next().simplify()
    x2 = Parser(r'(love jules mia)').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.\b.some c.(and (a c) (b c)) \d.(boxer d) \d.(sleep d))').next().simplify()
    x2 = Parser(r'some c.(and (boxer c) (sleep c))').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.(z a) \c.\a.(like a c))').next().simplify()
    x2 = Parser(r'(z \c.\a.(like a c))').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.\b.(a b) \c.\b.(like b c))').next().simplify()
    x2 = Parser(r'\b.(\c.\b.(like b c) b)').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.\b.(\c.(c a b) \b.\a.(loves b a)) jules mia)').next().simplify()
    x2 = Parser(r'(loves jules mia)').next().simplify()
    assert x1 == x2

    x1 = Parser(r'(\a.\b.(and some b.(a b) (a b)) \c.(boxer c) vincent)').next().simplify()
    x2 = Parser(r'(and some b.(boxer b) (boxer vincent))').next().simplify()
    assert x1 == x2

if __name__ == '__main__':
    runtests()
    main()

