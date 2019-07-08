# crispy
*Simple Python Script Packer*

crispy is a small and simple Python script packer intended to be used in size-coding challenges. It uses dictionary compression to compact the script down to a small string, which is decoded and executed once the minified program is run. The packer itself is fully self-contained and doesn't require any additional packages beyond a basic python install.

## Usage
```
usage: cris.py [-h] [-o outfile] [-v] [-p] infile

a small and simple Python script packer

positional arguments:
  infile          specify the input file

optional arguments:
  -h, --help      show this help message and exit
  -o outfile      specify the output file
  -v, --verbose   enable verbose output
```

## Example
In the following example, we want to compress the file "input.py" and store the result in "output.py". We are going to use the following command:
```
python cris.py input.py -o output.py -v
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
