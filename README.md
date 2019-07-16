# crispy
*Simple Python Script Packer*

crispy is a small and simple Python script packer intended to be used in size-coding challenges. It uses dictionary compression to compact the script down to a small string, which is decoded and executed once the minified program is run. The packer itself is fully self-contained and doesn't require any additional packages beyond a basic python install.

## Usage
```
usage: cris.py [-mfvh] [-o outfile] infile

a small and simple Python script packer

  infile         specify the input file
  -o outfile     specify the output file

  -m, --minify   minify python script before compressing (experimental)
  -f, --fast     enable fast compression mode for testing purposes
  -v, --verbose  increase verbosity level (can be set multiple times)
  -h, --help     show this help message and exit
```

## Example
In the following example, we want to compress the file "input.py" and store the result in "output.py". We are going to use the following command:
```
python cris.py input.py -o output.py -m -vv
```

The "input.py" file in our example looks like this:
```py
print("Hello, hello!")
```

And the "output.py" file ended up looking like this:
```py
c='print("H~, h~!")~ello'
for i in'~':c=c.split(i);c=c.pop().join(c)
exec(c)
```

**Note:** The packer ended up increasing the size of the script, as the input file given in this example was already very small. Because the packer comes with some overhead, it is only really effective, when compressing files in the range of a few kilobytes.

## Extra Credit
This project is *heavily* inspired by RegPack, a javascript packer developed by Siorki. Go check out that GitHub repo if you haven't already:
https://github.com/Siorki/RegPack
