import argparse
import tokenize
import random
import os

# args parsing
parser = argparse.ArgumentParser(description="a small and simple Python script packer", epilog="", formatter_class=argparse.RawTextHelpFormatter)

in_filename_default = ".crispy.output.py"
parser.add_argument("i", metavar="infile", help="specify the input file")
parser.add_argument("-o", metavar="outfile", default=in_filename_default, help="specify the output file")
parser.add_argument("-v", "--verbose", action='store_true', help="enable verbose output")

# write args to global vars
args = vars(parser.parse_args())
in_filename = args["i"]
out_filename = args["o"]
verbose = args["verbose"]





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
	global verbose
	output = ""
	size = 0

	try:
		# parse python code
		try:
			if verbose: print("\nReading code from {}... ".format(repr(filename)), end="")
			size = os.stat(filename).st_size
			output = read_python_code(filename)
			if verbose: print("Done!")

		# read file without python script optimisation
		except ParsingError:
			with open(filename, "r") as file: output = file.read()
			if verbose:
				print("Done!\n")
				print("Warning: Failed to parse input file as python code.")
				print("Continuing without Python script optimisation.")

	# exit on any other error
	except Exception as e:
		if verbose: print("ERROR!")
		print("\nError: {}\n\n".format(str(e)))
		exit(-1)

	return output, size





# create string of valid placeholders
def generate_placeholders(invalid):

	# alphabet of placeholders
	res = "!#$%&()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[]^_`abcdefghijklmnopqrstuvwxyz{|}~"
	
	# remove invalid characters
	for char in invalid:
		res = res.replace(char, "")

	# random shuffle for style
	temp = list(res)
	random.shuffle(temp)
	res = "".join(temp)

	return res





# generate substrings suitable for compression
def generate_substrings(string):
	strlen = len(string)
	minlen = min(strlen, 2)
	maxlen = strlen // 2

	# list of subs, that can safely be ignored
	ignore = [False] * strlen

	# generate substrings
	for size in range(minlen, maxlen):
		loops = strlen - 2*size + 1

		# list of items to ignore only within this iteration
		skip = [False] * (strlen - size + 1)

		for start in range(loops):

			# skip substring
			if skip[start] or ignore[start]: continue

			# create substring
			end = start + size
			sub = string[start:end]

			# find all occurences of sub in string
			count = 1
			index = start
			while True:
				index = string.find(sub, index + size - 1)
				if index < 0: break
				count += 1

				# skip all further occurences of this substring
				skip[index] = True

			# ignore subs, that only appear once
			if count < 2:
				ignore[start] = True
				continue

			# compute gain of substring
			gain = max(size-1, 0) * max(count-1, 0) - 2

			# yield substring
			yield sub, gain


# iterate over all substrings and find the best one
def find_best_substring(string):
	global verbose

	best_sub = ""
	best_score = 0
	counter = 0

	for sub, score in generate_substrings(string):
		counter += 1

		if score > best_score:
			best_sub = sub
			best_score = score

			# log best substring
			if verbose:
				print(" > substring found {} : {}".format(repr(sub), score))

	# print counter
	if verbose: print(" * {} substrings checked".format(counter))

	# return substring
	return best_sub, best_score


# compression loop
def compress_payload(payload, placeholders):
	global verbose
	keys_used = ""
	break_msg = "Out of placeholders!"

	for key in placeholders:

		# print result every iteration
		if verbose:
			print("\nCurrent code length: {} bytes".format(len(payload)))
			print(" > using placeholder: {}".format(repr(key)))

		# find substring for compression
		sub, score = find_best_substring(payload)

		# stop compession loop if gain is too low
		if score < 1:
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

	return payload, keys_used





# paste payload into decoder
def pack_payload(payload, placeholders):

	# raw decoder code
	decoder = "c={}\nfor i in{}:c=c.split(i);c=c.pop().join(c)\nexec(c)"
	
	# pack payload into decoder
	return decoder.format(payload, placeholders)


# export encoder
def write_to_file(filename, content):
	global verbose

	if verbose: print("\nSaving compressed script to {}... ".format(repr(filename)), end="")

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
	global in_filename, out_filename, verbose

	# read in payload
	payload, file_size = read_payload_from_file(in_filename)

	# save initial code size
	init_size = len(payload)
	if verbose:
		print("\nFile size: {} bytes".format(file_size))
		print("Code size: {} bytes".format(init_size))

	# generate and print keys
	keys = generate_placeholders(set(payload))
	if verbose: print("\n{} valid placeholders found: {}".format(len(keys), repr(keys)))

	# compress payload
	payload, keys = compress_payload(payload, keys)

	# pack payload into decoder
	escaped = repr(payload)
	output = pack_payload(escaped, repr(keys))

	# output file size
	if verbose:
		payload_size = len(payload)
		escaped_size = len(escaped)
		out_size = len(output)
		print("Initial size: {:4d} bytes".format(init_size))
		print("Payload size: {:4d} bytes".format(payload_size))
		print("Escaped code: {:4d} bytes".format(escaped_size))
		print("Decoder size: {:4d} bytes".format(out_size-escaped_size))
		print("Final script: {:4d} bytes".format(out_size))
		print("\nTotal gain: {} bytes".format(init_size-out_size))

	# output to file
	write_to_file(out_filename, output)





# handle keyboard interrupt
try: main()
except KeyboardInterrupt:
	if verbose: print("\n\nProgram has been stopped by user\n\n")