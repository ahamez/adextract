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
VERSION     = "1.0.0"
DESCRIPTION =\
"""Extract AsciiDoc from source file and output text readable by AsciiDoc."""

################################################################################
# Default to C-like commments
DEFAULT_START_TAG = '/*'
DEFAULT_END_TAG   = "*/"

################################################################################
DEFAULT_CACHE_DIR  = os.path.join(os.path.expanduser('~'), '.adextract_cache')
DEFAULT_CACHE_SIZE = 1024 * 1024 * 10

################################################################################
def configure():

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.add_argument('--numbered', action='store_true', default=False)
  parser.add_argument( '--no-cache', action='store_false', default=True
                     , dest='doCaching'
                     )
  parser.add_argument( '--cache-size', action='store'
                     , default=DEFAULT_CACHE_SIZE, dest='cacheSize'
                     )
  parser.add_argument( '--cache-dir', action='store'
                     , default=DEFAULT_CACHE_DIR, dest='cacheDir')
  parser.add_argument( '--start', action='store'
                     , default=DEFAULT_START_TAG, dest='startTag'
                     )
  parser.add_argument( '--end', action='store'
                     , default=DEFAULT_END_TAG, dest='endTag'
                     )
  parser.add_argument( 'infile', nargs='?', type=argparse.FileType('r')
                     , default=sys.stdin
                     )
  parser.add_argument( 'outfile', nargs='?', type=argparse.FileType('w')
                     , default=sys.stdout
                     )
  parser.add_argument( 'errors', nargs='?', type=argparse.FileType('w')
                     , default=sys.stderr
                     )
  parser.add_argument( '-a', '--attribute', action='append', dest='attributes'
                     , default=[]
                     )
  parser.add_argument('-b', '--backend', default='html')

  conf, unkown = parser.parse_known_args()

  conf.cacheDir = os.path.expanduser(conf.cacheDir)

  conf.errors.write("'" + conf.startTag + "'\n")
  conf.errors.write("'" + conf.endTag + "'\n")

  # Unkown arguments will be passed to the nested AsciiDoc.
  return conf, unkown

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

  def __init__(self, arg):
    super(CodeBlock, self).__init__()
    self.content = arg

  def __len__(self):
    return len(self.content)

  def __iter__(self):
    for l in self.content:
      yield l

################################################################################
def parseBlocks(conf, data, output):

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

  # At this point, the list of blocks is an alternation of CodeBlocks and
  # AsciiDocBlocks. The former type being always the first one and last one 
  # of the list of blocks (being possibly empty).

  currentLine = 1
  for b in blocks:

    if isinstance( b, CodeBlock):
      if b:
        output.write("----\n")
        for l in b:
          if conf.numbered:
            output.write("{:02d}    ".format(currentLine) + l + "\n")
            currentLine += 1
          else:
            output.write(l + "\n")
        output.write("----\n")
      else:
        continue

    else:
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
  outFile = hashlib.sha1(data).hexdigest()

  # The path to the file that will be passed to the calling AsciiDoc.
  # It's an absolute path if caching is enable. Otherwise, it's the
  # same as outFile.
  resFile = os.path.join(conf.cacheDir if conf.doCaching else "", outFile) 

  if not conf.doCaching or not os.path.exists(resFile):

    # The temporary file must be in the same repository as the main
    # document, otherwise paths like imagesdir would be incorrect.
    with tempfile.TemporaryFile() as tmpFile:

      # Fill the temporary file with the data to be processed.
      parseBlocks(conf, data, tmpFile)

      # Rewind The temporary file as the preceding call wrote into it.
      tmpFile.seek(0)

      # Create and configure asciidoc.
      asciidoc = asciidocapi.AsciiDocAPI()
      asciidoc.attributes =\
        dict( (x[0], x[2])
              for x in (p.partition("=") for p in conf.attributes)
            )
      for o in asciiDocOptions:
        asciidoc.options(o)

      # Launch AsciiDoc.
      asciidoc.execute(tmpFile, outfile=outFile, backend=conf.backend)

      if conf.doCaching:
        # Move the result into the cache directory.
        shutil.move(outFile, resFile)

  # Handle the result to AsciiDoc.
  with open(resFile, 'r') as f:
    conf.outfile.write(f.read())

  # If there is no caching, the file from the nested AsciiDoc was not moved.
  if not conf.doCaching:
    os.remove(resFile)

  # Cleanup the cache in a LRU way if needed.
  if conf.doCaching:
    files = sorted( [ os.path.join(conf.cacheDir, f) 
                     for f in os.listdir(conf.cacheDir)
                    ]
                  , key=os.path.getatime
                  )
    while sum(os.path.getsize(f) for f in files) > conf.cacheSize and files:
      os.remove(files.pop())

################################################################################
if __name__ == "__main__":

  try:
    main(*configure())

  except (KeyboardInterrupt, SystemExit):
    pass

  sys.exit(0)
