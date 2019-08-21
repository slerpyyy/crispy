#!/usr/bin/python3
import argparse
import tokenize
import hashlib
import random
import io



# method for parsing command line arguments
def parse_cmd_args():
	global in_filename, out_filename, minify, latin1, hex_mode, fast_mode, verbose

	# edit help message
	class CustomArgumentParser(argparse.ArgumentParser):
		def format_help(self):
			text = super().format_help()
			lines = text.split("\n")

			# manually pushing lines around
			# (ugly and horrible, but I don't have better options)
			lines.pop(4); lines.pop(6)
			lines.insert(12, lines.pop(6))
			lines.insert(6, lines.pop(5))

			text = "\n".join(lines)
			return "\n" + text + "\n\n"

	# init args parser object
	parser = CustomArgumentParser(
		usage="%(prog)s [-mlxfvh] [-o outfile] infile",
		description="a small and simple Python script packer",
		formatter_class=argparse.RawTextHelpFormatter
	)
	
	# set cmd args
	in_filename_default = ".crispy.output.py"
	parser.add_argument("i", metavar="infile", help="specify the input file")
	parser.add_argument("-o", metavar="outfile", default=in_filename_default, help="specify the output file")
	parser.add_argument("-m", "--minify", action="store_true", help="minify python script before compressing")
	parser.add_argument("-l", "--latin1", action="store_true", help="allow extended ascii chars as placeholders")
	parser.add_argument("-x", "--hex", action="store_true", help="turn rare chars into hex numbers (experimental)")
	parser.add_argument("-f", "--fast", action="store_true", help="enable fast compression mode for testing purposes")
	parser.add_argument("-v", "--verbose", action="count", default=0, help="increase verbosity level (can be set multiple times)")

	# write args to global vars
	args = vars(parser.parse_args())
	in_filename = args["i"]
	out_filename = args["o"]
	minify = args["minify"]
	latin1 = args["latin1"]
	hex_mode = args["hex"]
	fast_mode = args["fast"]
	verbose = args["verbose"]





# method to read in code to compress
def read_payload_from_file(filename):
	global verbose
	output = ""
	size = 0

	# read code
	try:
		if verbose > 0: print("\nReading code from {}".format(repr(filename)), end="... ")
		
		with open(filename, "r") as file:
			output = file.read()
			size = len(output)

		if verbose > 0: print("Done!")

	# exit on any other error
	except Exception as e:
		if verbose > 0: print("ERROR!")
		print("\nError: Failed to read infile\n\n")
		exit(-1)

	return output, size





# method for minifying python source code
def minify_iteration(input_code):
	
	# setup vars
	output_code = ""
	last_token = None
	last_erow  = -1
	last_ecol = 0

	# setup generators
	linegen = io.StringIO(input_code).readline
	tokgen = tokenize.generate_tokens(linegen)

	# read source code in tokens
	for token, text, (srow , scol), (erow , ecol), line in tokgen:

		# check for parsing errors
		if token == tokenize.ERRORTOKEN:
			raise tokenize.TokenError("Failed to parse python code")

		# choose when to keep a token
		keep_token = (token != tokenize.COMMENT) and (token != tokenize.NL) \
		and not ((last_token == tokenize.NEWLINE) and (token == tokenize.STRING))

		# keep token if flag is set
		if keep_token:

			# set indent flag
			set_indents = (token != tokenize.NEWLINE) \
			and (token != tokenize.STRING) and (last_token != tokenize.STRING) \
			and (token != tokenize.OP) and (last_token != tokenize.OP)

			# restore indentation
			if srow > last_erow:
				last_ecol = 0
			if (scol > last_ecol) and set_indents:
				indents = scol - last_ecol
				output_code += " " * indents

			# convert tabs to spaces
			if token == tokenize.INDENT:
				text = text.replace("\t", " ")

			# convert windows line breaks to proper line breaks
			if token == tokenize.NEWLINE:
				text = "\n"

			# write code to buffer
			output_code += text

		# update vars
		last_erow  = erow 
		last_ecol = ecol

		if (token != tokenize.DEDENT) and (token != tokenize.INDENT):
			last_token = token

	# return the read source code
	return output_code


