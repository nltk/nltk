import yaml

"""
Register YAML tags in the NLTK namespace with the YAML loader, by telling it
what module and class to look for.

NLTK uses simple '!' tags to mark the types of objects, but the fully-qualified
"tag:nltk.org,2011:" prefix is also accepted in case anyone ends up
using it.
"""

def custom_import(name):
    components = name.split('.')
    module_path = '.'.join(components[:-1])
    mod = __import__(module_path)
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

def metaloader(classpath):
    def loader(*args, **kwds):
        classref = custom_import(classpath)
        return classref.from_yaml(*args, **kwds)
    return loader

def register_tag(tag, classpath):
    yaml.add_constructor(u'!'+tag, metaloader(classpath))
    yaml.add_constructor(u'tag:nltk.org,2011:'+tag,
                         metaloader(classpath))

register_tag(u'tag.Unigram', 'nltk.tag.unigram.Unigram')
register_tag(u'tag.Brill', 'nltk.tag.brill.Brill')

__all__ = ['custom_import', 'metaloader', 'register_tag']
