--------------------------------------------------------------------------------
1. Introduction

adextract.py is a tool to extract AsciiDoc annotations from a source file. The
pinciple is really simple: you put AsciiDoc stuff in your source comments and
adextract.py extract them and put your code into AsciiDoc listing blocks. It
then handles this intermediary result to AsciiDoc. The final result is the
output provided by AsciiDoc.

Thus, you can still compile your code, while still fully describing it using
AsciiDoc syntax. It is very useful to write a complete documentation with source
files and checking that they compile.

It works both as an AsciiDoc filter and as a stand-alone tool. In both cases, a
cache mechanism is provided.

--------------------------------------------------------------------------------
2. Requirements

- Python 2.7 or higher  (http://www.python.org)
- AsciiDoc 8.6.4 or higher (http://www.methods.co.nz/asciidoc)

--------------------------------------------------------------------------------
3. Usage as an AsciiDoc filter

First, install adextract.py as a filter as stated on the AsciiDoc website:
http://www.methods.co.nz/asciidoc/manpage.html :

  asciidoc --filter install adextract.zip

Also, you can just create a 'filters' directory in your AsciiDoc document main
directory and copy the 'adextract' top directory into it.

The typical use-case of this filter is to include the code source file to be
processed in a passthrough block (adextract only work on this block type), whose
style attribute is 'adextract':

    [adextract]
    ++++
    include::foo.c[]
    ++++

Note that the enclosed source file does not need to be a complete AsciiDoc file
per se, as the filter instructs AsciiDoc to remove headers and footers.

You can also provide the 'numbered' attribute to number source code lines:

    [adextract, numbered]
    ++++
    include::foo.c[]
    ++++

The file foo.c could be something like:

    /*{
    Here, some _AsciiDoc_ stuff.
    }*/
    
    int main(int argc, char** argv)
    {
      return 0;
    }
    
    /*{
    Some other *AsciiDoc* stuff.
    }*/

There must not be spaces between the '{' and '}' and the comments delimiters.
Otherwise, the comment will be interpreted as standard comment.

Note that the default handled comments are C-like: '/*' and '*/'. You can change
this by specifying the 'start' and 'end' attributes (don't forget the quotes
around the delimiters):

    [adextract, start='(*', end='*)']
    ++++
    include::foo.sml[]
    ++++

Finally, attributes like imagesdir are passed to the nested AsciiDoc, thus the
paths are relative to the enclosing AsciiDoc document. However, they will not
override attributes that you might have set in your source code.

--------------------------------------------------------------------------------
4. Usage as a stand-alone tool

The basic usage is just to call adextract.py on your source file:

    adextract.py foo.c foo.html

Note that this time the source file should be a complete AsciiDoc file. However,
any option that is not recognize by adextract.py is directly given to AsciiDoc.
Thus you could do:

    adextract --no-header-footer foo.c foo.html

See adextract.py --help for more options.
