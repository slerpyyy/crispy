import argparse
import tokenize
import random


# args parsing
parser = argparse.ArgumentParser(description="a small and simple Python script packer", epilog="", formatter_class=argparse.RawTextHelpFormatter)

infile_default = ".crispy.output.py"
parser.add_argument("i", metavar="infile", help="specify the input file")
parser.add_argument("-o", metavar="outfile", default=infile_default, help="specify the output file")
parser.add_argument("-v", "--verbose", action='store_true', help="enable verbose output")
parser.add_argument("-p", "--progress", action='store_true', help="add periodic progress updates to verbose output\n(recommended for large payloads)")

# write args to vars
args = vars(parser.parse_args())
in_file_name = args["i"]
out_file_name = args["o"]
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
		if verbose:
			print("Done!\n")
			print("Warning: Failed to parse input file as python code.")
			print("Continuing without Python script optimisation.")

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
# ignoring the empty and whole string
def generate_substrings(a):
	for size in range(1, len(a)):
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





# method for escaping special characters in strings
def escape_string(string):
	table = {"\\":"\\\\", "\n":"\\n", "\t":"\\t", "\r":"\\r", "\"":"\\\"", "\'":"\\\'"}
	return string.translate(str.maketrans(table))

# paste payload into decoder
def pack_payload(payload, placeholders):
	decoder = "c=\"{}\"\nfor i in\"{}\":c=c.split(i);c=c.pop().join(c)\nexec(c)"
	return decoder.format(payload, placeholders)

def write_to_file(filename, content):
	if verbose: print("\nSaving compressed script to \"{}\"... ".format(filename), end="")

	try:
		with open(filename, "w") as file:
			file.write(content)
	
	except:
		if verbose: print("ERROR!")
		print("\nError: Failed to write to outfile\n\n")
		exit(-1)

	if verbose: print("Done!\n\n")





# The main function
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
	break_msg = "Out of placeholders!"
	for key in keys:

		# print result every iteration
		if verbose: print("\nCurrent code length: {} bytes".format(len(payload)))

		# find substring for compression
		sub, score = find_best_substring(payload)

		# stop compession loop if gain is too low
		if score < 3:
			break_msg = "Gain too low!"
			break

		# replace substring with key
		parts = list(payload.split(sub))
		parts.append(sub)
		payload = key.join(parts)

		# update list of used keys
		keys_used = key + keys_used

	# log out of placeholders loop break
	if verbose: print("\nCompression loop break: {}\n".format(break_msg))


	# pack payload into decoder
	payload = escape_string(payload)
	output = pack_payload(payload, keys_used)

	# output file size
	if verbose:
		code_size = len(payload)
		out_size = len(output)
		print("Initial code size: {} bytes".format(init_size))
		print("Escaped code size: {} bytes".format(code_size))
		print("Decompressor size: {} bytes".format(out_size-code_size))
		print("Final script size: {} bytes".format(out_size))

	# output to file
	write_to_file(out_file_name, output)





# handle keyboard interrupt
try: main()
except KeyboardInterrupt:
	if verbose: print("\n\nProgram has been stopped by user\n\n")