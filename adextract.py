#! /usr/bin/env python

import argparse
import asciidocapi
import errno
import hashlib
import os
import os.path
import re
import shutil
import sys
import tempfile

################################################################################
VERSION     = "1.0.1"
DESCRIPTION =\
"""Extract AsciiDoc from source file and output the result of AsciiDoc."""

################################################################################
# Default to C-like commments
DEFAULT_START_TAG = '/*'
DEFAULT_END_TAG   = "*/"

################################################################################
DEFAULT_CACHE_DIR  = os.path.join('~', '.adextract_cache')
DEFAULT_CACHE_SIZE = 1024 * 1024 * 10

################################################################################
def configure():

  parser = argparse.ArgumentParser( description=DESCRIPTION
                                  , epilog="Any other option is passed as is \
                                            to AsciiDoc.")
  parser.add_argument( '--version', action='version'
                     , version='%(prog)s '+ VERSION
                     )
  parser.add_argument( '--numbered', action='store_true', default=False
                     , help="Number source code lines."
                     )
  parser.add_argument( '--no-cache', action='store_false', default=True
                     , dest='doCaching'
                     , help='Disable the cache.'
                     )
  parser.add_argument( '--cache-size', action='store'
                     , default=DEFAULT_CACHE_SIZE, dest='cacheSize'
                     , help='Set the cache size.'
                     )
  parser.add_argument( '--cache-dir', action='store'
                     , default=DEFAULT_CACHE_DIR, dest='cacheDir'
                     , help='Set the cache directory. Default to '
                            + DEFAULT_CACHE_DIR + '.'
                     )
  parser.add_argument( '--start', action='store'
                     , default=DEFAULT_START_TAG, dest='startTag'
                     , help='Set the starting delimiter of a comment.'
                     )
  parser.add_argument( '--end', action='store'
                     , default=DEFAULT_END_TAG, dest='endTag'
                     , help='Set the ending delimiter of a comment.'
                     )
  parser.add_argument( 'infile', nargs='?', type=argparse.FileType('r')
                     , default=sys.stdin
                     , help='The file to process.' +
                            " If '-', uses the standard input."
                     )
  parser.add_argument( 'outfile', nargs='?', type=argparse.FileType('w')
                     , default=sys.stdout
                     , help='The processed result.' +
                            " If '-', uses the standard output."
                     )
  parser.add_argument( 'errfile', nargs='?', type=argparse.FileType('w')
                     , default=sys.stderr
                     , help='Where to print errors and warnings. ' +
                            " If '-', uses the standard error output."
                     )
  parser.add_argument( '-a', '--attribute', action='append', dest='attributes'
                     , default=[]
                     , help='Set the attributes to be passed to AsciiDoc.' +
                            ' Can be repeated.'
                     )
  parser.add_argument( '-b', '--backend', default='html'
                     , help='Set the backend for AsciiDoc.'
                     )

  conf, unknown = parser.parse_known_args()

  conf.cacheDir = os.path.expanduser(conf.cacheDir)

  if conf.errfile == '-':
    conf.infile = sys.stderr

  # Unkown arguments will be passed to the nested AsciiDoc.
  return conf, unknown

################################################################################
class AsciiDocBlock(object):

  def __init__(self, arg):
    super(AsciiDocBlock, self).__init__()
    self.content = arg

  def __len__(self):
    return len(self.content)

  def __str__(self):
    return self.content

################################################################################
class CodeBlock(object):

  """CodeBlock is actually a list of source code lines."""

  currentLine = 1
  numbered    = False

  def __init__(self, arg):
    super(CodeBlock, self).__init__()
    self.content  = arg

  def __str__(self):

    res = ""

    if self.content:
      res = "----\n"
      for l in self.content:
        if self.__class__.numbered:
          res += "{:02d}    ".format(self.__class__.currentLine) + l + "\n"
          self.__class__.currentLine += 1
        else:
          res += l + "\n"
      res += "----\n"

    return res

################################################################################
def parseBlocks(conf, data, output):

  CodeBlock.numbered = conf.numbered

  startTag = re.escape(conf.startTag)
  endTag   = re.escape(conf.endTag)

  asciiDocRE = re.compile( startTag
                         + """\{(.*?)\}"""
                         + endTag
                         + """\n?"""
                         , re.DOTALL
                         )

  pos            = 0
  blocks         = []

  while pos < len(data):
    
    m = asciiDocRE.search(data, pos)

    if not m:
      break

    blocks.append( CodeBlock(data[pos : m.start(0)].splitlines()) )
    blocks.append( AsciiDocBlock(m.group(1)) )

    pos = m.end(0)

  blocks.append( CodeBlock(data[pos:].splitlines()))

  for b in blocks:
    output.write(str(b) + "\n")

################################################################################
def main(conf, asciiDocOptions):

  if conf.doCaching:
    # Do we have a cache directory? If not, we can live without it.
    try:
      os.mkdir(conf.cacheDir)
    except OSError as e:
      if e.errno != errno.EEXIST:
        conf.doCaching = False

    if not os.access(conf.cacheDir, os.R_OK | os.W_OK):
      conf.doCaching = False

  # The data to be transformed into a readable shape for the nested AsciiDoc.
  data = conf.infile.read()

  # The name of the file that the nested AsciiDoc will create.
  outFile = None
  if conf.doCaching:
    h = hashlib.sha1()
    h.update(data)
    h.update("".join(conf.attributes))
    h.update("".join(asciiDocOptions))
    h.update(conf.backend)
    h.update(str(conf.numbered))
    h.update(conf.startTag)
    h.update(conf.endTag)
    h.update(VERSION)
    outFile = os.path.join(conf.cacheDir,h.hexdigest())
  else:
    outFile = "adextract_asciidoc_output.tmp"

  if not conf.doCaching or not os.path.exists(outFile):

    with tempfile.TemporaryFile() as tmpFile:

      # Fill the temporary file with the data to be processed.
      parseBlocks(conf, data, tmpFile)

      # Rewind The temporary file as the preceding call wrote into it.
      tmpFile.seek(0)

      # Create and configure asciidoc.
      asciidoc = asciidocapi.AsciiDocAPI()
      asciidoc.attributes =\
        {x[0] : x[2] for x in (p.partition("=") for p in conf.attributes)}
      for o in asciiDocOptions:
        asciidoc.options(o)

      # Launch AsciiDoc.
      asciidoc.execute(tmpFile, outfile=outFile, backend=conf.backend)

  # Handle the result to AsciiDoc.
  with open(outFile, 'r') as f:
    conf.outfile.write(f.read())

  # If there is no caching, the file from the nested AsciiDoc was not moved.
  if not conf.doCaching:
    os.remove(outFile)

  # Cleanup the cache in a LRU way if needed.
  if conf.doCaching:
    files = sorted( [ os.path.join(conf.cacheDir, f) 
                     for f in os.listdir(conf.cacheDir)
                    ]
                  , key=os.path.getatime
                  )
    sizes = [os.path.getsize(f) for f in files]
    while sum(sizes) > conf.cacheSize and files:
      os.remove(files.pop(0))
      del sizes[0]

################################################################################
if __name__ == "__main__":

  try:
    main(*configure())

  except (KeyboardInterrupt, SystemExit):
    pass

  sys.exit(0)
