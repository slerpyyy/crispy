#!/usr/bin/python3

import argparse
import tokenize
import hashlib
import random
import os


# method for parsing command line arguments
def parse_cmd_args():
	global in_filename, out_filename, verbose

	# init args parser
	in_filename_default = ".crispy.output.py"
	parser = argparse.ArgumentParser(description="a small and simple Python script packer", epilog="", formatter_class=argparse.RawTextHelpFormatter)
	parser.add_argument("i", metavar="infile", help="specify the input file")
	parser.add_argument("-o", metavar="outfile", default=in_filename_default, help="specify the output file")
	parser.add_argument("-v", "--verbose", action="count", default=0, help="increase verbosity level")

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
		last_token = tokenize.COMMENT

		# read source code in tokens
		tokgen = tokenize.generate_tokens(file.readline)
		for token, text, (sline, scol), (eline, ecol), ltext in tokgen:

			# check for parsing errors
			if token == tokenize.ERRORTOKEN:
				raise ParsingError("Failed to parse python code.")

			# remove comments and empty lines
			if token != tokenize.COMMENT and token != tokenize.NL:

				# restore indentation
				if sline > last_line:
					last_col = 0
				if scol > last_col:
					indents = scol - last_col
					source_code += " " * indents

				# write code to buffer
				source_code += text

			# update vars
			last_line = eline
			last_col = ecol
			last_token = token

	# replace tabs with spaces
	source_code = source_code.replace("\t", " ")

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
			if verbose > 0: print("\nReading code from {}... ".format(repr(filename)), end="")
			size = os.stat(filename).st_size
			output = read_python_code(filename)
			if verbose > 0: print("Done!")

		# read file without python script optimisation
		except ParsingError:
			with open(filename, "r") as file: output = file.read()
			if verbose > 0:
				print("Done!\n")
				print("Warning: Failed to parse input file as python code.")
				print("Continuing without Python script optimisation.")

	# exit on any other error
	except Exception as e:
		if verbose > 0: print("ERROR!")
		print("\nError: Failed to read infile\n\n".format(str(e)))
		exit(-1)

	return output, size





# create string of valid placeholders
def generate_placeholders(invalid):

	# create set from string
	invalid = set(invalid)

	# generate placeholders
	res = ""
	for i in range(128):
		key = chr(i)

		# filter placeholder
		if key in invalid: continue
		if len(repr(repr(key))) > 5: continue
		
		res += key

	# random shuffle for style
	temp = list(res)
	random.shuffle(temp)
	res = "".join(temp)

	return res


# yields a string of characters and the number of times they appear
def inverted_histogram(string):

	# create histogram
	histo = {}
	for char in string:
		if char in histo: histo[char] += 1
		else: histo[char] = 1

	# invert histogram
	inv = {}
	for char, count in histo.items():
		if count in inv: inv[count] += char
		else: inv[count] = char

	# yield strings
	for key in sorted(inv.keys()):
		yield inv[key], key





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
		ignore_counter = 0

		for start in range(loops):

			# ignore substring
			if ignore[start]:
				ignore_counter += 1
				continue

			# skip substring
			if skip[start]: continue

			# create substring
			end = start + size
			sub = string[start:end]

			# find all occurences of sub in string
			count = 1
			index = start
			while True:
				index = string.find(sub, index + size)
				if index < 0: break
				count += 1

				# skip all further occurences of this substring
				skip[index] = True

			# ignore subs, that only appear once
			if count < 2:
				ignore[start] = True
				ignore_counter += 1
				continue

			# compute score of substring
			gain = size * count
			cost = size + count + 1
			score = gain - cost

			# generate token
			token = "{:x}:{:x};".format(start, size)

			yield sub, score, token

		# exit function if all substrings are set to ignore
		if ignore_counter == loops: return


