import argparse
import tokenize
import random


# args parsing
parser = argparse.ArgumentParser(description="A simple Python script minifier.")

infile_default = ".crispy.out"
parser.add_argument("infile", help="specify the input file")
parser.add_argument("-o", "--outfile", default=infile_default, help="specify the output file (the default is \"{}\")".format(infile_default))
parser.add_argument("-v", "--verbose", action='store_true', help="enable verbose output")
parser.add_argument("-p", "--progress", action='store_true', help="add periodic progress updates to verbose output (recommendet for large payloads)")


# write args to vars
args = vars(parser.parse_args())
in_file_name = args["infile"]
out_file_name = args["outfile"]
verbose = args["verbose"]
progress = args["progress"]


# define ParsingError
class ParsingError(Exception): pass


# method for reading python source code
def read_python_code(filename):
	source_code = ""

	with open(filename, "r") as file:
		last_line = -1
		last_col = 0

		# read source code in tokens
		tokgen = tokenize.generate_tokens(file.readline)
		for token, text, (sline, scol), (eline, ecol), ltext in tokgen:

			# check for parsing errors
			if token == tokenize.ERRORTOKEN:
				raise ParsingError("Failed to parse python code.")

			# remove comments and empty lines
			if token == tokenize.COMMENT or token == tokenize.NL: continue

			# restore indentation
			if sline > last_line: last_col = 0
			if scol > last_col: source_code += " " * (scol - last_col)
			last_line, last_col = eline, ecol

			# write code to buffer
			source_code += text

	# return the read source code
	return source_code


# methode to read in code to compress
def read_payload_from_file(filename):
	output = ""

	# parse python code
	try:
		if verbose: print("\nReading code from \"{}\"... ".format(filename), end="")
		output = read_python_code(filename)
		if verbose: print("Done!")

	# exit if file not found
	except FileNotFoundError:
		if verbose: print("ERROR!")
		print("\nError: Input File not found\n\n")
		exit(-1)

	# read file without python script optimisation
	except ParsingError:
		with open(filename, "r") as file: output = file.read()
		if verbose: print("Done!\n\nWarning: Failed to parse input file as python code.\nContinuing without Python script optimisation.")

	return output


# create string of valid placeholders
def generate_placeholders(invalid):

	# alphabet of placeholders
	res  = "0123456789"
	res += "^~#!$%&}])<|{[(>`*.,_-+:;/=?@"
	res += "abcdefghijklmnopqrstuvwxyz"
	res += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
	
	# remove invalid characters
	for char in invalid:
		res = res.replace(char, "")

	# random shuffle for style
	temp = list(res)
	random.shuffle(temp)
	res = "".join(temp)

	return res


# generate all substrings of a given string
# with given minimum length and ignoring the whole string
def generate_substrings(a, minlen=2):
	minlen = min(minlen, len(a))
	for size in range(minlen, len(a)):
		for start in range(len(a)-size+1):
			end = start + size
			yield a[start:end]


# score substring for use in zip compression
def score_substring(a, b):
	size = len(b)
	count = len(a.split(b))-1
	return max(size-1, 0) * max(count-1, 0)


# iterate over all substrings and find the best one
def find_best_substring(string):

	# setup vars
	best_sub = ""
	best_score = 0
	counter = 0
	size = len(string)
	iterations = size * (size + 1) // 2 - 1

	# print total number of iterations
	if verbose: print(" * {} substrings to search".format(iterations))

	for sub in generate_substrings(string):
		score = score_substring(string, sub)
		counter += 1

		# periodic status updates
		if verbose and progress and (counter % (iterations // 32) == 0):
			print(" * {:3d}% completed".format(round(100 * counter // iterations, 2)))

		if score > best_score:
			best_sub = sub
			best_score = score

			# log best substring
			if verbose: print(" > substring found \"{}\" : {}".format(sub.replace("\n", "."), score))

	# return substring
	return best_sub, best_score


def main():

	# read in payload
	payload = read_payload_from_file(in_file_name)


	# print initial code size
	init_size = len(payload)
	if verbose: print("\nInitial code size: {} bytes".format(init_size))


	# generate and print keys
	keys = generate_placeholders(set(payload))
	if verbose: print("\n{} valid placeholders found: {}".format(len(keys), keys))


	# compression loop
	keys_used = ""
	for key in keys:

		# print result every iteration
		if verbose: print("\nCurrent code length: {} bytes".format(len(payload)))

		# find substring for compression
		sub, score = find_best_substring(payload)

		# stop compession loop if gain is too low
		if score < 3:
			if verbose: print("\nCompression loop break: Gain too low!\n")
			break

		# replace substring with key
		parts = list(payload.split(sub))
		parts.append(sub)
		payload = key.join(parts)

		# update list of used keys
		keys_used = key + keys_used


	else:
		# log out of placeholders loop break
		if verbose: print("\nCompression loop break: Out of placeholders!\n")


	# escape payload
	escape = {"\\":"\\\\", "\n":"\\n", "\t":"\\t", "\r":"\\r", "\"":"\\\"", "\'":"\\\'"}
	payload = payload.translate(str.maketrans(escape))


	# pack payload into decoder
	decoder = "c=\"{}\"\nfor i in\"{}\":c=c.split(i);c=c.pop().join(c)\nexec(c)"
	output = decoder.format(payload, keys_used)


	# output file size
	if verbose:
		code_size = len(payload)
		out_size = len(output)
		print("Initial code size: {} bytes".format(init_size))
		print("Escaped code size: {} bytes".format(code_size))
		print("Decompressor size: {} bytes".format(out_size-code_size))
		print("Final script size: {} bytes".format(out_size))


	# output to file
	if verbose: print("\nSaving compressed script to \"{}\"... ".format(out_file_name), end="")

	try:
		with open(out_file_name, "w") as file:
			file.write(output)
	
	except:
		if verbose: print("ERROR!")
		print("\nError: Failed to write to outfile\n\n")
		exit(-1)

	if verbose: print("Done!\n\n")


# handle keyboard interrupt
try: main()
except KeyboardInterrupt:
	if verbose: print("\n\nProgram has been stopped by user\n\n")