# minify code iteratively
def python_minifier(code):
	global verbose, fast_mode

	try:
		if verbose > 0: print("\nRunning python code minifier")

		last_size = len(code)
		while True:

			# minify once
			code = minify_iteration(code)
			curr_size = len(code)

			# debug message
			if verbose > 0: print(" - code size: {} bytes ({} bytes)".format(curr_size, curr_size-last_size))

			# break early in fast mode
			if fast_mode: break

			# check for gain
			if curr_size == last_size: break
			last_size = curr_size

	# break on token error
	except tokenize.TokenError:
		if verbose > 0:
			print("WARNING!\n")
			print("Warning: Failed to parse input file as python code.")
			print("Continuing without Python script optimization.")

	return code





# create string of valid placeholders
def generate_placeholders(invalid):
	global latin1

	# create set from string
	invalid = set(invalid)

	# set number of iterations
	scope = 0x80
	if latin1: scope = 0x100

	# generate placeholders
	keys = ""
	for i in range(scope):
		key = chr(i)

		# filter placeholder
		if key in invalid: continue
		keys += key

	# random shuffle for style
	keys = list(keys)
	random.shuffle(keys)

	# sort after length
	escape_cost = lambda x: len(repr(x + '"'))
	keys = sorted(keys, key=escape_cost)

	# return result
	return "".join(keys)


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