# iterate over all substrings and find the best one
def find_best_substring(string):
	global verbose

	best_sub = ""
	best_score = 0
	best_token = None
	counter = 0

	for sub, score, token in generate_substrings(string):
		counter += 1

		if score > best_score:

			# log best substring
			if verbose > 1:
				print(" > substring found {} : {}".format(repr(sub), score))

			# update vars
			best_sub = sub
			best_score = score
			best_token = token

	# print counter
	if verbose > 1:
		print(" * {} substrings checked".format(counter))
		print(" * debug token: {}".format(repr(best_token)))

	# return substring
	return best_sub, best_score, best_token


# compression loop
def compress_payload(payload, placeholders):
	global verbose
	loop_counter = 0
	max_iter = len(placeholders)
	keys_used = ""
	break_msg = "Out of placeholders!"
	debug_hash = hashlib.md5()

	# log start of compression loop
	if verbose > 0:
		print("\nStarting compression loop")

	for key in placeholders:
		loop_counter += 1

		# print result every iteration
		if verbose > 1:
			print("\nIteration {} (max. {})".format(loop_counter, max_iter))
			print(" * current code: {} bytes".format(len(payload)))
			print(" * using placeholder: {}".format(repr(key)))

		# find substring for compression
		sub, score, token = find_best_substring(payload)

		# stop compession loop if gain is too low
		if score < 1:
			break_msg = "Gain too low!"
			break

		# update compression hash
		debug_hash.update(token.encode("ascii"))

		# replace substring with key
		parts = list(payload.split(sub))
		parts.append(sub)
		payload = key.join(parts)

		# update list of used keys
		keys_used = key + keys_used

	# log placeholders loop break
	if verbose > 0:
		print("\nCompression loop break: {}".format(break_msg))
		print("\nDebug hash: {}\n".format(debug_hash.hexdigest()))

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

	if verbose > 0: print("\nSaving compressed script to {}... ".format(repr(filename)), end="")

	try:
		with open(filename, "w") as file:
			file.write(content)

	except:
		if verbose > 0: print("ERROR!")
		print("\nError: Failed to write to outfile\n\n")
		exit(-1)

	if verbose > 0: print("Done!\n\n")





# The main function
def main():
	global in_filename, out_filename, verbose

	# parse command line arguments
	parse_cmd_args()

	# read in payload
	payload, file_size = read_payload_from_file(in_filename)

	# save initial code size
	init_size = len(payload)
	if verbose > 0:
		print("\nFile size: {} bytes".format(file_size))
		print("Code size: {} bytes".format(init_size))

	# generate and print keys
	keys = generate_placeholders(payload)
	if verbose > 0: print("\n{} valid placeholders found: {}".format(len(keys), repr(keys)))

	# print least used characters in payload
	if verbose > 0:
		for string, count in inverted_histogram(payload):
			if verbose < 2 and count > 16: break

			msg = " # {} appears {}"
			if len(string) > 1: msg = msg.replace("s", "")

			amount = "{} times".format(count)
			if count < 3: amount = (["once", "twice"])[count-1]
			
			print(msg.format(repr(string), amount))

	# compress payload
	payload, keys = compress_payload(payload, keys)

	# pack payload into decoder
	escaped = repr(payload)
	output = pack_payload(escaped, repr(keys))

	# output file size
	if verbose > 0:
		payload_size = len(payload)
		escaped_size = len(escaped)
		out_size = len(output)
		total_gain = init_size - out_size
		print("Initial size: {:4d} bytes".format(init_size))
		print("Payload size: {:4d} bytes".format(payload_size))
		print("Escaped code: {:4d} bytes".format(escaped_size))
		print("Decoder size: {:4d} bytes".format(out_size-escaped_size))
		print("Final script: {:4d} bytes".format(out_size))
		print("\nTotal gain: {} bytes".format(total_gain))

		if total_gain < 0:
			print("\nWarning: File size increased during compression!")

	# output to file
	write_to_file(out_filename, output)





# run main and handle keyboard interrupt
if __name__ == "__main__":
	try: main()
	except KeyboardInterrupt:
		if verbose > 0: print("\n\nProgram has been stopped by user\n\n")
