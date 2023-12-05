#!/bin/python3
import os
import re
import glob
from sys import argv

pattern_existing_version = re.compile(r'/static/[A-Za-z0-9]+/.+\.min\.[A-Za-z0-9]+\?v=[0-9]+', re.IGNORECASE)
pattern_no_version = re.compile(r'/static/[A-Za-z0-9]+/.+\.min\.[A-Za-z0-9]+(?!.*\?v=)', re.IGNORECASE)
version_pattern = re.compile("\?v=[0-9]+")


def process_file(filename):
    with open(filename, 'r') as f:
        file_out = []
        lines = f.readlines()
        for line in lines:
            if re.findall(pattern_no_version, line):
                match_string = re.findall(pattern_no_version, line)[0]
                line = re.sub(match_string, match_string + "?v=0", line)
            elif re.findall(pattern_existing_version, line):
                version_string = re.findall(version_pattern, line)[0]
                version_number = int(version_string.split('?v=')[1])
                line = re.sub(version_pattern, f"?v={version_number+1}", line)
            file_out.append(line)
    with open(filename, 'w') as f:
        f.write(''.join(file_out))  # \n is already there :P
        f.truncate()


if __name__ == "__main__":
    if argv:
        valid_files = ['templates/' + arg for arg in argv[1:]]
        input(f"Forcing client update for static files linked in:\n{', '.join(valid_files)}\nPress enter to continue...")
    else:
        input(f"Forcing client update for static files linked in:ALL FILES\nPress enter to continue...")
        valid_dirs = ('templates', 'templates/components')
        valid_files = [file for file in glob.glob('templates/learn/**', recursive=True) if file.endswith('.html')]
        for d in valid_dirs:
            valid_files += [f'{d}/{file}' for file in os.listdir(d) if file.endswith('.html')]

    for file in valid_files:
        process_file(file)