# replace rare characters in payload with their hex representation to free up placeholders
def rare_to_hex(code, inv_histo, escape):
	global fast_mode

	# set max number of occurrences for rare chars
	# (vague unexplained hand-wavy placeholder math)
	all_counts = [count for _, count in inv_histo]
	first_half = all_counts[:len(all_counts)//2]
	threshold = sum(first_half)/max(len(first_half),1)

	# shortcut for fast mode
	if fast_mode: threshold = min(threshold, 4)

	# get string of chars to replace
	rare_chars = ""
	for string, count in inv_histo:
		if count > threshold: break
		rare_chars += string

	# always translate escape character first
	rare_chars = escape + rare_chars.replace(escape, "")

	# remove literals
	for num in range(16):
		literal = "{:x}".format(num)
		rare_chars = rare_chars.replace(literal, "")

	# replace rare chars
	for char in rare_chars:
		hex_repr = escape + "{:02x}".format(ord(char))
		code = code.replace(char, hex_repr)

	return code, rare_chars





# generate substrings suitable for compression
def generate_substrings(string):
	global fast_mode
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

			# find all occurrences of sub in string
			count = 1
			index = start
			overlap = index + size
			while True:
				index = string.find(sub, index + 1)
				if index < 0: break
				
				# skip all further occurrences of this substring
				skip[index] = True

				# increment counter, if the substrings do not overlap
				if index >= overlap:
					overlap = index + size
					count += 1

			# ignore subs, that only appear once
			if count < 2:
				ignore[start] = True
				ignore_counter += 1
				continue

			# generate token
			token = "{:x}:{:x};".format(start, size)

			yield sub, size, count, token

		# exit function if all substrings are set to be ignored or is fast mode is enabled
		if fast_mode or (ignore_counter == loops): return


# iterate over all substrings and find the best one
def find_best_substring(string, key):
	global verbose

	best_sub = ""
	best_score = 0
	best_token = ""
	counter = 0

	# output additional cost
	key_cost = len(repr(key + '"')) - 3
	if verbose > 2:
		print(" * cost of placeholder: {}".format(key_cost))

	# loop over substrings
	for sub, size, count, token in generate_substrings(string):
		counter += 1

		# compute score of substring
		gain = size * count
		cost = size + key_cost * (count + 2)
		score = gain - cost

		if score > best_score:

			# log best substring
			if verbose > 2:
				print(" > substring found {} : {}".format(repr(sub), score))

			# update vars
			best_sub = sub
			best_score = score
			best_token = token

	# print counter
	if verbose > 2:
		print(" * {} substrings checked".format(counter))
		print(" * debug token: {}".format(repr(best_token)))

	# return substring
	return best_sub, best_score, best_token


# compression loop
def compress_payload(payload, placeholders):
	global verbose, fast_mode
	loop_counter = 0
	max_iter = len(placeholders)
	keys_used = ""
	break_msg = "Out of placeholders!"
	debug_hash = hashlib.md5()

	# log start of compression loop
	if verbose > 0:
		print("\nStarting compression loop")
		if verbose == 2: print()

	for key in placeholders:
		loop_counter += 1

		# print result every iteration
		if verbose > 2:
			print("\nIteration {} (max. {})".format(loop_counter, max_iter))
			print(" * current code: {} bytes".format(len(payload)))
			print(" * using placeholder: {}".format(repr(key)))

		# find substring for compression
		sub, score, token = find_best_substring(payload, key)

		# less verbose output
		if verbose == 2:
			print("Iter {:03d}/{:03d}: {} {}".format(loop_counter, max_iter, repr(key), score))

		# stop compression loop if gain is too low
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

		# break on fast mode
		if fast_mode:
			break_msg = "Fast mode is enabled!"
			break

	# log placeholders loop break
	if verbose > 0:
		print("\nCompression loop break: {}".format(break_msg))
		print("\nDebug hash: {}\n".format(debug_hash.hexdigest()))

	return payload, keys_used





# paste payload into decoder
def pack_payload(payload, placeholders, escape):
	global latin1, hex_mode

	# raw decoder code
	decoder = "c={}\nfor i in{}:a=c.split(i);c=a.pop().join(a)\n".format(payload, placeholders)

	# specify encoding if necessary
	if latin1:
		decoder = "#coding=l1\n" + decoder

	# add code for hex decoder
	if hex_mode:
		decoder += "a=c.split({});c=a.pop(0)\n".format(escape)
		decoder += "for i in a:c+=chr(int(i[:2],16))+i[2:]\n"

	# run payload once decoded
	decoder += "exec(c)"

	# output decoder source code
	return decoder


# export encoder
def write_to_file(filename, content):
	global verbose

	if verbose > 0: print("\nSaving compressed script to {}".format(repr(filename)), end="... ")

	# write data to file
	try:
		with open(filename, "w") as file:
			file.write(content)

	# exit on error
	except:
		if verbose > 0: print("ERROR!")
		print("\nError: Failed to write to outfile\n\n")
		exit(-1)

	if verbose > 0: print("Done!\n\n")





# The main function
def main():
	global in_filename, out_filename, verbose, minify, hex_mode

	# parse command line arguments
	parse_cmd_args()

	# read and minify payload
	payload, file_size = read_payload_from_file(in_filename)
	if minify: payload = python_minifier(payload)

	# save initial code size
	init_size = len(payload)
	if verbose > 0:
		print("\nFile size: {} bytes".format(file_size))
		print("Code size: {} bytes".format(init_size))



	# generate inverted histogram
	inv_histo = list(inverted_histogram(payload))

	# replace rare chars with hex nums
	hex_esc_char = "$"
	if hex_mode:
		if verbose > 0: print("\nConverting rare chars to hex", end="... ")

		payload, replaced_chars = rare_to_hex(payload, inv_histo, hex_esc_char)
		
		if verbose > 0:
			print("Done!")
			print("\nChars replaced: {}".format(repr(replaced_chars)))
			print("Placeholders freed up: {}".format(len(replaced_chars)))
			print("Code size: {}".format(len(payload)))



	# generate placeholders for dictionary compression
	keys = generate_placeholders(payload)
	if verbose > 0:
		print("\n{} valid placeholders found: {}".format(len(keys), repr(keys)))

		for string, count in inv_histo:
			if (verbose < 2) and (count > 8): break

			msg = " # {} appears {}"
			if len(string) > 1: msg = msg.replace("s", "")

			amount = "{} times".format(count)
			if count < 3: amount = (["once", "twice"])[count-1]
			
			print(msg.format(repr(string), amount))



	# compress and pack payload
	payload, keys = compress_payload(payload, keys)
	escaped = repr(payload)
	output = pack_payload(escaped, repr(keys), repr(hex_esc_char))



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
