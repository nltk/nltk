from nltk_contrib.drt import *

def resolve(drs):
    print drs
    print drs.__class__
    print AbstractDRS
    print isinstance(drs, AbstractDRS)
    assert isinstance(drs, AbstractDRS)
    return _resolve(drs, [])

def _resolve(current, trail):
    resolve_method = None
    if isinstance(current, DRS):
        resolve_method = _resolve_DRS
    elif isinstance(current, LambdaDRS):
        resolve_method = _resolve_LambdaDRS
    elif isinstance(current, ConcatenationDRS):
        resolve_method = _resolve_ConcatenationDRS
    elif isinstance(current, ApplicationDRS):
        resolve_method = _resolve_ApplicationDRS
    elif isinstance(current, ApplicationExpression):
        resolve_method = _resolve_ApplicationExpression
    elif isinstance(current, VariableBinderExpression):    
        resolve_method = _resolve_VariableBinderExpression
    elif isinstance(current, Expression):
        resolve_method = _resolve_Expression
    else:
        raise AssertionError, 'Not a valid expression'

    return resolve_method(current, trail)


def _resolve_DRS(current, trail):
    r_conds = []
    for cond in current.conds:
        r_cond = _resolve(cond, trail + [current])
        
        # if the condition is of the form '(x = [])' then do not include it
        if not _isNullResolution(r_cond):
            r_conds.append(r_cond)
            
    return current.__class__(current.refs, r_conds)
    
def _isNullResolution(current):
    return isinstance(current, ApplicationExpression) and \
           isinstance(current.first, ApplicationExpression) and \
           isinstance(current.first.first, FolOperator) and \
           current.first.first.operator == Tokens.EQ and \
           ((isinstance(current.second, PossibleAntecedents) and not current.second) or \
            (isinstance(current.first.second, PossibleAntecedents) and not current.first.second))

def _resolve_LambdaDRS(current, trail):
    return current.__class__(current.variable, _resolve(current.term, trail + [current]))

def _resolve_ApplicationDRS(current, trail):
    trail_addition = [current]
    if isinstance(current.first, ApplicationDRS) \
            and isinstance(current.first.first, DrsOperator) \
            and current.first.first.operator == 'implies':
        trail_addition.append(current.first.second)

    r_first = _resolve(current.first, trail + trail_addition)
    r_second = _resolve(current.second, trail + trail_addition)
    return current.__class__(r_first, r_second)

def _resolve_ConcatenationDRS(current, trail):
    r_first = _resolve(current.first, trail + [current])
    r_second = _resolve(current.second, trail + [current])
    return current.__class__(r_first, r_second)

def _resolve_ApplicationExpression(current, trail):
    if isinstance(current.first, VariableExpression) and current.first.variable.name == Tokens.PRONOUN:
        possible_antecedents = PossibleAntecedents()
        for ancestor in trail:
            if isinstance(ancestor, AbstractDRS):
                possible_antecedents.extend(ancestor.get_refs())
    #===============================================================================
    #   This line ensures that statements of the form ( x = x ) wont appear.
    #   Possibly change to remove antecedents with the wrong 'gender' 
    #===============================================================================
        possible_antecedents.remove(current.second)
        eqalityExp = ApplicationExpression(ApplicationExpression(FolOperator(Tokens.EQ), current.second),possible_antecedents) 
        return eqalityExp
    else:
        r_first = _resolve(current.first, trail + [current])
        r_second = _resolve(current.second, trail + [current])
        return current.__class__(r_first, r_second)

def _resolve_Expression(current, trail):
    return current

def _resolve_VariableBinderExpression(current, trail):
    return current.__class__(current.variable, _resolve(current.term, trail + [current]))

def testResolve_anaphora():
    print 'Test resolve_anaphora():'
    drs = Parser().parse(r'drs([x,y,z],[(dog x), (cat y), (walks z), (PRO z)])')
    print '    ' + str(drs.infixify())
    print '    resolves to: ' + str(resolve(drs.simplify()).infixify()) + '\n'

    drs = Parser().parse(r'drs([],[(drs([x],[(dog x)]) implies drs([y],[(walks y), (PRO y)]))])')
    print '    ' + str(drs.infixify())
    print '    resolves to: ' + str(resolve(drs.simplify()).infixify()) + '\n'

    drs = Parser().parse(r'drs([],[((drs([x],[]) + drs([],[(dog x)])) implies drs([y],[(walks y), (PRO y)]))])')
    print '    ' + str(drs.infixify())
    print '    resolves to: ' + str(resolve(drs.simplify()).infixify()) + '\n'

if __name__ == '__main__':
    testResolve_anaphora()
