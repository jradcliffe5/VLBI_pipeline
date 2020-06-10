with open('eg078g_edit.antab', 'w') as out_file:
	with open('eg078g.antab', 'r') as in_file:
		i = 0
		j=0
		start_edit = 0
		found_tele = False
		for line in in_file:
			i+=1
			if (line.startswith('GAIN CM')) or (line.startswith('GAIN DA')) or (line.startswith('GAIN KN')) or (line.startswith('GAIN TA')):
				found_tele = True
				start_edit = i+4
			#print (i>start_edit),((found_tele == True),(line.startswith('/')==False))
			if ((found_tele == True) and (i>start_edit) and (line.startswith('/')==False)):
				out_file.write(line.rstrip('\n') + ' 1.0 1.0 1.0 1.0' + '\n')
			elif (line.startswith('/')==True) and (i>start_edit):
				found_tele = False
				out_file.write(line.rstrip('\n') +  '\n')
			else:
				out_file.write(line.rstrip('\n') +  '\n')
