import argparse
import token, tokenize
import random


# args parsing
parser = argparse.ArgumentParser(description="A simple Python script minifier.")

parser.add_argument("infile", help="specifies the input file")
parser.add_argument("outfile", help="specifies the output file")
parser.add_argument("-v", "--verbose", action='store_true', help="enables verbose output")

args = vars(parser.parse_args())

in_file_name = args["infile"]
out_file_name = args["outfile"]
verbose = args["verbose"]


# read in code to compress
if verbose: print("\nReading code from \"{}\"... ".format(in_file_name), end="")

code = ""
with open(in_file_name) as file:
	
	last_lineno = -1
	last_col = 0

	# read source code in tokens
	tokgen = tokenize.generate_tokens(file.readline)
	for toktype, toktext, (slineno, scol), (elineno, ecol), ltext in tokgen:

		# remove comments and spacing
		if toktype == tokenize.COMMENT or toktype == tokenize.NL: continue

		# restore indentation
		if slineno > last_lineno: last_col = 0
		if scol > last_col: code += " " * (scol - last_col)

		# updating vars
		last_lineno = elineno
		last_col = ecol

		# write code to buffer
		code += toktext

if verbose: print("Done!")


# print initial code size
init_size = len(code)
if verbose: print("\nInitial code size: {} bytes".format(init_size))


# generate all substrings of a given string
# ignoring the empty and whole string
def generateSub(a):
	for size in range(1, len(a)):
		for start in range(len(a)-size+1):
			end = start + size
			yield a[start:end]


# score substring for use in zip compression
def scoreSub(a, b):
	size = len(b)
	count = len(a.split(b))-1
	return max(size-1, 0) * max(count-1, 0)


# create list of valid keys for substring replacement
keys  = "0123456789"
keys += "^~#!$%&}])<|{[(>`*.,_-+:;/=?@"
keys += "abcdefghijklmnopqrstuvwxyz"
keys += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
for char in code: keys = keys.replace(char, "")

keys = list(keys)
random.shuffle(keys)
keys = "".join(keys)


# print found keys
if verbose: print("\nValid placeholders found: {}".format(keys))


# compression loop
keys_used = ""
for key in keys:

	# print result every iteration
	if verbose: print("\nCurrent code length: {} bytes".format(len(code)))

	# iterate over all substrings
	# and find the best one
	best_sub = ""
	best_score = 0
	counter = 0
	size = len(code)
	iterations = size * (size + 1) // 2 - 1

	# print total number of iterations
	if verbose: print(" * {} substrings to search".format(iterations))

	for sub in generateSub(code):
		score = scoreSub(code, sub)
		counter += 1

		if verbose and (size > 2048) and (counter % (iterations // 32) == 0):
			print(" * {:3d}% completed".format(round(100 * counter // iterations, 2)))

		if score > best_score:
			best_sub = sub
			best_score = score

			# log best substring
			if verbose: print(" > substring found \"{}\" : {}".format(sub.replace("\n", "."), score))

	# stop compession loop if gain is too low
	if best_score < 3:
		if verbose: print("\nCompression loop break: Gain too low!\n")
		break

	# replace substring with key
	parts = list(code.split(best_sub))
	parts.append(best_sub)
	code = key.join(parts)
	keys_used = key + keys_used


else:
	# log out of placeholders loop break
	if verbose: print("\nCompression loop break: Out of placeholders!\n")


# escape code
escape = {"\\":"\\\\", "\n":"\\n", "\t":"\\t", "\r":"\\r", "\"":"\\\"", "\'":"\\\'"}
code = code.translate(str.maketrans(escape))


# pack code into decoder
decoder = "c=\"{}\"\nfor i in\"{}\":c=c.split(i);c=c.pop().join(c)\nexec(c)"
output = decoder.format(code, keys_used)


# output file size
if verbose:
	print("Initial code size: {} bytes".format(init_size))
	print("Escaped code size: {} bytes".format(len(code)))
	print("Decompressor size: {} bytes".format(len(output)-len(code)))
	print("Final script size: {} bytes".format(len(output)))


# output to file
if verbose: print("\nSaving compressed script to \"{}\"... ".format(out_file_name), end="")

with open(out_file_name, "w") as file:
	file.write(output)

if verbose: print("Done!\n\n")