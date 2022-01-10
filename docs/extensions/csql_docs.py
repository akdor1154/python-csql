from sphinx.application import Sphinx
from typing import *

def setup(app: Sphinx):
    #print('hello!')
    app.connect('autodoc-process-docstring', process_docstring)
    app.connect('autodoc-process-signature', process_signature)

def process_docstring(app: Sphinx, what: str, name: str, obj: Any, options: Any, lines: List[str]):
    #print(f'{what=}: {name=}')
    #for l in lines: print(l)
    return lines

def process_signature(app: Sphinx, what: str, name: str, obj: Any, options: Any, signature: str, return_annotation: str):
    #print(f'signature for {what=}: {name=}')
    #print(f'{signature=} {return_annotation=}')

    # If I've manually suppressed a class's constructor with 
    # .. autoclass:: Class()
    # then suppress the type annotations appearing as well.

    if signature == '()' and return_annotation is None:
        annotations = app.env.temp_data.get('annotations', {})
        annotation = annotations.get(name, {})
        annotation.clear()
    

    return
